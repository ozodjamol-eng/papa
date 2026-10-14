import json,time
from pathlib import Path
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from nexus_control.app import create_app,Settings
from nexus_control import core
from nexus_control.core import Store

HASH=PasswordHasher(time_cost=1,memory_cost=8192,parallelism=1).hash('safe-owner-password-987654')

def mk(tmp_path):
    return Store(tmp_path/'r.db',tmp_path/'st')

def test_attempt_counter_and_max_attempts(tmp_path):
    s=mk(tmp_path)
    t=s.create('ai','gateway_health')['id']
    for i in range(core.MAX_ATTEMPTS):
        row=s.claim_server(); assert row['id']==t
        Store(tmp_path/'r.db',tmp_path/'st')  # simulated crash+restart requeues
    s2=Store(tmp_path/'r.db',tmp_path/'st')
    assert s2.get(t)['status']=='failed'
    assert s2.get(t)['attempts']==core.MAX_ATTEMPTS
    assert s2.claim_server() is None

def test_finished_task_not_rerun_after_restart(tmp_path):
    s=mk(tmp_path)
    t=s.create('ai','gateway_health',idempotency='once-1')['id']
    s.finish(s.claim_server()['id'],'succeeded',{'ok':1})
    s2=mk(tmp_path)
    assert s2.claim_server() is None
    assert s2.create('ai','gateway_health',idempotency='once-1')['duplicate'] is True
    assert s2.get(t)['attempts']==1

def test_queued_task_expires(tmp_path):
    s=mk(tmp_path)
    t=s.create('ai','gateway_health')['id']
    with s.conn() as d: d.execute("UPDATE tasks SET created_at='2000-01-01T00:00:00+00:00' WHERE id=?",(t,))
    assert s.claim_server() is None
    assert s.get(t)['status']=='expired'

def test_queue_limit(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'QUEUE_LIMIT',3)
    s=mk(tmp_path)
    for _ in range(3): s.create('ai','gateway_health')
    with pytest.raises(ValueError,match='queue_full'): s.create('ai','gateway_health')

def test_agent_lease_max_attempts(tmp_path):
    s=mk(tmp_path)
    t=s.create('owner','device_health',target='pc1')['id']
    for _ in range(core.MAX_ATTEMPTS):
        assert s.next_agent('pc1')['id']==t
        with s.conn() as d: d.execute('UPDATE tasks SET lease_until=1 WHERE id=?',(t,))
    assert s.next_agent('pc1') is None
    assert s.get(t)['status']=='failed'

def test_housekeeping_prunes_old(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'AUDIT_KEEP',5)
    s=mk(tmp_path)
    for _ in range(12): s.create('ai','gateway_health')
    s.housekeeping()
    assert len(s.audit(100))<=5

def test_migration_on_old_schema(tmp_path):
    import sqlite3
    db=tmp_path/'old.db'
    c=sqlite3.connect(db)
    c.execute('''CREATE TABLE tasks (id TEXT PRIMARY KEY, operation TEXT NOT NULL, target TEXT NOT NULL,
      priority INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, idempotency TEXT NOT NULL UNIQUE,
      fingerprint TEXT NOT NULL, result TEXT, requested_by TEXT NOT NULL, approved_by TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL, lease_until REAL)''')
    c.commit();c.close()
    s=Store(db,tmp_path/'st')
    s.create('ai','gateway_health')
    assert s.claim_server()['attempts']==0

def test_worker_heartbeat_written(tmp_path):
    cfg=Settings(db=tmp_path/'h.db',state_dir=tmp_path/'st',owner_password_hash=HASH,ai_token='a'*40,
                 agents={},secure_cookies=False,run_worker=True)
    with TestClient(create_app(cfg)) as c:
        hb=tmp_path/'st'/'worker.heartbeat'
        for _ in range(40):
            if hb.exists():break
            time.sleep(.1)
        assert hb.exists() and time.time()-float(hb.read_text())<10
