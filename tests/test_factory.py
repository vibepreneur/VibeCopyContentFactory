from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import time
import pytest
from factory.db import DB
from factory.engine import Factory
from factory.fake_worker import FakeWorker, serve
from factory.bot import Controller, FakeGateway, flush_notifications
from conftest import seed

async def candidates(f):
    worker=FakeWorker(f.config.data/'worker.db')
    return worker

async def test_mode_a_review_retry_partial_and_cost(factory):
    worker=FakeWorker(factory.config.data/'worker.db')
    async with serve(worker) as url:
        factory.config.worker_url=url
        batch=factory.start_a()
        assert len(factory.db.all('SELECT * FROM batch_slots'))==10
        await factory.drain('processing')
        cases=factory.db.all('SELECT * FROM cases ORDER BY id')
        assert all(c['status']=='PENDING_REVIEW' for c in cases)
        first,second=cases[:2]
        assert factory.review_case(first['id'],'approve',1)=='OK'
        assert factory.review_case(first['id'],'approve',1)=='ALREADY_HANDLED'
        assert factory.db.one("SELECT count(*) n FROM queue_jobs WHERE type='screencast' AND status='QUEUED'")['n']==1
        assert factory.db.one("SELECT count(*) n FROM cases WHERE status='PENDING_REVIEW'")['n']==9
        old=second['processing_request_id']
        assert factory.review_case(second['id'],'retry',1)=='OK'
        assert factory.review_case(second['id'],'approve',1)=='STALE'
        new=factory.db.one('SELECT * FROM cases WHERE id=?',(second['id'],))['processing_request_id']
        assert old!=new
        await factory.drain('processing')
        for c in cases[1:]:
            factory.review_case(c['id'],'reject-final')
        # Explicitly mark the one pending render failed to test terminal accounting.
        factory.db.execute("UPDATE batch_slots SET status='FAILED' WHERE case_id=?",(first['id'],))
        factory.refresh_batches()
        assert factory.db.one('SELECT * FROM batches WHERE id=?',(batch,))['status']=='PARTIAL'
        assert len(factory.db.all('SELECT * FROM batch_slots'))==10
        assert worker.calls==11
        assert factory.db.one('SELECT count(*) n FROM expenses')['n']==11
        assert factory.db.one('SELECT sum(amount_nullable) amount FROM expenses')['amount']==13.75

def approved_screens(factory,count=2):
    return [factory.library.add(f'UNIT SCREEN {i}'.encode(),'screencast','video/mp4','APPROVED','test-only',metadata={'tags':[]}) for i in range(count)]

def test_mode_b_parallel_unique_novelty_and_zero_worker(factory):
    screens=approved_screens(factory)
    factory.library.add(b'UNIT AVATAR 2','animated_avatar','video/mp4','APPROVED','test-only')
    # A second selector uses another DB connection and runs concurrently.
    other=Factory(factory.config)
    with ThreadPoolExecutor(max_workers=2) as pool:
        batches=list(pool.map(lambda f:f.start_b(),[factory,other]))
    rows=factory.db.all('SELECT * FROM combinations ORDER BY created_at')
    assert len(rows)==20
    keys={(r['avatar_clip_asset_id'],r['screencast_asset_id'],r['hook_id'],r['scenario_id'],r['scenario_version'],r['creative_revision']) for r in rows}
    assert len(keys)==20
    assert len({(r['avatar_clip_asset_id'],r['screencast_asset_id']) for r in rows[:4]})==4
    assert factory._worker is None and other._worker is None
    empty=factory.start_b()
    assert factory.db.one('SELECT * FROM batches WHERE id=?',(empty,))['status']=='PARTIAL'
    assert factory.db.one('SELECT count(*) n FROM combinations WHERE batch_id=?',(empty,))['n']==0

def test_queue_restart_and_immutable_library(factory):
    factory.start_a()
    job=factory.db.claim(lease=-1)
    factory.db.execute('UPDATE queue_jobs SET owner_pid=2147483647 WHERE id=?',(job['id'],))
    recovered=DB(factory.db.path).claim()
    assert recovered['id']==job['id']
    assert factory.db.one('SELECT max(version) v FROM schema_version')['v']==2
    asset=factory.db.one('SELECT * FROM assets LIMIT 1')
    path=factory.library.file(asset['id'])
    path.write_bytes(b'corrupted fixture')
    with pytest.raises(ValueError,match='ASSET_HASH_MISMATCH'):
        factory.library.file(asset['id'])

async def test_bot_auth_callbacks_and_missing_delivery(factory):
    control=Controller(factory)
    assert control.command(7,'/mode_a 10')=='Доступ запрещён.'
    assert control.callback(7,'anything')=='Доступ запрещён.'
    assert factory.db.all('SELECT * FROM batches')==[]
    worker=FakeWorker(factory.config.data/'worker.db')
    async with serve(worker) as url:
        factory.config.worker_url=url
        control.command(42,'/mode_a 10')
        await factory.drain('processing')
        gateway=FakeGateway()
        assert await flush_notifications(factory,gateway)==10
        assert len(gateway.messages)==10
        data=gateway.messages[0]['buttons'][0][1]
        assert len(data.encode())<=64
        assert control.callback(42,data)=='OK'
        assert control.callback(42,data)=='ALREADY_HANDLED'
        # Delivery failure is durable and can be retried without processing again.
        case=factory.db.one("SELECT * FROM cases WHERE status='PENDING_REVIEW' LIMIT 1")
        factory.library.file(case['result_asset_id']).rename(factory.config.data/'removed-result.png')
        factory.db.execute("UPDATE notifications SET status='PENDING' WHERE entity_id=?",(case['processing_request_id'],))
        await flush_notifications(factory,gateway)
        assert factory.db.one('SELECT * FROM notifications WHERE entity_id=?',(case['processing_request_id'],))['status']=='FAILED'
        assert worker.calls==10

async def test_retry_limit_and_reconciliation_guard(factory):
    worker=FakeWorker(factory.config.data/'worker.db',outcome='FAILED')
    async with serve(worker) as url:
        factory.config.worker_url=url
        factory.start_a()
        await factory.drain('processing')
        case=factory.db.one('SELECT * FROM cases LIMIT 1')
        for n in range(3):
            factory.review_case(case['id'],'retry')
            await factory.drain('processing')
        with pytest.raises(ValueError,match='RETRY_LIMIT_EXCEEDED'):
            factory.review_case(case['id'],'retry')
        assert worker.calls==13
        factory.db.execute("UPDATE cases SET status='RECONCILIATION_REQUIRED' WHERE id=?",(case['id'],))
        with pytest.raises(ValueError,match='RECONCILIATION_REQUIRED'):
            factory.review_case(case['id'],'retry')
