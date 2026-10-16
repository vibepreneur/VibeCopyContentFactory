"""Contract-conforming, durable local HTTP fixture. Never imports an AI pipeline."""
from contextlib import asynccontextmanager, contextmanager
from io import BytesIO
from pathlib import Path
import hashlib
import hmac
import sqlite3
import uuid
from aiohttp import web
from PIL import Image, UnidentifiedImageError

def error(code, message, status, request_id=None):
    return web.json_response({'error':{'code':code,'message':message,'request_id':request_id}},status=status)

class FakeWorker:
    def __init__(self, path: Path, token='factory-local-fake-token', max_bytes=15*1024*1024, outcome='COMPLETED'):
        self.path,self.token,self.max_bytes,self.outcome=Path(path),token,max_bytes,outcome
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS jobs(request_id TEXT PRIMARY KEY, signature TEXT NOT NULL, original BLOB NOT NULL, status TEXT NOT NULL, result BLOB, calls INTEGER NOT NULL DEFAULT 0)')

    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=30)
        c.row_factory=sqlite3.Row
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    @property
    def calls(self):
        with self.db() as c:
            return c.execute('SELECT coalesce(sum(calls),0) FROM jobs').fetchone()[0]

    def app(self):
        @web.middleware
        async def auth(request,handler):
            if request.path != '/health' and not hmac.compare_digest(request.headers.get('Authorization','').encode(), ('Bearer '+self.token).encode()):
                return error('UNAUTHORIZED','Bearer required',401)
            try:
                return await handler(request)
            except web.HTTPRequestEntityTooLarge:
                return error('INVALID_INPUT','Upload too large',413)
            except web.HTTPNotFound:
                return error('NOT_FOUND','Unknown endpoint',404)
        app=web.Application(middlewares=[auth],client_max_size=self.max_bytes*2+1024*1024)
        async def health(request):
            return web.json_response({'status':'ok'})
        app.router.add_get('/health',health)
        app.router.add_get('/v1/capabilities',self.capabilities)
        app.router.add_post('/v1/jobs',self.submit)
        app.router.add_get('/v1/jobs/{request_id}',self.status)
        app.router.add_get('/v1/jobs/{request_id}/result',self.result)
        return app

    async def capabilities(self,request):
        return web.json_response({'contract_versions':['1.0'],'pipeline_version':'fake/fixture-v1','supported_mime_types':['image/jpeg','image/png','image/webp'],'max_file_bytes':self.max_bytes,'worker_queue_concurrency':1})

    async def submit(self,request):
        if request.content_type!='multipart/form-data':
            return error('INVALID_INPUT','Multipart required',400)
        parts={}
        try:
            reader=await request.multipart()
            async for part in reader:
                if part.name in parts or part.name not in ('request_id','photo_pair_id','original','reference'):
                    return error('INVALID_INPUT','Unknown or repeated field',400)
                if part.name in ('original','reference'):
                    if not part.filename or any(s in part.filename for s in ('/','\\','..')):
                        return error('INVALID_INPUT','Unsafe filename',400)
                    content=bytearray()
                    while chunk:=await part.read_chunk():
                        content.extend(chunk)
                        if len(content)>self.max_bytes:
                            return error('INVALID_INPUT','Upload too large',413)
                    declared=part.headers.get('Content-Type','')
                    try:
                        with Image.open(BytesIO(content)) as im:
                            actual=Image.MIME.get(im.format)
                            im.verify()
                        if declared!=actual or actual not in ('image/jpeg','image/png','image/webp'):
                            return error('INVALID_INPUT','Unsupported image',415)
                    except (UnidentifiedImageError,OSError,ValueError):
                        return error('INVALID_INPUT','Invalid image bytes',415)
                    parts[part.name]=bytes(content)
                else:
                    content=await part.read(decode=True)
                    if len(content)>256:
                        return error('INVALID_INPUT','Field too long',400)
                    parts[part.name]=content.decode('utf-8')
            rid=parts['request_id']
            if str(uuid.UUID(rid))!=rid.lower() or len(parts.get('photo_pair_id',''))>128:
                raise ValueError()
            original,reference=parts['original'],parts['reference']
        except (KeyError,ValueError,UnicodeError,AssertionError):
            return error('INVALID_INPUT','Invalid multipart fields',400)
        signature=hashlib.sha256(original+hashlib.sha256(reference).digest()+parts.get('photo_pair_id','').encode()).hexdigest()
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM jobs WHERE request_id=?',(rid,)).fetchone()
            if old:
                if old['signature']!=signature:
                    return error('IDEMPOTENCY_CONFLICT','UUID content differs',409,rid)
                status,code=old['status'],200
            else:
                c.execute('INSERT INTO jobs(request_id,signature,original,status) VALUES(?,?,?,?)',(rid,signature,original,'QUEUED'))
                status,code='QUEUED',202
        return web.json_response({'contract_version':'1.0','request_id':rid,'status':status,'pipeline_version':'fake/fixture-v1'},status=code)

    def get(self,rid):
        with self.db() as c:
            r=c.execute('SELECT * FROM jobs WHERE request_id=?',(rid,)).fetchone()
            return dict(r) if r else None

    async def status(self,request):
        rid=request.match_info['request_id']
        job=self.get(rid)
        if not job:
            return error('NOT_FOUND','Unknown request',404)
        with self.db() as c:
            if job['status']=='QUEUED':
                c.execute("UPDATE jobs SET status='PROCESSING' WHERE request_id=?",(rid,))
            elif job['status']=='PROCESSING':
                output=BytesIO()
                with Image.open(BytesIO(job['original'])) as im:
                    im.convert('RGB').save(output,format='PNG')
                c.execute('UPDATE jobs SET status=?,result=?,calls=calls+1 WHERE request_id=? AND status=?',(self.outcome,output.getvalue(),rid,'PROCESSING'))
        job=self.get(rid)
        unknown=job['status']=='RECONCILIATION_REQUIRED'
        return web.json_response({'contract_version':'1.0','request_id':rid,'status':job['status'],'result_ready':job['status']=='COMPLETED','pipeline_version':'fake/fixture-v1','cost':{'currency':'RUB','amount':None if unknown else (1.25 if job['calls'] else 0),'cost_status':'unknown' if unknown else 'actual'},'stages':[{'stage':'fixture','status':job['status']}]})

    async def result(self,request):
        rid=request.match_info['request_id']
        job=self.get(rid)
        if not job:
            return error('NOT_FOUND','Unknown request',404)
        if job['status']!='COMPLETED':
            return error('INVALID_STATE','Result not ready',409,rid)
        return web.Response(body=job['result'],content_type='image/png',headers={'X-Content-SHA256':hashlib.sha256(job['result']).hexdigest()})

@asynccontextmanager
async def serve(worker: FakeWorker, port=0):
    runner=web.AppRunner(worker.app())
    await runner.setup()
    try:
        site=web.TCPSite(runner,'127.0.0.1',port)
        await site.start()
        actual=site._server.sockets[0].getsockname()[1]
        yield f'http://127.0.0.1:{actual}'
    finally:
        await runner.cleanup()
