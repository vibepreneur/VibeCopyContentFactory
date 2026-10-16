from dataclasses import replace
import hashlib
import uuid
import aiohttp
import pytest
from aiohttp import web
from factory.config import Config
from factory.fake_worker import FakeWorker, serve
from factory.worker import WorkerClient, WorkerError, Contract
from conftest import picture

async def multipart(url,token,rid,original,reference,filename='image.png',mime='image/png'):
    form=aiohttp.FormData()
    form.add_field('request_id',rid)
    form.add_field('original',original,filename=filename,content_type=mime)
    form.add_field('reference',reference,filename='ref.png',content_type='image/png')
    async with aiohttp.ClientSession() as s:
        async with s.post(url+'/v1/jobs',data=form,headers={'Authorization':'Bearer '+token}) as r:
            return r.status,await r.json()

async def test_http_idempotency_binary_and_restart(workspace):
    original,ref=workspace/'o.png',workspace/'r.png'
    original.write_bytes(picture('red'));ref.write_bytes(picture('blue'))
    worker=FakeWorker(workspace/'worker.db')
    rid=str(uuid.uuid4())
    async with serve(worker) as url:
        client=WorkerClient(Config(data=workspace,worker_url=url))
        caps=await client.capabilities()
        assert caps['worker_queue_concurrency']==1
        for _ in range(3):
            assert (await client.submit(rid,original,ref,'pair'))['request_id']==rid
        assert worker.calls==0
        with pytest.raises(WorkerError,match='INVALID_STATE'):
            await client.result(rid)
        assert (await client.status(rid))['status']=='PROCESSING'
        assert (await client.status(rid))['status']=='COMPLETED'
        content,mime=await client.result(rid)
        assert mime=='image/png' and content==original.read_bytes()
        assert worker.calls==1
        for _ in range(3):
            await client.submit(rid,original,ref,'pair')
        assert worker.calls==1
        ref.write_bytes(picture('green'))
        with pytest.raises(WorkerError,match='IDEMPOTENCY_CONFLICT'):
            await client.submit(rid,original,ref,'pair')
    recovered=FakeWorker(workspace/'worker.db')
    async with serve(recovered) as url:
        client=WorkerClient(Config(data=workspace,worker_url=url))
        assert (await client.status(rid))['status']=='COMPLETED'
        assert (await client.result(rid))[0]==content
        assert recovered.calls==1

async def test_auth_limits_mime_paths_and_errors(workspace):
    worker=FakeWorker(workspace/'worker.db',max_bytes=500)
    contract=Contract()
    async with serve(worker) as url:
        async with aiohttp.ClientSession() as s:
            async with s.get(url+'/v1/capabilities') as r:
                assert r.status==401
                contract.validate('ErrorEnvelope',await r.json())
            async with s.get(url+'/health') as r:
                assert await r.json()=={'status':'ok'}
        rid=str(uuid.uuid4())
        for blob,name,mime,expected in [(b'x'*501,'o.png','image/png',413),(b'not image','o.png','image/png',415),(picture('red'),'../o.png','image/png',400),(picture('red'),'o.png','image/jpeg',415)]:
            status,body=await multipart(url,worker.token,rid,blob,picture('blue'),name,mime)
            assert status==expected
            contract.validate('ErrorEnvelope',body)
        assert worker.calls==0

async def test_version_guard_and_unknown_cost(workspace):
    class BadVersion(FakeWorker):
        async def capabilities(self,r):
            return web.json_response({'contract_versions':['2.0'],'pipeline_version':'fake/v2','supported_mime_types':['image/png'],'max_file_bytes':1000,'worker_queue_concurrency':1})
    async with serve(BadVersion(workspace/'bad.db')) as url:
        with pytest.raises(WorkerError,match='BLOCKED_API_CONTRACT'):
            await WorkerClient(Config(data=workspace,worker_url=url)).capabilities()
    with pytest.raises(WorkerError,match='PAID_CALLS_DISABLED'):
        WorkerClient(Config(data=workspace,worker_url='https://remote.invalid'))
    with pytest.raises(WorkerError,match='PAID_CALLS_DISABLED'):
        WorkerClient(Config(data=workspace,mode='REAL'))
    Contract().validate('Cost',{'currency':'RUB','amount':None,'cost_status':'unknown'})
    with pytest.raises(WorkerError,match='BLOCKED_API_CONTRACT'):
        Contract().validate('Cost',{'currency':'RUB','amount':-1,'cost_status':'actual'})

async def test_failed_attempt_cost_is_retained(workspace):
    worker=FakeWorker(workspace/'failed.db',outcome='FAILED')
    async with serve(worker) as url:
        original=workspace/'o.png';original.write_bytes(picture('red'))
        client=WorkerClient(Config(data=workspace,worker_url=url))
        rid=str(uuid.uuid4())
        await client.submit(rid,original,original,'failure')
        await client.status(rid)
        result=await client.status(rid)
        assert result['status']=='FAILED' and result['cost']['amount']==1.25
        assert worker.calls==1

@pytest.mark.parametrize('fmt,mime,ext',[('JPEG','image/jpeg','.jpg'),('PNG','image/png','.png'),('WEBP','image/webp','.webp')])
async def test_all_contract_image_formats(workspace,fmt,mime,ext):
    from PIL import Image
    path=workspace/('input'+ext)
    Image.new('RGB',(32,48),'orange').save(path,format=fmt)
    worker=FakeWorker(workspace/'formats.db')
    async with serve(worker) as url:
        client=WorkerClient(Config(data=workspace,worker_url=url))
        rid=str(uuid.uuid4())
        await client.submit(rid,path,path,'formats')
        await client.status(rid);await client.status(rid)
        content,result_mime=await client.result(rid)
        assert result_mime=='image/png' and content.startswith(b'\x89PNG')
        assert worker.calls==1

async def test_rate_limit_and_bad_result_hash(workspace):
    from factory.fake_worker import error
    class RateLimited(FakeWorker):
        async def submit(self,request):
            return error('RATE_LIMIT','Busy',429)
    path=workspace/'input.png';path.write_bytes(picture('red'))
    async with serve(RateLimited(workspace/'rate.db')) as url:
        client=WorkerClient(Config(data=workspace,worker_url=url))
        with pytest.raises(WorkerError,match='RATE_LIMIT'):
            await client.submit(str(uuid.uuid4()),path,path,'rate')
    class BadHash(FakeWorker):
        async def result(self,request):
            return web.Response(body=picture('red'),content_type='image/png',headers={'X-Content-SHA256':'0'*64})
    async with serve(BadHash(workspace/'hash.db')) as url:
        client=WorkerClient(Config(data=workspace,worker_url=url))
        with pytest.raises(WorkerError,match='RESULT_HASH_MISMATCH'):
            await client.result(str(uuid.uuid4()))
