"""Исполнитель Лондона: видит только papa_task target=london в статусе ready и только со своим токеном."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from nexus_control.app import create_app, Settings
from argon2 import PasswordHasher

HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash('safe-owner-password-987654')
AI = {'Authorization': 'Bearer ' + 'a' * 40}
RUN = {'Authorization': 'Bearer ' + 'r' * 40, 'X-Device-ID': 'london-runner'}
RO = {'Authorization': 'Bearer ' + 'l' * 40, 'X-Device-ID': 'london'}


@pytest.fixture
def env(tmp_path):
    db = tmp_path / 't.db'
    cfg = Settings(db=db, state_dir=tmp_path / 's', owner_password_hash=HASH, ai_token='a' * 40,
                   agents={'london-runner': 'r' * 40, 'london': 'l' * 40}, secure_cookies=False, run_worker=False)
    with TestClient(create_app(cfg)) as c:
        yield c, db


def queue(c, task='london-diagnose', target='london'):
    r = c.post('/api/tasks', headers=AI, json={'operation': 'papa_task', 'target': target,
                                               'payload': {'task': task, 'reason': 'проверка'}})
    assert r.status_code == 200
    return r.json()['id']


def set_status(db, tid, status):
    with sqlite3.connect(db) as d:
        d.execute('UPDATE tasks SET status=? WHERE id=?', (status, tid))


def test_queued_task_is_not_given_before_autopilot_allows(env):
    c, db = env
    queue(c)
    assert c.post('/api/runner/next', headers=RUN).json() == {'task': None}


def test_ready_task_runs_once_and_finishes(env):
    c, db = env
    tid = queue(c)
    set_status(db, tid, 'ready')
    t = c.post('/api/runner/next', headers=RUN).json()['task']
    assert t == {'id': tid, 'task': 'london-diagnose', 'reason': 'проверка'}
    assert c.post('/api/runner/next', headers=RUN).json() == {'task': None}
    r = c.post('/api/runner/result', headers=RUN, json={'task_id': tid, 'ok': True, 'result': {'rc': 0, 'summary': 'ok'}})
    assert r.status_code == 200
    one = c.get('/api/tasks/' + tid, headers=AI).json()
    assert one['status'] == 'succeeded'
    assert c.post('/api/runner/result', headers=RUN, json={'task_id': tid, 'ok': True, 'result': {}}).status_code == 409


def test_frankfurt_tasks_never_go_to_london(env):
    c, db = env
    tid = queue(c, target='frankfurt')
    set_status(db, tid, 'ready')
    assert c.post('/api/runner/next', headers=RUN).json() == {'task': None}


def test_read_only_agent_cannot_use_runner_api(env):
    c, db = env
    tid = queue(c)
    set_status(db, tid, 'ready')
    assert c.post('/api/runner/next', headers=RO).status_code == 403
    assert c.post('/api/runner/next', headers={'X-Device-ID': 'london-runner'}).status_code == 401
    assert c.post('/api/runner/next', headers={**RUN, 'Authorization': 'Bearer ' + 'x' * 40}).status_code == 401


def test_ai_cannot_call_runner_api(env):
    c, db = env
    assert c.post('/api/runner/next', headers=AI).status_code == 401


def test_result_size_limited(env):
    c, db = env
    tid = queue(c)
    set_status(db, tid, 'ready')
    c.post('/api/runner/next', headers=RUN)
    big = {'output': 'x' * 40000}
    assert c.post('/api/runner/result', headers=RUN, json={'task_id': tid, 'ok': True, 'result': big}).status_code == 409
