from test_connect import env, connect, token, rpc  # noqa: F401  (reuse fixtures)


def test_razvedka_tool_read_scope(env):
    c, calls = env
    orig = c.app.state.gw

    def gw(method, path, **kw):
        if path == '/api/razvedka':
            calls.append((method, path, kw))
            return {'generated': '15.10.2026 06:10', 'text': 'ЛИДЕРЫ', 'age_hours': 1.0}
        return orig(method, path, **kw)
    c.app.state.gw = gw
    cid, v, cb, r = connect(c, allow_checks=False); tok = token(c, cid, v, cb, r)['access_token']
    tools = {t['name']: t for t in rpc(c, tok, 'tools/list').json()['result']['tools']}
    assert tools['nexus_razvedka']['annotations']['readOnlyHint'] is True
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_razvedka', 'arguments': {}}).json()['result']
    assert out['isError'] is False and out['structuredContent']['generated'] == '15.10.2026 06:10'
    assert ('GET', '/api/razvedka', {}) in calls
    assert not any(m == 'POST' for m, _, _ in calls)
