"""Автопилот PAPA: ИИ ставит задачу papa_task для Франкфурта; шлюз проверяет только форму, сам ничего не выполняет."""
import pytest
from fastapi.testclient import TestClient
from nexus_control.app import create_app, Settings
from argon2 import PasswordHasher

HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash('safe-owner-password-987654')

H = {'Authorization': 'Bearer ' + 'a' * 40}


@pytest.fixture
def client(tmp_path):
    cfg = Settings(db=tmp_path / 't.db', state_dir=tmp_path / 's', owner_password_hash=HASH, ai_token='a' * 40,
                   agents={}, secure_cookies=False, run_worker=False)
    with TestClient(create_app(cfg)) as c:
        yield c


def task(c, payload, target='frankfurt'):
    return c.post('/api/tasks', headers=H, json={'operation': 'papa_task', 'target': target, 'payload': payload})


def test_ai_can_queue_task_and_read_it(client):
    r = task(client, {'task': 'genplan-restart', 'reason': 'новая панель'})
    assert r.status_code == 200 and r.json()['status'] == 'queued'
    one = client.get('/api/tasks/' + r.json()['id'], headers=H).json()
    assert one['status'] == 'queued' and 'genplan-restart' in one['payload']


@pytest.mark.parametrize('payload', [{'task': '../etc'}, {'task': 'a; rm -rf /'}, {'task': 'X'}, {'task': 'ok-name', 'cmd': 'ls'}, {}])
def test_bad_task_rejected(client, payload):
    assert task(client, payload).status_code == 422


def test_only_known_targets(client):
    assert task(client, {'task': 'status'}, target='tokyo').status_code == 422
    assert task(client, {'task': 'status'}, target='cloud').status_code == 422
    assert task(client, {'task': 'status'}, target='london').status_code == 200


def test_queue_limit(client):
    for i in range(5):
        assert task(client, {'task': f'status-{i}'}).status_code == 200
    assert task(client, {'task': 'status-x'}).status_code == 422


def test_unknown_task_id(client):
    assert client.get('/api/tasks/abc123', headers=H).status_code == 404
