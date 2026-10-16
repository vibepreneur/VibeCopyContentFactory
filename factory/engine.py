import asyncio
import json
import time
from .config import Config
from .db import DB, uid
from .library import Library
from .media import Remotion, Composer
from .worker import WorkerClient, WorkerError

class Factory:
    def __init__(self,config: Config):
        self.config=config
        self.db=DB(config.data/'factory.sqlite3')
        self.library=Library(self.db,config.data)
        self.remotion=Remotion(config)
        self.composer=Composer(config)
        self._worker=None
        with self.db.transaction() as c:
            for n,text in enumerate(('Твоё фото — в стиле референса','Повтори обработку любимого кадра','Один референс меняет настроение','Сохрани свой образ, перенеси стиль','Попробуй новый свет и цвет'),1):
                c.execute('INSERT OR IGNORE INTO hooks VALUES(?,?,?,?)',(f'hook-{n}',text,'[]','APPROVED'))
            c.execute('INSERT OR IGNORE INTO scenarios VALUES(?,?,?,?,?)',('standard','Avatar / Telegram / CTA',1,json.dumps({'hook_seconds':3,'screencast_seconds':24,'cta_seconds':3}),'APPROVED'))

    @property
    def worker(self):
        if self._worker is None:
            self._worker=WorkerClient(self.config)
        return self._worker

    def start_a(self,count=10):
        if count!=10:
            raise ValueError('Mode A requires exactly 10 initial slots')
        if self.config.mode=='REAL':
            raise ValueError('LIVE_KLING_API_NOT_CONFIGURED: Mode A live integration pending')
        pairs=self.db.all("SELECT p.* FROM photo_pairs p JOIN assets o ON o.id=p.original_asset_id JOIN assets r ON r.id=p.reference_asset_id WHERE p.status='APPROVED' AND o.status='APPROVED' AND r.status='APPROVED' ORDER BY (SELECT count(*) FROM cases c WHERE c.pair_id=p.id),p.id LIMIT 10")
        if len(pairs)<10:
            raise ValueError('TEN_APPROVED_PHOTO_PAIRS_REQUIRED')
        for pair in pairs:
            self.library.file(pair['original_asset_id'])
            self.library.file(pair['reference_asset_id'])
        batch=uid()
        with self.db.transaction() as c:
            c.execute('INSERT INTO batches VALUES(?,?,?,?,?,NULL)',(batch,'A',10,'RUNNING',time.time()))
            for n,pair in enumerate(pairs,1):
                case,slot=uid(),uid()
                c.execute('INSERT INTO cases(id,pair_id,status) VALUES(?,?,?)',(case,pair['id'],'PROCESSING_QUEUED'))
                c.execute('INSERT INTO batch_slots VALUES(?,?,?,?,?,?,?)',(slot,batch,n,case,0,'PROCESSING','QUEUED'))
                self._attempt(c,case,slot,batch)
        return batch

    def _attempt(self,c,case,slot,batch):
        previous=c.execute('SELECT coalesce(max(attempt_no),0) FROM processing_attempts WHERE case_id=?',(case,)).fetchone()[0]
        if previous>=1+self.config.max_retries:
            raise ValueError('RETRY_LIMIT_EXCEEDED')
        rid=uid()
        c.execute('INSERT INTO processing_attempts(id,case_id,request_id,attempt_no,worker_status,created_at) VALUES(?,?,?,?,?,?)',(uid(),case,rid,previous+1,'NOT_SUBMITTED',time.time()))
        c.execute("UPDATE cases SET processing_request_id=?,result_asset_id=NULL,status='PROCESSING_QUEUED' WHERE id=?",(rid,case))
        c.execute("UPDATE batch_slots SET attempt_no=?,stage='PROCESSING',status='QUEUED' WHERE id=?",(previous+1,slot))
        c.execute('INSERT INTO expenses VALUES(?,?,?,?,?,?,?,?,?,?)',(uid(),'worker:'+rid,'worker',batch,None,'RUB',None,'unknown','fake' if self.config.mode=='MOCK' else 'worker',time.time()))
        DB.enqueue(c,'processing','processing:'+rid,{'case_id':case,'request_id':rid})
        return rid

    def review_case(self,case_id,action,attempt_no=None):
        if action not in ('approve','retry','reject-final'):
            raise ValueError('INVALID_REVIEW_ACTION')
        with self.db.transaction() as c:
            case=c.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone()
            if not case:
                raise ValueError('CASE_NOT_FOUND')
            slot=c.execute('SELECT * FROM batch_slots WHERE case_id=?',(case_id,)).fetchone()
            if attempt_no is not None and slot['attempt_no']!=attempt_no:
                return 'STALE'
            allowed=('PENDING_REVIEW',) if action=='approve' else ('PENDING_REVIEW','FAILED','RECONCILIATION_REQUIRED')
            if case['status'] not in allowed:
                return 'ALREADY_HANDLED'
            if action=='approve':
                target=self.library.snapshot(case['result_asset_id'])
                c.execute("UPDATE assets SET path=?,status='APPROVED',approved_at=? WHERE id=?",(str(target),time.time(),case['result_asset_id']))
                c.execute("UPDATE cases SET status='SCREENCAST_QUEUED',reviewed_at=? WHERE id=?",(time.time(),case_id))
                c.execute("UPDATE batch_slots SET stage='SCREENCAST',status='QUEUED' WHERE id=?",(slot['id'],))
                DB.enqueue(c,'screencast','screencast:'+case_id,{'case_id':case_id})
            elif action=='retry':
                if case['status']=='RECONCILIATION_REQUIRED':
                    raise ValueError('RECONCILIATION_REQUIRED: resolve possible provider spending before retry')
                self._attempt(c,case_id,slot['id'],slot['batch_id'])
            else:
                c.execute("UPDATE cases SET status='REJECT_FINAL',reviewed_at=? WHERE id=?",(time.time(),case_id))
                c.execute("UPDATE batch_slots SET stage='CLOSED',status='REJECTED' WHERE id=?",(slot['id'],))
        self.refresh_batches()
        return 'OK'

    def _reserve(self,c,batch,slot=None,screencast=None):
        # Query each reservation anew inside one write transaction, so newly used
        # pairs immediately lose their novelty preference.
        rows=c.execute("""SELECT a.id avatar,s.id screen,h.id hook,sc.id scenario,sc.version,
             h.tags_json hook_tags,s.metadata_json screen_meta
          FROM assets a CROSS JOIN assets s CROSS JOIN hooks h CROSS JOIN scenarios sc
          WHERE a.type='animated_avatar' AND a.status='APPROVED' AND s.type='screencast'
          AND ((? IS NULL AND s.status='APPROVED') OR (? IS NOT NULL AND s.id=?))
          AND h.status='APPROVED' AND sc.status='APPROVED'
          AND NOT EXISTS(SELECT 1 FROM combinations x WHERE x.avatar_clip_asset_id=a.id AND x.screencast_asset_id=s.id AND x.hook_id=h.id AND x.scenario_id=sc.id AND x.scenario_version=sc.version AND x.creative_revision=1)
          ORDER BY (SELECT count(*) FROM combinations x WHERE x.avatar_clip_asset_id=a.id AND x.screencast_asset_id=s.id),a.id,s.id,h.id,sc.id""",(screencast,screencast,screencast)).fetchall()
        for row in rows:
            if not set(json.loads(row['hook_tags'])).issubset(set(json.loads(row['screen_meta']).get('tags',[]))):
                continue
            self.library.file(row['avatar'])
            self.library.file(row['screen'])
            combination,video=uid(),uid()
            c.execute('INSERT INTO combinations VALUES(?,?,?,?,?,?,?,?,?,?,?)',(combination,batch,slot,row['avatar'],row['screen'],row['hook'],row['scenario'],row['version'],1,'RESERVED',time.time()))
            c.execute('INSERT INTO video_jobs(id,combination_id,output_status,review_status,created_at) VALUES(?,?,?,?,?)',(video,combination,'QUEUED','PENDING',time.time()))
            DB.enqueue(c,'compose','compose:'+video,{'video_id':video})
            return combination
        return None

    def start_b(self,count=10):
        if count!=10:
            raise ValueError('Mode B target is 10')
        batch=uid()
        with self.db.transaction() as c:
            c.execute('INSERT INTO batches VALUES(?,?,?,?,?,NULL)',(batch,'B',count,'RUNNING',time.time()))
            for n in range(1,count+1):
                slot=uid()
                c.execute('INSERT INTO batch_slots VALUES(?,?,?,NULL,0,?,?)',(slot,batch,n,'VIDEO','QUEUED'))
                if not self._reserve(c,batch,slot):
                    c.execute('DELETE FROM batch_slots WHERE id=?',(slot,))
                    break
        self.refresh_batches()
        return batch

    async def _processing(self,payload):
        case_id,rid=payload['case_id'],payload['request_id']
        case=self.db.one('SELECT * FROM cases WHERE id=?',(case_id,))
        if case['processing_request_id']!=rid or case['status'] in ('SCREENCAST_QUEUED','VIDEO_PENDING_REVIEW','VIDEO_APPROVED','REJECT_FINAL'):
            return
        pair=self.db.one('SELECT * FROM photo_pairs WHERE id=?',(case['pair_id'],))
        attempt=self.db.one('SELECT * FROM processing_attempts WHERE request_id=?',(rid,))
        try:
            if attempt['worker_status']=='NOT_SUBMITTED':
                form=await self.worker.prepare_submission(rid,self.library.file(pair['original_asset_id']),self.library.file(pair['reference_asset_id']),pair['id'])
                self.db.execute("UPDATE processing_attempts SET worker_status='SUBMITTING' WHERE request_id=?",(rid,))
                await self.worker.submit_prepared(rid,form)
            self.db.execute("UPDATE cases SET status='PROCESSING' WHERE id=?",(case_id,))
            deadline=time.monotonic()+1800
            while True:
                try:
                    state=await self.worker.status(rid)
                except WorkerError as e:
                    if e.code=='NOT_FOUND':
                        raise WorkerError('RECONCILIATION_REQUIRED','Submission may have reached provider') from None
                    raise
                status=state['status']
                cost=state.get('cost',{'amount':None,'currency':'RUB','cost_status':'unknown'})
                with self.db.transaction() as c:
                    c.execute('UPDATE processing_attempts SET worker_status=?,generation_cost_amount=?,cost_status=? WHERE request_id=?',(status,cost['amount'],cost['cost_status'],rid))
                    c.execute('UPDATE expenses SET amount_nullable=?,currency=?,cost_status=? WHERE source_call_id=?',(cost['amount'],cost['currency'],cost['cost_status'],'worker:'+rid))
                if status in ('COMPLETED','FAILED','RECONCILIATION_REQUIRED'):
                    break
                if time.monotonic()>deadline:
                    raise WorkerError('RECONCILIATION_REQUIRED','Polling timed out; no resubmit')
                await asyncio.sleep(.05 if self.config.mode=='MOCK' else 2)
            if status=='COMPLETED' and state['result_ready']:
                content,mime=await self.worker.result(rid)
                asset=self.library.add(content,'result',mime,source=rid,rights='test-only' if self.config.mode=='MOCK' else 'unknown')
                with self.db.transaction() as c:
                    c.execute("UPDATE cases SET result_asset_id=?,pipeline_version=?,status='PENDING_REVIEW' WHERE id=? AND processing_request_id=?",(asset,state.get('pipeline_version'),case_id,rid))
                    c.execute("UPDATE batch_slots SET stage='REVIEW',status='PENDING_REVIEW' WHERE case_id=?",(case_id,))
                    DB.notify(c,'candidate',rid)
            else:
                status='RECONCILIATION_REQUIRED' if status=='COMPLETED' else status
                with self.db.transaction() as c:
                    c.execute('UPDATE cases SET status=? WHERE id=?',(status,case_id))
                    c.execute('UPDATE batch_slots SET status=? WHERE case_id=?',(status,case_id))
                    DB.notify(c,'candidate',rid)
        except Exception:
            current=self.db.one('SELECT worker_status FROM processing_attempts WHERE request_id=?',(rid,))
            safe_failure=current['worker_status']=='NOT_SUBMITTED'
            failed_status='FAILED' if safe_failure else 'RECONCILIATION_REQUIRED'
            with self.db.transaction() as c:
                c.execute('UPDATE cases SET status=? WHERE id=?',(failed_status,case_id))
                c.execute('UPDATE batch_slots SET status=? WHERE case_id=?',(failed_status,case_id))
                if safe_failure:
                    # No POST was attempted: this is known zero spend, not an
                    # unknown provider charge. Technical resume keeps the UUID.
                    c.execute("UPDATE expenses SET amount_nullable=0,cost_status='actual' WHERE source_call_id=?",('worker:'+rid,))
                DB.notify(c,'candidate',rid)
            raise

    async def _screencast(self,payload):
        case_id=payload['case_id']
        case=self.db.one('SELECT * FROM cases WHERE id=?',(case_id,))
        if case['screencast_asset_id']:
            return
        pair=self.db.one('SELECT * FROM photo_pairs WHERE id=?',(case['pair_id'],))
        photos={k:self.library.file(v) for k,v in {'original':pair['original_asset_id'],'reference':pair['reference_asset_id'],'result':case['result_asset_id']}.items()}
        output,timeline=await asyncio.to_thread(self.remotion.render,case_id,photos,self.config.data/'work'/case_id)
        screen=self.library.add(output.read_bytes(),'screencast','video/mp4',metadata={'timeline':timeline,'tags':json.loads(pair['tags_json']),'case_id':case_id},rights='test-only' if self.config.mode=='MOCK' else 'unknown')
        with self.db.transaction() as c:
            slot=c.execute('SELECT * FROM batch_slots WHERE case_id=?',(case_id,)).fetchone()
            if not self._reserve(c,slot['batch_id'],slot['id'],screen):
                raise ValueError('APPROVED_AVATAR_CLIP_REQUIRED_OR_COMBINATIONS_EXHAUSTED')
            c.execute("UPDATE cases SET screencast_asset_id=?,status='VIDEO_QUEUED' WHERE id=?",(screen,case_id))
            c.execute("UPDATE batch_slots SET stage='VIDEO',status='QUEUED' WHERE id=?",(slot['id'],))

    async def _compose(self,payload):
        video=self.db.one('SELECT * FROM video_jobs WHERE id=?',(payload['video_id'],))
        if video['output_status']=='RENDERED':
            return
        combo=self.db.one('SELECT * FROM combinations WHERE id=?',(video['combination_id'],))
        screen=self.db.one('SELECT * FROM assets WHERE id=?',(combo['screencast_asset_id'],))
        hook=self.db.one('SELECT * FROM hooks WHERE id=?',(combo['hook_id'],))
        output=await asyncio.to_thread(self.composer.compose,self.library.file(screen['id']),self.library.file(combo['avatar_clip_asset_id']),hook['text'],json.loads(screen['metadata_json']).get('timeline',{}),self.config.data/'work'/video['id'])
        asset=self.library.add(output.read_bytes(),'final','video/mp4',metadata={'combination_id':combo['id'],'mock':self.config.mode=='MOCK'},rights='test-only' if self.config.mode=='MOCK' else 'unknown')
        with self.db.transaction() as c:
            c.execute("UPDATE video_jobs SET final_asset_id=?,duration=30,output_status='RENDERED',review_status='PENDING_REVIEW',error_code=NULL WHERE id=?",(asset,video['id']))
            c.execute("UPDATE combinations SET status='RENDERED' WHERE id=?",(combo['id'],))
            c.execute("UPDATE batch_slots SET status='VIDEO_PENDING_REVIEW' WHERE id=?",(combo['slot_id'],))
            c.execute("UPDATE cases SET status='VIDEO_PENDING_REVIEW' WHERE id=(SELECT case_id FROM batch_slots WHERE id=?)",(combo['slot_id'],))
            DB.notify(c,'video',video['id'])

    def review_video(self,video_id,action):
        if action not in ('approve','reject','remake'):
            raise ValueError('INVALID_REVIEW_ACTION')
        with self.db.transaction() as c:
            video=c.execute('SELECT * FROM video_jobs WHERE id=?',(video_id,)).fetchone()
            if not video:
                raise ValueError('VIDEO_NOT_FOUND')
            if video['review_status']!='PENDING_REVIEW':
                return 'ALREADY_HANDLED'
            combo=c.execute('SELECT * FROM combinations WHERE id=?',(video['combination_id'],)).fetchone()
            if action=='remake':
                c.execute("UPDATE video_jobs SET review_status='REMAKE_REQUESTED' WHERE id=?",(video_id,))
                c.execute("UPDATE combinations SET status='REMADE' WHERE id=?",(combo['id'],))
                new_combo,new_video=uid(),uid()
                c.execute('INSERT INTO combinations VALUES(?,?,?,?,?,?,?,?,?,?,?)',(new_combo,combo['batch_id'],combo['slot_id'],combo['avatar_clip_asset_id'],combo['screencast_asset_id'],combo['hook_id'],combo['scenario_id'],combo['scenario_version'],combo['creative_revision']+1,'RESERVED',time.time()))
                c.execute('INSERT INTO video_jobs(id,combination_id,output_status,review_status,created_at) VALUES(?,?,?,?,?)',(new_video,new_combo,'QUEUED','PENDING',time.time()))
                DB.enqueue(c,'compose','compose:'+new_video,{'video_id':new_video})
                c.execute("UPDATE batch_slots SET status='QUEUED' WHERE id=?",(combo['slot_id'],))
            else:
                status='APPROVED' if action=='approve' else 'REJECTED'
                if action=='approve':
                    for asset_id in (video['final_asset_id'],combo['screencast_asset_id']):
                        target=self.library.snapshot(asset_id)
                        c.execute("UPDATE assets SET status='APPROVED',path=?,approved_at=? WHERE id=?",(str(target),time.time(),asset_id))
                c.execute('UPDATE video_jobs SET review_status=? WHERE id=?',(status,video_id))
                c.execute('UPDATE combinations SET status=? WHERE id=?',(status,combo['id']))
                c.execute("UPDATE batch_slots SET stage='CLOSED',status=? WHERE id=?",(status,combo['slot_id']))
                c.execute('UPDATE cases SET status=? WHERE id=(SELECT case_id FROM batch_slots WHERE id=?)',('VIDEO_'+status,combo['slot_id']))
        self.refresh_batches()
        return 'OK'

    async def step(self,lane=None):
        job=self.db.claim(lane=lane)
        if not job:
            return False
        try:
            await {'processing':self._processing,'screencast':self._screencast,'compose':self._compose}[job['type']](json.loads(job['payload_json']))
        except Exception as e:
            self.db.finish(job['id'],str(e))
            if job['type']=='compose':
                vid=json.loads(job['payload_json'])['video_id']
                self.db.execute("UPDATE video_jobs SET output_status='FAILED',error_code=? WHERE id=?",(str(e),vid))
                self.db.execute("UPDATE combinations SET status='FAILED' WHERE id=(SELECT combination_id FROM video_jobs WHERE id=?)",(vid,))
                self.db.execute("UPDATE batch_slots SET status='FAILED' WHERE id=(SELECT slot_id FROM combinations WHERE id=(SELECT combination_id FROM video_jobs WHERE id=?))",(vid,))
            elif job['type']=='screencast':
                self.db.execute("UPDATE batch_slots SET status='FAILED' WHERE case_id=?",(json.loads(job['payload_json'])['case_id'],))
            raise
        else:
            self.db.finish(job['id'])
        finally:
            self.refresh_batches()
        return True

    async def drain(self,lane=None):
        while await self.step(lane):
            pass

    def resume(self,job_id):
        row=self.db.one("SELECT * FROM queue_jobs WHERE id=? AND status='FAILED'",(job_id,))
        if not row:
            raise ValueError('FAILED_JOB_REQUIRED')
        self.db.execute("UPDATE queue_jobs SET status='QUEUED',error=NULL,lease_until=NULL WHERE id=?",(job_id,))
        payload=json.loads(row['payload_json'])
        if row['type']=='screencast':
            self.db.execute("UPDATE batch_slots SET status='QUEUED' WHERE case_id=?",(payload['case_id'],))
        elif row['type']=='compose':
            self.db.execute("UPDATE batch_slots SET status='QUEUED' WHERE id=(SELECT slot_id FROM combinations WHERE id=(SELECT combination_id FROM video_jobs WHERE id=?))",(payload['video_id'],))
        return job_id

    def refresh_batches(self):
        with self.db.transaction() as c:
            for batch in c.execute('SELECT * FROM batches').fetchall():
                counts={r[0]:r[1] for r in c.execute('SELECT status,count(*) FROM batch_slots WHERE batch_id=? GROUP BY status',(batch['id'],))}
                total=sum(counts.values())
                terminal=sum(counts.get(s,0) for s in ('APPROVED','REJECTED','FAILED'))
                if total==terminal:
                    status='COMPLETED' if counts.get('APPROVED',0)==batch['target_count'] else 'PARTIAL'
                else:
                    status='RUNNING'
                c.execute('UPDATE batches SET status=?,finished_at=? WHERE id=?',(status,time.time() if status!='RUNNING' else None,batch['id']))

    def status(self):
        return {'integration':self.config.mode,'batches':self.db.all('SELECT b.*, (SELECT count(*) FROM batch_slots s WHERE s.batch_id=b.id) actual_slots FROM batches b ORDER BY created_at'),
                'slots':self.db.all('SELECT batch_id,stage,status,count(*) count FROM batch_slots GROUP BY batch_id,stage,status'),
                'queue':self.db.all('SELECT type,status,count(*) count FROM queue_jobs GROUP BY type,status'),
                'expenses':self.db.all('SELECT provider,currency,cost_status,sum(amount_nullable) amount,count(*) attempts FROM expenses GROUP BY provider,currency,cost_status'),
                'pending_candidates':self.db.all("SELECT c.id,c.pair_id,c.status,s.attempt_no FROM cases c JOIN batch_slots s ON s.case_id=c.id WHERE c.status IN ('PENDING_REVIEW','FAILED','RECONCILIATION_REQUIRED') ORDER BY c.id LIMIT 100"),
                'pending_videos':self.db.all("SELECT v.id,c.batch_id,v.review_status,a.path FROM video_jobs v JOIN combinations c ON c.id=v.combination_id LEFT JOIN assets a ON a.id=v.final_asset_id WHERE v.review_status='PENDING_REVIEW' ORDER BY v.created_at LIMIT 100"),
                'errors':self.db.all("SELECT id,type,error FROM queue_jobs WHERE status='FAILED' ORDER BY updated_at DESC LIMIT 100"),
                'delivery':self.db.all('SELECT status,count(*) count FROM notifications GROUP BY status')}

    async def run(self):
        async def lane(name):
            while True:
                try:
                    if not await self.step(name):
                        await asyncio.sleep(.5)
                except Exception as e:
                    print(f'{name}: {e}',flush=True)
                    await asyncio.sleep(1)
        await asyncio.gather(lane('processing'),lane('heavy'))
