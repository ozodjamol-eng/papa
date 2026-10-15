import base64, hashlib, json, re, secrets
from urllib.parse import urlparse, parse_qs
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from nexus_connect.app import create_app, Config

PW = 'owner-password-for-tests-123'
HASH = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash(PW)
BASE = 'https://nexus.example.ts.net:8443'
CB_CLAUDE = 'https://claude.ai/api/mcp/auth_callback'
CB_GPT = 'https://chatgpt.com/connector_platform_oauth_redirect'

@pytest.fixture
def env(tmp_path):
    cfg = Config(base_url=BASE, db=tmp_path / 'c.db', owner_hash=HASH, ai_token='a' * 40, secret='s' * 40)
    app = create_app(cfg)
    calls = []
    def fake_gw(method, path, **kw):
        calls.append((method, path, kw))
        if path == '/api/status': return {'gateway': 'online', 'queue': {}}
        if path == '/api/devices': return {'devices': []}
        if path == '/api/audit': return {'events': [{'i': i} for i in range(30)]}
        if method == 'POST' and path == '/api/tasks': return {'id': 't1', 'status': 'queued'}
        if path == '/api/tasks': return {'tasks': [{'id': 't1', 'status': 'succeeded', 'result': json.dumps({'healthy': True})}]}
        raise AssertionError(path)
    app.state.gw = fake_gw
    return TestClient(app, base_url=BASE), calls

def pkce():
    v = secrets.token_urlsafe(48)
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode()
    return v, c

def connect(c, cb=CB_CLAUDE, allow_checks=True, password=PW):
    r = c.post('/register', json={'client_name': 'Test', 'redirect_uris': [cb]}); assert r.status_code == 201
    cid = r.json()['client_id']; v, ch = pkce()
    q = {'client_id': cid, 'redirect_uri': cb, 'response_type': 'code', 'code_challenge': ch, 'code_challenge_method': 'S256', 'state': 'xyz', 'resource': BASE + '/mcp'}
    page = c.get('/authorize', params=q); assert page.status_code == 200
    ts = re.search(r'name="ts" value="(\d+)"', page.text).group(1); sig = re.search(r'name="sig" value="([0-9a-f]+)"', page.text).group(1)
    form = {**q, 'ts': ts, 'sig': sig, 'password': password, 'decision': 'allow', 'scope': ''}
    if allow_checks: form['allow_checks'] = '1'
    r = c.post('/authorize', data=form, follow_redirects=False)
    return cid, v, cb, r

def token(c, cid, v, cb, r):
    qs = parse_qs(urlparse(r.headers['location']).query)
    assert qs['state'] == ['xyz']
    t = c.post('/token', data={'grant_type': 'authorization_code', 'code': qs['code'][0], 'code_verifier': v, 'client_id': cid, 'redirect_uri': cb})
    assert t.status_code == 200, t.text
    return t.json()

def rpc(c, tok, method, params=None, i=1):
    return c.post('/mcp', headers={'Authorization': 'Bearer ' + tok}, json={'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params or {}})

def test_discovery(env):
    c, _ = env
    assert c.get('/.well-known/oauth-protected-resource').json()['resource'] == BASE + '/mcp'
    m = c.get('/.well-known/oauth-authorization-server').json()
    assert m['code_challenge_methods_supported'] == ['S256'] and m['registration_endpoint'] == BASE + '/register'

def test_mcp_requires_auth_with_metadata_hint(env):
    c, _ = env
    r = c.post('/mcp', json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'})
    assert r.status_code == 401 and 'resource_metadata=' in r.headers['www-authenticate']
    assert rpc(c, 'nxa_fake', 'tools/list').status_code == 401

def test_register_rejects_foreign_redirect(env):
    c, _ = env
    for bad in ['https://evil.com/cb', 'http://claude.ai/cb', 'https://claude.ai.evil.com/cb', 'https://user@claude.ai/cb']:
        assert c.post('/register', json={'redirect_uris': [bad]}).status_code == 400

def test_full_flow_claude_and_gpt(env):
    c, calls = env
    for cb, label in ((CB_CLAUDE, 'Claude'), (CB_GPT, 'ChatGPT')):
        cid, v, cb_, r = connect(c, cb)
        assert r.status_code == 303
        tok = token(c, cid, v, cb_, r)
        init = rpc(c, tok['access_token'], 'initialize', {'protocolVersion': '2025-06-18'}).json()
        assert init['result']['protocolVersion'] == '2025-06-18'
        names = [t['name'] for t in rpc(c, tok['access_token'], 'tools/list').json()['result']['tools']]
        assert names == ['nexus_status', 'nexus_tasks', 'nexus_audit', 'nexus_devices', 'nexus_run_check', 'nexus_genplan', 'nexus_razvedka', 'nexus_voronka']
        out = rpc(c, tok['access_token'], 'tools/call', {'name': 'nexus_run_check', 'arguments': {'check': 'host_health'}}).json()['result']
        assert out['isError'] is False and out['structuredContent']['status'] == 'succeeded'
        aud = rpc(c, tok['access_token'], 'tools/call', {'name': 'nexus_audit', 'arguments': {'limit': 5}}).json()['result']
        assert len(aud['structuredContent']['events']) == 5
        assert any(k.get('json', {}).get('idempotency_key', '').startswith(f'mcp-{label}-') for _, _, k in calls)

def test_wrong_password_no_code(env):
    c, _ = env
    _, _, _, r = connect(c, password='wrong')
    assert r.status_code == 200 and 'Неверный пароль' in r.text

def test_lockout_after_5(env):
    c, _ = env
    for _ in range(5): connect(c, password='wrong')
    _, _, _, r = connect(c)
    assert 'Слишком много попыток' in r.text

def test_deny_returns_access_denied(env):
    c, _ = env
    r = c.post('/register', json={'redirect_uris': [CB_CLAUDE]}); cid = r.json()['client_id']; v, ch = pkce()
    q = {'client_id': cid, 'redirect_uri': CB_CLAUDE, 'response_type': 'code', 'code_challenge': ch, 'code_challenge_method': 'S256', 'state': 's'}
    p = c.get('/authorize', params=q).text
    ts = re.search(r'name="ts" value="(\d+)"', p).group(1); sig = re.search(r'name="sig" value="([0-9a-f]+)"', p).group(1)
    r = c.post('/authorize', data={**q, 'ts': ts, 'sig': sig, 'decision': 'deny'}, follow_redirects=False)
    assert 'error=access_denied' in r.headers['location']

def test_tampered_form_rejected(env):
    c, _ = env
    cid, v, cb, r = connect(c)
    r2 = c.post('/register', json={'redirect_uris': [CB_CLAUDE]}); cid2 = r2.json()['client_id']
    _, ch = pkce()
    form = {'client_id': cid2, 'redirect_uri': CB_CLAUDE, 'response_type': 'code', 'code_challenge': ch, 'code_challenge_method': 'S256', 'state': 'x',
            'ts': '9999999999', 'sig': 'deadbeef', 'password': PW, 'decision': 'allow'}
    assert c.post('/authorize', data=form, follow_redirects=False).status_code == 400

def test_pkce_and_code_reuse(env):
    c, _ = env
    cid, v, cb, r = connect(c)
    code = parse_qs(urlparse(r.headers['location']).query)['code'][0]
    assert c.post('/token', data={'grant_type': 'authorization_code', 'code': code, 'code_verifier': 'x' * 50, 'client_id': cid}).status_code == 400
    # code is single-use even after a failed attempt
    assert c.post('/token', data={'grant_type': 'authorization_code', 'code': code, 'code_verifier': v, 'client_id': cid}).status_code == 400

def test_scope_read_only_hides_checks(env):
    c, _ = env
    cid, v, cb, r = connect(c, allow_checks=False)
    tok = token(c, cid, v, cb, r)['access_token']
    names = [t['name'] for t in rpc(c, tok, 'tools/list').json()['result']['tools']]
    assert 'nexus_run_check' not in names
    assert 'error' in rpc(c, tok, 'tools/call', {'name': 'nexus_run_check', 'arguments': {'check': 'host_health'}}).json()

def test_no_critical_ops(env):
    c, calls = env
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    for bad in ['restart_service_request', 'deploy_request', 'policy_repair', 'telegram_publish_request']:
        out = rpc(c, tok, 'tools/call', {'name': 'nexus_run_check', 'arguments': {'check': bad}}).json()['result']
        assert out['isError'] is True
    assert not any(m == 'POST' and k.get('json', {}).get('operation') not in ('gateway_health', 'host_health', 'policy_verify') for m, _, k in calls)
    assert 'error' in rpc(c, tok, 'tools/call', {'name': 'shell', 'arguments': {}}).json()

def test_refresh_rotation_and_revoke(env, tmp_path):
    c, _ = env
    cid, v, cb, r = connect(c); t = token(c, cid, v, cb, r)
    n = c.post('/token', data={'grant_type': 'refresh_token', 'refresh_token': t['refresh_token'], 'client_id': cid}); assert n.status_code == 200
    assert c.post('/token', data={'grant_type': 'refresh_token', 'refresh_token': t['refresh_token'], 'client_id': cid}).status_code == 400
    st = c.app.state.store
    with st.c() as d: d.execute('UPDATE clients SET revoked=1 WHERE id=?', (cid,))
    assert rpc(c, n.json()['access_token'], 'tools/list').status_code == 401

def test_notification_and_batch(env):
    c, _ = env
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    r = c.post('/mcp', headers={'Authorization': 'Bearer ' + tok}, json={'jsonrpc': '2.0', 'method': 'notifications/initialized'})
    assert r.status_code == 202
