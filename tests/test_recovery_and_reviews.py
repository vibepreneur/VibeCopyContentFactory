import asyncio
import json
import subprocess
import sys
import pytest
from factory.config import Config
from factory.engine import Factory
from factory.fake_worker import FakeWorker, serve
from factory.worker import WorkerError
from factory.avatar import CachedAvatarProvider, KlingProvider
from factory.bot import FakeGateway, flush_notifications
from conftest import seed
from test_factory import approved_screens

async def test_ambiguous_submit_restart_never_resubmits(factory):
    factory.start_a()
    job=factory.db.one('SELECT * FROM queue_jobs ORDER BY created_at LIMIT 1')
    payload=json.loads(job['payload_json'])
    factory.db.execute("UPDATE processing_attempts SET worker_status='SUBMITTING' WHERE request_id=?",(payload['request_id'],))
    worker=FakeWorker(factory.config.data/'worker.db')
    async with serve(worker) as url:
        factory.config.worker_url=url
        for _ in range(2):
            with pytest.raises(WorkerError,match='RECONCILIATION_REQUIRED'):
                await factory.step('processing')
            factory.resume(job['id'])
        assert worker.calls==0
        assert worker.get(payload['request_id']) is None
        assert factory.db.one('SELECT * FROM cases WHERE id=?',(payload['case_id'],))['status']=='RECONCILIATION_REQUIRED'

async def test_unknown_cost_and_avatar_guards(factory):
    worker=FakeWorker(factory.config.data/'worker.db',outcome='RECONCILIATION_REQUIRED')
    async with serve(worker) as url:
        factory.config.worker_url=url
        factory.start_a()
        await factory.step('processing')
        expense=factory.db.one("SELECT * FROM expenses WHERE cost_status='unknown' ORDER BY created_at LIMIT 1")
        assert expense['amount_nullable'] is None
        assert await CachedAvatarProvider(factory.library).animate()
        with pytest.raises(RuntimeError,match='PAID_CALLS_DISABLED'):
            await KlingProvider(factory.config).animate('static','uuid')

async def test_preflight_failure_can_resume_same_uuid_without_new_attempt(factory):
    worker=FakeWorker(factory.config.data/'worker.db')
    async with serve(worker) as url:
        factory.config.worker_url=url
        factory.config.worker_token='wrong-token'
        factory.start_a()
        job=factory.db.one('SELECT * FROM queue_jobs ORDER BY created_at LIMIT 1')
        payload=json.loads(job['payload_json'])
        with pytest.raises(WorkerError,match='UNAUTHORIZED'):
            await factory.step('processing')
        assert worker.calls==0 and worker.get(payload['request_id']) is None
        assert factory.db.one('SELECT * FROM cases WHERE id=?',(payload['case_id'],))['status']=='FAILED'
        assert factory.db.one('SELECT * FROM expenses WHERE source_call_id=?',('worker:'+payload['request_id'],))['amount_nullable']==0
        factory.config.worker_token=worker.token
        factory.resume(job['id'])
        await factory.step('processing')
        case=factory.db.one('SELECT * FROM cases WHERE id=?',(payload['case_id'],))
        assert case['status']=='PENDING_REVIEW' and case['processing_request_id']==payload['request_id']
        assert factory.db.one('SELECT count(*) n FROM processing_attempts')['n']==10
        assert worker.calls==1

def test_video_approve_reject_remake_idempotency(factory):
    approved_screens(factory)
    batch=factory.start_b()
    videos=factory.db.all('SELECT * FROM video_jobs ORDER BY created_at')
    for i,v in enumerate(videos[:3]):
        asset=factory.library.add(f'UNIT FINAL {i}'.encode(),'final','video/mp4',rights='test-only')
        factory.db.execute("UPDATE video_jobs SET final_asset_id=?,output_status='RENDERED',review_status='PENDING_REVIEW' WHERE id=?",(asset,v['id']))
    assert factory.review_video(videos[0]['id'],'approve')=='OK'
    assert factory.review_video(videos[0]['id'],'approve')=='ALREADY_HANDLED'
    assert factory.review_video(videos[1]['id'],'remake')=='OK'
    assert factory.review_video(videos[1]['id'],'remake')=='ALREADY_HANDLED'
    assert factory.db.one('SELECT count(*) n FROM combinations WHERE creative_revision=2')['n']==1
    assert factory.review_video(videos[2]['id'],'reject')=='OK'
    assert factory.db.one('SELECT count(*) n FROM combinations')['n']==11

async def test_failed_render_resume_keeps_combination(factory):
    approved_screens(factory)
    factory.start_b()
    def fail(*args):
        raise RuntimeError('SIMULATED_COMPOSER_FAILURE')
    factory.composer.compose=fail
    with pytest.raises(RuntimeError,match='SIMULATED_COMPOSER_FAILURE'):
        await factory.step('heavy')
    job=factory.db.one("SELECT * FROM queue_jobs WHERE status='FAILED'")
    factory.resume(job['id'])
    def succeed(screen,avatar,hook,timeline,work):
        work.mkdir(parents=True,exist_ok=True)
        path=work/'unit-master.mp4';path.write_bytes(b'UNIT OUTPUT')
        return path
    factory.composer.compose=succeed
    await factory.step('heavy')
    assert factory.db.one('SELECT count(*) n FROM combinations')['n']==10
    assert factory.db.one("SELECT count(*) n FROM video_jobs WHERE output_status='RENDERED'")['n']==1

def test_import_50_pairs_missing_asset_and_conflict(workspace):
    f=Factory(Config(data=workspace))
    manifest=seed(f,50)
    assert f.library.import_manifest(manifest)==50
    assert f.db.one('SELECT count(*) n FROM photo_pairs')['n']==50
    doc=json.loads(manifest.read_text())
    doc['pairs']=[{**doc['pairs'][0],'original':'missing.png'}]
    manifest.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='missing import path'):
        f.library.import_manifest(manifest)
    doc['pairs'][0]['original']='o1.png'
    manifest.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='PAIR_ID_CONFLICT'):
        f.library.import_manifest(manifest)

def test_heavy_lock_serializes_processes(workspace):
    code="""from pathlib import Path
import json,sys,time
from factory.media import heavy_lock
with heavy_lock(Path(sys.argv[1]).parent):
    start=time.monotonic()
    time.sleep(.3)
    Path(sys.argv[1]).write_text(json.dumps([start,time.monotonic()]))
"""
    first,second=workspace/'first.json',workspace/'second.json'
    processes=[subprocess.Popen([sys.executable,'-X','utf8','-c',code,str(p)]) for p in (first,second)]
    assert all(p.wait(timeout=30)==0 for p in processes)
    spans=sorted([json.loads(p.read_text()) for p in (first,second)])
    assert spans[0][1]<=spans[1][0]
