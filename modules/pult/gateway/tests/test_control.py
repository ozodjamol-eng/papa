import json,os,sqlite3,tempfile,time
from pathlib import Path
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from nexus_control.app import create_app,Settings
from nexus_control.core import Store,POLICY,safe_server_execute
from nexus_control.agent import perform

HASH=PasswordHasher(time_cost=1,memory_cost=8192,parallelism=1).hash('safe-owner-password-987654')

@pytest.fixture
def state(tmp_path):
    cfg=Settings(db=tmp_path/'test.db',state_dir=tmp_path/'state',owner_password_hash=HASH,
                 ai_token='a'*40,agents={'office-windows':'w'*40,'my-mac':'m'*40},secure_cookies=False,run_worker=False)
    app=create_app(cfg)
    with TestClient(app) as client:
        yield app,client

@pytest.fixture
def owner(state):
    app,client=state
    r=client.post('/api/login',json={'password':'safe-owner-password-987654'})
    assert r.status_code==200
    csrf=r.json()['csrf']
    return app,client,{'X-CSRF-Token':csrf}

def test_start_requires_password(tmp_path):
    with pytest.raises(RuntimeError,match='NEXUS_OWNER_PASSWORD_HASH'):
        Settings(db=tmp_path/'db',state_dir=tmp_path/'state',owner_password_hash='')

def test_password_wrong_and_rate_limited(state):
    _,client=state
    for _ in range(5):assert client.post('/api/login',json={'password':'x'}).status_code==401
    assert client.post('/api/login',json={'password':'x'}).status_code==429

def test_unauthenticated_data_forbidden(state):
    _,client=state
    for path in ['status','tasks','devices','audit','me']:
        assert client.get('/api/'+path).status_code==401

def test_owner_cookie_secure_flags(state):
    _,client=state
    r=client.post('/api/login',json={'password':'safe-owner-password-987654'})
    cookies=r.headers.get_list('set-cookie')
    session=next(x for x in cookies if 'nexus_session=' in x)
    assert 'httponly' in session.lower() and 'samesite=strict' in session.lower()
    assert client.get('/api/me').json()['role']=='owner'

def test_unauthorized_post_no_action(state):
    app,client=state
    assert client.post('/api/tasks',json={'operation':'gateway_health'}).status_code==401
    assert not app.state.store.tasks()

def test_owner_requires_csrf(state):
    app,client=state
    client.post('/api/login',json={'password':'safe-owner-password-987654'})
    assert client.post('/api/tasks',json={'operation':'gateway_health'}).status_code==403
    assert not app.state.store.tasks()

def test_owner_safe_task_runs(owner):
    app,client,headers=owner
    r=client.post('/api/tasks',json={'operation':'gateway_health'},headers=headers)
    assert r.status_code==200
    done=app.state.execute_once()
    assert done['status']=='succeeded'
    assert done['result']['production_genplan_verified'] is False

def test_owner_policy_repair(owner):
    app,client,headers=owner
    app.state.store.policy_path.write_text('{"mode":"unrestricted"}')
    task=client.post('/api/tasks',json={'operation':'policy_repair'},headers=headers).json()
    app.state.execute_once()
    assert app.state.store.get(task['id'])['status']=='succeeded'
    assert app.state.store.policy()['ok']

def test_owner_policy_repair_symlink(owner,tmp_path):
    app,client,headers=owner
    p=app.state.store.policy_path;p.unlink()
    outside=tmp_path/'outside';outside.write_text('unchanged')
    p.symlink_to(outside)
    client.post('/api/tasks',json={'operation':'policy_repair'},headers=headers)
    result=app.state.execute_once()
    assert result['status']=='failed'
    assert outside.read_text()=='unchanged'

def test_urgent_priority_and_no_publishing(owner):
    app,client,headers=owner
    client.post('/api/tasks',json={'operation':'gateway_health'},headers=headers)
    urgent=client.post('/api/tasks',json={'operation':'urgent_prepare','payload':{'post_id':780}},headers=headers).json()
    done=app.state.execute_once()
    assert done['id']==urgent['id'] and done['result']['bypasses_genplan']
    assert done['result']['published'] is False and done['result']['telegram_ack'] is None

def test_urgent_requires_explicit_id(owner):
    _,client,headers=owner
    assert client.post('/api/tasks',json={'operation':'urgent_prepare','payload':{'text':'Диққат'}},headers=headers).status_code==422

def test_idempotency_same_request(owner):
    app,client,headers=owner
    args={'operation':'gateway_health','idempotency_key':'constant-key'}
    a=client.post('/api/tasks',json=args,headers=headers).json()
    b=client.post('/api/tasks',json=args,headers=headers).json()
    assert a['id']==b['id'] and b['duplicate'] is True
    assert len(app.state.store.tasks())==1

def test_idempotency_conflict(owner):
    _,client,headers=owner
    a={'operation':'urgent_prepare','payload':{'post_id':780},'idempotency_key':'key-1234'}
    assert client.post('/api/tasks',json=a,headers=headers).status_code==200
    a['payload']['post_id']=781
    assert client.post('/api/tasks',json=a,headers=headers).status_code==422

def test_disallow_arbitrary_shell(owner):
    app,client,headers=owner
    assert client.post('/api/tasks',json={'operation':'shell','payload':{'cmd':'whoami'}},headers=headers).status_code==422
    assert len(app.state.store.tasks())==0

def test_critical_requires_owner_and_never_executes(owner):
    app,client,headers=owner
    task=client.post('/api/tasks',json={'operation':'restart_service_request','target':'cloud','payload':{'reason':'test'}},headers=headers).json()
    assert task['status']=='awaiting_approval'
    assert app.state.execute_once() is None
    assert client.post(f"/api/tasks/{task['id']}/approve",json={'confirmation':'APPROVE:wrong'},headers=headers).status_code==422
    ok=client.post(f"/api/tasks/{task['id']}/approve",json={'confirmation':f"APPROVE:{task['id']}"},headers=headers).json()
    assert ok['status']=='approved_not_executable' and not ok['executed']
    assert app.state.execute_once() is None

def test_ai_read_and_safe_write_only(state):
    _,client=state
    h={'Authorization':'Bearer '+'a'*40}
    assert client.get('/api/status',headers=h).status_code==200
    assert client.post('/api/tasks',headers=h,json={'operation':'gateway_health'}).status_code==200
    assert client.post('/api/tasks',headers=h,json={'operation':'os_repair_request','payload':{'reason':'try'}}).status_code==403

def test_wrong_ai_key_denied(state):
    _,client=state
    assert client.get('/api/status',headers={'Authorization':'Bearer '+'x'*40}).status_code==401

def test_cross_origin_denied(owner):
    _,client,headers=owner
    headers['Origin']='https://attacker.example'
    assert client.post('/api/tasks',headers=headers,json={'operation':'gateway_health'}).status_code==403

def test_agent_authentication_and_heartbeat(state):
    _,client=state
    h={'X-Device-ID':'office-windows','Authorization':'Bearer '+'w'*40}
    assert client.post('/api/agent/hello',headers=h,json={'platform':'Windows','hostname':'office','details':{}}).status_code==200
    assert client.post('/api/agent/hello',headers={**h,'Authorization':'Bearer '+'z'*40},json={'platform':'Windows','hostname':'x'}).status_code==401
    assert client.post('/api/agent/next',headers=h).json()['task'] is None
    # agents cannot access owner dashboard API
    assert client.get('/api/status',headers=h).status_code==401

def test_agent_end_to_end(owner):
    app,client,csrf=owner
    task=client.post('/api/tasks',headers=csrf,json={'operation':'device_health','target':'office-windows'}).json()
    h={'X-Device-ID':'office-windows','Authorization':'Bearer '+'w'*40}
    job=client.post('/api/agent/next',headers=h).json()['task']
    assert job['id']==task['id']
    report=perform(job['operation'],job['payload'])
    assert report['source']=='local_agent'
    assert client.post('/api/agent/result',headers=h,json={'task_id':job['id'],'ok':True,'result':report}).status_code==200
    assert app.state.store.get(task['id'])['status']=='succeeded'

def test_agent_cannot_submit_other_device_result(owner):
    app,client,csrf=owner
    t=client.post('/api/tasks',headers=csrf,json={'operation':'startup_audit','target':'office-windows'}).json()
    w={'X-Device-ID':'office-windows','Authorization':'Bearer '+'w'*40}
    m={'X-Device-ID':'my-mac','Authorization':'Bearer '+'m'*40}
    client.post('/api/agent/next',headers=w)
    assert client.post('/api/agent/result',headers=m,json={'task_id':t['id'],'ok':True,'result':{}}).status_code==409

def test_agent_no_shell():
    with pytest.raises(PermissionError):perform('shell',{'command':'pwd'})

def test_agent_startup_readonly():
    result=perform('startup_audit',{})
    assert result['checked'] and 'read-only' in result['scope']

def test_logout_invalidates_session(owner):
    _,client,csrf=owner
    assert client.post('/api/logout',headers=csrf).status_code==200
    assert client.get('/api/me').status_code==401

def test_safety_no_unapproved_executor():
    from nexus_control.core import SAFE_AGENT, SAFE_SERVER, RESTRICTED
    assert not ({'shell','ssh','telegram_publish','deploy'} & (SAFE_AGENT | SAFE_SERVER))
    assert not (RESTRICTED & (SAFE_SERVER | SAFE_AGENT))

def test_device_offline_when_stale(owner):
    app,client,csrf=owner
    s=app.state.store
    s.seen('office-windows','Windows','w',{})
    with s.conn() as d:d.execute('UPDATE devices SET last_seen=? WHERE id=?',(time.time()-120,'office-windows'))
    r=client.get('/api/devices').json()['devices'][0]
    assert r['online'] is False

def test_safe_job_recovery(tmp_path):
    s=Store(tmp_path/'tasks.db',tmp_path/'state')
    a=s.create('owner','gateway_health')
    with s.conn() as d:d.execute("UPDATE tasks SET status='running' WHERE id=?",(a['id'],))
    s.bootstrap()
    assert s.get(a['id'])['status']=='queued'

def test_approved_critical_not_requeued(tmp_path):
    s=Store(tmp_path/'tasks.db',tmp_path/'state')
    a=s.create('owner','deploy_request',{'reason':'test'})
    s.approve(a['id'],'owner',f"APPROVE:{a['id']}")
    s.bootstrap()
    assert s.get(a['id'])['status']=='approved_not_executable'
