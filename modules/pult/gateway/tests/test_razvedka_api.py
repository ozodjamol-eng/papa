import json
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from nexus_control.app import create_app, Settings

HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash('safe-owner-password-987654')
AI = {'Authorization': 'Bearer ' + 'a' * 40}


def client(tmp_path):
    cfg = Settings(db=tmp_path / 'g.db', state_dir=tmp_path / 'st', owner_password_hash=HASH, ai_token='a' * 40,
                   agents={}, secure_cookies=False, run_worker=False)
    return TestClient(create_app(cfg))


def test_razvedka_requires_auth_and_reports_missing(tmp_path, monkeypatch):
    monkeypatch.setenv('NEXUS_RAZVEDKA_REPORT', str(tmp_path / 'latest.json'))
    with client(tmp_path) as c:
        assert c.get('/api/razvedka').status_code == 401
        assert c.get('/api/razvedka', headers={'Authorization': 'Bearer ' + 'x' * 40}).status_code == 401
        assert c.get('/api/razvedka', headers=AI).status_code == 404


def test_razvedka_returns_report(tmp_path, monkeypatch):
    p = tmp_path / 'latest.json'
    p.write_text(json.dumps({'generated': '15.10.2026 06:10', 'text': 'ЛИДЕРЫ ...'}, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setenv('NEXUS_RAZVEDKA_REPORT', str(p))
    with client(tmp_path) as c:
        r = c.get('/api/razvedka', headers=AI)
        assert r.status_code == 200
        body = r.json()
        assert body['generated'] == '15.10.2026 06:10' and 'age_hours' in body


def test_razvedka_broken_file(tmp_path, monkeypatch):
    p = tmp_path / 'latest.json'
    p.write_text('{broken', encoding='utf-8')
    monkeypatch.setenv('NEXUS_RAZVEDKA_REPORT', str(p))
    with client(tmp_path) as c:
        assert c.get('/api/razvedka', headers=AI).status_code == 503
