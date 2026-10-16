from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import time
import uuid
import os
import psutil

def uid():
    return str(uuid.uuid4())

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS assets(
 id TEXT PRIMARY KEY, type TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL,
 mime TEXT NOT NULL, width INTEGER, height INTEGER, duration REAL,
 rights_status TEXT NOT NULL, approved_at REAL, source_id TEXT,
 created_at REAL NOT NULL, status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
 UNIQUE(type,sha256));
CREATE TABLE IF NOT EXISTS photo_pairs(
 id TEXT PRIMARY KEY, original_asset_id TEXT NOT NULL REFERENCES assets(id),
 reference_asset_id TEXT NOT NULL REFERENCES assets(id), tags_json TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS batches(
 id TEXT PRIMARY KEY, mode TEXT NOT NULL, target_count INTEGER NOT NULL,
 status TEXT NOT NULL, created_at REAL NOT NULL, finished_at REAL);
CREATE TABLE IF NOT EXISTS cases(
 id TEXT PRIMARY KEY, pair_id TEXT NOT NULL REFERENCES photo_pairs(id),
 processing_request_id TEXT, result_asset_id TEXT REFERENCES assets(id),
 screencast_asset_id TEXT REFERENCES assets(id), pipeline_version TEXT,
 status TEXT NOT NULL, reviewed_at REAL);
CREATE TABLE IF NOT EXISTS batch_slots(
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
 slot_no INTEGER NOT NULL, case_id TEXT REFERENCES cases(id), attempt_no INTEGER NOT NULL DEFAULT 0,
 stage TEXT NOT NULL, status TEXT NOT NULL, UNIQUE(batch_id,slot_no));
CREATE TABLE IF NOT EXISTS processing_attempts(
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), request_id TEXT NOT NULL UNIQUE,
 attempt_no INTEGER NOT NULL, worker_status TEXT NOT NULL, generation_cost_amount REAL,
 cost_status TEXT NOT NULL DEFAULT 'unknown', created_at REAL NOT NULL,
 UNIQUE(case_id,attempt_no));
CREATE TABLE IF NOT EXISTS hooks(
 id TEXT PRIMARY KEY, text TEXT NOT NULL, tags_json TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scenarios(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
 definition_json TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS combinations(
 id TEXT PRIMARY KEY, batch_id TEXT NOT NULL REFERENCES batches(id),
 slot_id TEXT REFERENCES batch_slots(id), avatar_clip_asset_id TEXT NOT NULL REFERENCES assets(id),
 screencast_asset_id TEXT NOT NULL REFERENCES assets(id), hook_id TEXT NOT NULL REFERENCES hooks(id),
 scenario_id TEXT NOT NULL REFERENCES scenarios(id), scenario_version INTEGER NOT NULL,
 creative_revision INTEGER NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL,
 UNIQUE(avatar_clip_asset_id,screencast_asset_id,hook_id,scenario_id,scenario_version,creative_revision));
CREATE TABLE IF NOT EXISTS video_jobs(
 id TEXT PRIMARY KEY, combination_id TEXT NOT NULL UNIQUE REFERENCES combinations(id),
 final_asset_id TEXT REFERENCES assets(id), duration REAL, output_status TEXT NOT NULL,
 review_status TEXT NOT NULL, error_code TEXT, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS expenses(
 id TEXT PRIMARY KEY, source_call_id TEXT NOT NULL UNIQUE, source_type TEXT NOT NULL,
 batch_id TEXT NOT NULL REFERENCES batches(id), asset_id TEXT REFERENCES assets(id),
 currency TEXT NOT NULL, amount_nullable REAL, cost_status TEXT NOT NULL,
 provider TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS queue_jobs(
 id TEXT PRIMARY KEY, type TEXT NOT NULL, dedupe_key TEXT NOT NULL UNIQUE,
 payload_json TEXT NOT NULL, status TEXT NOT NULL, lease_until REAL,
 attempt_count INTEGER NOT NULL DEFAULT 0, error TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, entity_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING', error TEXT, created_at REAL NOT NULL,
 UNIQUE(kind,entity_id));
"""

class DB:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.executescript(SCHEMA)
            c.execute('BEGIN IMMEDIATE')
            columns={r[1] for r in c.execute('PRAGMA table_info(queue_jobs)')}
            if 'owner_pid' not in columns:
                c.execute('ALTER TABLE queue_jobs ADD COLUMN owner_pid INTEGER')
                c.execute('ALTER TABLE queue_jobs ADD COLUMN owner_started REAL')
            c.execute('INSERT OR IGNORE INTO schema_version VALUES(2)')

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=30000")
        c.execute("PRAGMA journal_mode=WAL")
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    @contextmanager
    def transaction(self):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            yield c

    def one(self, sql, params=()):
        with self.connect() as c:
            r = c.execute(sql, params).fetchone()
            return dict(r) if r else None

    def all(self, sql, params=()):
        with self.connect() as c:
            return [dict(r) for r in c.execute(sql, params)]

    def execute(self, sql, params=()):
        with self.connect() as c:
            return c.execute(sql, params).rowcount

    @staticmethod
    def enqueue(c, kind, key, payload):
        c.execute("INSERT OR IGNORE INTO queue_jobs(id,type,dedupe_key,payload_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                  (uid(), kind, key, json.dumps(payload), "QUEUED", time.time(), time.time()))

    @staticmethod
    def notify(c, kind, entity):
        c.execute("INSERT OR IGNORE INTO notifications(id,kind,entity_id,created_at) VALUES(?,?,?,?)",
                  (uid(), kind, entity, time.time()))

    def claim(self, lease=3600, lane=None):
        now = time.time()
        with self.transaction() as c:
            for running in c.execute("SELECT * FROM queue_jobs WHERE status='RUNNING'").fetchall():
                alive=False
                if running['owner_pid']:
                    try:
                        alive=abs(psutil.Process(running['owner_pid']).create_time()-running['owner_started'])<.1
                    except (psutil.NoSuchProcess,psutil.AccessDenied):
                        pass
                expired=running['lease_until'] is not None and running['lease_until']<now
                if not alive and (running['owner_pid'] is not None or expired):
                    c.execute("UPDATE queue_jobs SET status='QUEUED',lease_until=NULL WHERE id=?",(running['id'],))
            condition = " AND type='processing'" if lane=='processing' else (" AND type IN ('screencast','compose')" if lane=='heavy' else '')
            row = c.execute("SELECT * FROM queue_jobs WHERE status='QUEUED'"+condition+" ORDER BY CASE type WHEN 'screencast' THEN 0 WHEN 'compose' THEN 1 ELSE 2 END,created_at LIMIT 1").fetchone()
            if not row:
                return None
            c.execute("UPDATE queue_jobs SET status='RUNNING',lease_until=?,attempt_count=attempt_count+1,updated_at=?,owner_pid=?,owner_started=? WHERE id=?", (now+lease, now, os.getpid(),psutil.Process().create_time(),row['id']))
            return dict(row)

    def finish(self, job_id, error=None):
        self.execute("UPDATE queue_jobs SET status=?,error=?,lease_until=NULL,updated_at=? WHERE id=?",
                     ("FAILED" if error else "DONE", error, time.time(), job_id))
