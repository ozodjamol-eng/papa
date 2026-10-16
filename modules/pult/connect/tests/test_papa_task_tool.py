import json
from test_connect import env, connect, token, rpc  # noqa: F401  (reuse fixtures)


def test_papa_task_queues_for_frankfurt_and_returns_output(env):
    c, calls = env
    app_gw = c.app.state.gw

    def gw(method, path, **kw):
        if method == 'POST' and path == '/api/tasks':
            calls.append((method, path, kw)); return {'id': 'abcdef0123', 'status': 'queued'}
        if path == '/api/tasks/abcdef0123':
            return {'id': 'abcdef0123', 'status': 'succeeded', 'result': json.dumps({'rc': 0, 'output': '== DONE'})}
        return app_gw(method, path, **kw)
    c.app.state.gw = gw
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    tools = {t['name']: t for t in rpc(c, tok, 'tools/list').json()['result']['tools']}
    assert 'nexus_papa_task' in tools and 'nexus_papa_result' in tools
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_papa_task', 'arguments': {'task': 'genplan-restart', 'reason': 'тест'}}).json()['result']
    assert out['isError'] is False and out['structuredContent']['status'] == 'succeeded'
    assert out['structuredContent']['output'] == '== DONE'
    sent = [k['json'] for m, p, k in calls if m == 'POST' and p == '/api/tasks'][-1]
    assert sent['operation'] == 'papa_task' and sent['target'] == 'frankfurt' and sent['payload']['task'] == 'genplan-restart'


def test_papa_task_bad_name_rejected(env):
    c, calls = env
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_papa_task', 'arguments': {'task': 'x; rm -rf /', 'reason': 'зло'}}).json()
    assert ('error' in out) or out['result']['isError'] is True
    assert not [1 for m, p, k in calls if m == 'POST' and p == '/api/tasks']


def test_papa_task_hidden_without_checks_scope(env):
    c, _ = env
    cid, v, cb, r = connect(c, allow_checks=False); tok = token(c, cid, v, cb, r)['access_token']
    names = [t['name'] for t in rpc(c, tok, 'tools/list').json()['result']['tools']]
    assert 'nexus_papa_task' not in names and 'nexus_papa_result' in names


def _fake(c, calls, status='ready'):
    app_gw = c.app.state.gw

    def gw(method, path, **kw):
        if method == 'POST' and path == '/api/tasks':
            calls.append((method, path, kw)); return {'id': 'abcdef0456', 'status': 'queued'}
        if path == '/api/tasks/abcdef0456':
            return {'id': 'abcdef0456', 'status': status, 'target': 'london', 'result': None}
        return app_gw(method, path, **kw)
    c.app.state.gw = gw


def test_papa_task_for_london(env, monkeypatch):
    c, calls = env
    _fake(c, calls, status='succeeded')
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_papa_task',
                                     'arguments': {'task': 'london-diagnose', 'reason': 'тест', 'server': 'london'}}).json()['result']
    assert out['isError'] is False and out['structuredContent']['server'] == 'london'
    sent = [k['json'] for m, p, k in calls if m == 'POST' and p == '/api/tasks'][-1]
    assert sent['target'] == 'london' and sent['payload'] == {'task': 'london-diagnose', 'reason': 'тест'}


def test_papa_task_unknown_server_rejected(env):
    c, calls = env
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_papa_task',
                                     'arguments': {'task': 'status', 'reason': 'x', 'server': 'tokyo'}}).json()
    assert ('error' in out) or out['result']['isError'] is True
    assert not [1 for m, p, k in calls if m == 'POST' and p == '/api/tasks']
