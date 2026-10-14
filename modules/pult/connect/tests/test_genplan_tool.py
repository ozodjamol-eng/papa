import json
from test_connect import env, connect, token, rpc  # noqa: F401  (reuse fixtures)


def test_genplan_tool_targets_london_readonly(env):
    c, calls = env
    cid, v, cb, r = connect(c); tok = token(c, cid, v, cb, r)['access_token']
    tools = {t['name']: t for t in rpc(c, tok, 'tools/list').json()['result']['tools']}
    assert tools['nexus_genplan']['annotations']['readOnlyHint'] is True
    out = rpc(c, tok, 'tools/call', {'name': 'nexus_genplan', 'arguments': {}}).json()['result']
    assert out['isError'] is False and out['structuredContent']['status'] == 'succeeded'
    posts = [k['json'] for m, p, k in calls if m == 'POST' and p == '/api/tasks']
    assert posts and all(x['operation'] == 'genplan_status' and x['target'] == 'london' for x in posts)


def test_genplan_tool_hidden_without_checks_scope(env):
    c, _ = env
    cid, v, cb, r = connect(c, allow_checks=False); tok = token(c, cid, v, cb, r)['access_token']
    names = [t['name'] for t in rpc(c, tok, 'tools/list').json()['result']['tools']]
    assert 'nexus_genplan' not in names
