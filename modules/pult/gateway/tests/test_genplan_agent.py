from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from nexus_control.app import create_app, Settings
from nexus_control.core import SAFE_AGENT, Store

HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash('safe-owner-password-987654')
AI = {'Authorization': 'Bearer ' + 'a' * 40}
LON = {'Authorization': 'Bearer ' + 'L' * 40, 'X-Device-ID': 'london'}


def client(tmp_path):
    cfg = Settings(db=tmp_path / 'g.db', state_dir=tmp_path / 'st', owner_password_hash=HASH, ai_token='a' * 40,
                   agents={'london': 'L' * 40}, secure_cookies=False, run_worker=False)
    return TestClient(create_app(cfg))


def test_genplan_status_is_agent_only_readonly_op():
    assert 'genplan_status' in SAFE_AGENT


def test_full_agent_roundtrip(tmp_path):
    with client(tmp_path) as c:
        r = c.post('/api/tasks', headers=AI, json={'operation': 'genplan_status', 'target': 'london'})
        assert r.status_code == 200, r.text
        tid = r.json()['id']
        assert c.post('/api/agent/hello', headers=LON, json={'platform': 'Linux', 'hostname': 'x', 'details': {}}).json()['ok']
        task = c.post('/api/agent/next', headers=LON).json()['task']
        assert task['id'] == tid and task['operation'] == 'genplan_status'
        assert c.post('/api/agent/result', headers=LON, json={'task_id': tid, 'ok': True, 'result': {'genplan': 'ok'}}).status_code == 200
        row = next(t for t in c.get('/api/tasks', headers=AI).json()['tasks'] if t['id'] == tid)
        assert row['status'] == 'succeeded'
        assert any(d['id'] == 'london' and d['online'] for d in c.get('/api/devices', headers=AI).json()['devices'])


def test_genplan_status_rejected_for_cloud_and_other_devices(tmp_path):
    with client(tmp_path) as c:
        assert c.post('/api/tasks', headers=AI, json={'operation': 'genplan_status'}).status_code == 422
        tid = c.post('/api/tasks', headers=AI, json={'operation': 'genplan_status', 'target': 'london'}).json()['id']
        bad = {'Authorization': 'Bearer ' + 'L' * 40, 'X-Device-ID': 'office-windows'}
        assert c.post('/api/agent/next', headers=bad).status_code == 401
        assert c.post('/api/agent/next', headers={'X-Device-ID': 'london'}).status_code == 401
        task = c.post('/api/agent/next', headers=LON).json()['task']
        assert task['id'] == tid


def test_agent_cannot_finish_foreign_or_restricted(tmp_path):
    s = Store(tmp_path / 'r.db', tmp_path / 'st')
    t = s.create('owner', 'restart_service_request', {'reason': 'x'}, 'london')
    assert s.next_agent('london') is None
    try:
        s.agent_finish('london', t['id'], True, {})
        raise AssertionError('must fail')
    except ValueError as e:
        assert str(e) == 'task_not_claimed'


def test_oversized_result_rejected(tmp_path):
    s = Store(tmp_path / 'r.db', tmp_path / 'st')
    s.create('ai', 'genplan_status', {}, 'london')
    n = s.next_agent('london')
    try:
        s.agent_finish('london', n['id'], True, {'x': 'y' * 20000})
        raise AssertionError('must fail')
    except ValueError as e:
        assert str(e) == 'invalid_result'
