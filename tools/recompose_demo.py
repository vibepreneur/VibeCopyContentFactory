"""Re-encode completed, test-only demo jobs without changing combination IDs.

This repair tool refuses normal Factory databases and never contacts a Worker.
"""
from pathlib import Path
import argparse
import asyncio
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factory.config import Config
from factory.engine import Factory
from factory.fake_worker import FakeWorker

async def repair(data,limit=None,skip=0):
    data=Path(data).resolve()
    if not data.is_relative_to(ROOT/'data/demo'):
        raise ValueError('Only disposable data/demo databases may be repaired')
    report=json.loads((data/'report.json').read_text())
    if report['integration']!='MOCK':
        raise ValueError('MOCK report required')
    f=Factory(Config(data=data))
    assert not f.db.all("SELECT id FROM queue_jobs WHERE status IN ('QUEUED','RUNNING')"),'Finish/resume the current demo before repairing'
    worker=FakeWorker(data/'fake-worker.sqlite3')
    calls=worker.calls
    videos=f.db.all('SELECT * FROM video_jobs ORDER BY created_at')[skip:]
    if limit is not None:
        videos=videos[:limit]
    for index,v in enumerate(videos,1):
        asset=f.db.one('SELECT * FROM assets WHERE id=?',(v['final_asset_id'],))
        if not asset or asset['rights_status']!='test-only':
            raise ValueError('Only generated test masters may be repaired')
        with f.db.transaction() as c:
            c.execute("UPDATE video_jobs SET output_status='QUEUED',review_status='PENDING' WHERE id=?",(v['id'],))
            c.execute("UPDATE combinations SET status='RESERVED' WHERE id=?",(v['combination_id'],))
            c.execute("UPDATE batch_slots SET stage='VIDEO',status='QUEUED' WHERE id=(SELECT slot_id FROM combinations WHERE id=?)",(v['combination_id'],))
            c.execute("UPDATE queue_jobs SET status='QUEUED',error=NULL,lease_until=NULL WHERE dedupe_key=?",('compose:'+v['id'],))
            c.execute("UPDATE notifications SET status='PENDING' WHERE kind='video' AND entity_id=?",(v['id'],))
        print(f'Recompose {index}/{len(videos)}: same video/combination {v["id"]}',flush=True)
        await f.drain('heavy')
        f.review_video(v['id'],'approve')
    assert worker.calls==calls
    assert f._worker is None
    print(f'PASS: {len(videos)} masters re-encoded; zero Worker calls',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('data');p.add_argument('--limit',type=int);p.add_argument('--skip',type=int,default=0)
    args=p.parse_args();asyncio.run(repair(args.data,args.limit,args.skip))
