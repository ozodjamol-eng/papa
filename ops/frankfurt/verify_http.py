"""Live HTTP verification against the running gateway. Prints only status codes, never secrets."""
import json,sys,time,uuid
from pathlib import Path
import httpx
env=dict(l.split('=',1) for l in Path('/etc/nexus-private-control.env').read_text().splitlines() if '=' in l)
tok=env['NEXUS_AI_TOKEN'].strip()
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8788'
ai={'Authorization':'Bearer '+tok}
out={'base':base}
with httpx.Client(base_url=base,timeout=10,trust_env=False) as c:
    out['root']=c.get('/').status_code
    out['noauth']={p:c.get('/api/'+p).status_code for p in ('status','tasks','devices','audit','me')}
    out['noauth_post_task']=c.post('/api/tasks',json={'operation':'gateway_health'}).status_code
    out['bad_bearer']=c.get('/api/status',headers={'Authorization':'Bearer '+'x'*48}).status_code
    out['wrong_owner_password']=c.post('/api/login',json={'password':'definitely-wrong-'+uuid.uuid4().hex}).status_code
    out['agent_no_token']=c.post('/api/agent/next',headers={'X-Device-Id':'pc1'}).status_code
    out['ai_role']=c.get('/api/me',headers=ai).json().get('role')
    out['ai_status']=c.get('/api/status',headers=ai).status_code
    out['ai_critical']={op:c.post('/api/tasks',headers=ai,json={'operation':op,'payload':{'reason':'verification'}}).status_code
        for op in ('restart_service_request','deploy_request','telegram_publish_request','delete_data_request')}
    out['ai_approve']=c.post('/api/tasks/x/approve',headers=ai,json={'confirmation':'APPROVE:x'}).status_code
    out['ai_unknown_op']=c.post('/api/tasks',headers=ai,json={'operation':'shell'}).status_code
    run=uuid.uuid4().hex[:8]; cycles=[]
    for i in range(5):
        r=c.post('/api/tasks',headers=ai,json={'operation':'host_health','idempotency_key':f'verify-{run}-{i}'})
        tid=r.json()['id'];t0=time.time();st=None
        while time.time()-t0<15:
            row=next(x for x in c.get('/api/tasks',headers=ai).json()['tasks'] if x['id']==tid)
            st=row['status']
            if st in ('succeeded','failed'):break
            time.sleep(.3)
        res=json.loads(row['result'] or '{}')
        cycles.append({'cycle':i+1,'status':st,'sec':round(time.time()-t0,2),'mem_avail_mb':(res.get('memory_available_bytes') or 0)//1048576})
    out['cycles']=cycles
    k=f'dup-{run}'
    a=c.post('/api/tasks',headers=ai,json={'operation':'gateway_health','idempotency_key':k}).json()
    b=c.post('/api/tasks',headers=ai,json={'operation':'gateway_health','idempotency_key':k}).json()
    time.sleep(2)
    claims=sum(1 for e in c.get('/api/audit',headers=ai).json()['events'] if e['subject']==a['id'] and e['action']=='claimed')
    out['duplicate']={'same_id':a['id']==b['id'],'second_flag':b.get('duplicate'),'executions':claims}
    hb=Path('/var/lib/nexus-private-control/state/worker.heartbeat')
    out['heartbeat_age_s']=round(time.time()-float(hb.read_text()),1)
ok=(out['root']==200 and set(out['noauth'].values())=={401} and out['noauth_post_task']==401 and out['bad_bearer']==401
    and out['wrong_owner_password']==401 and out['agent_no_token']==401 and out['ai_role']=='ai' and out['ai_status']==200
    and set(out['ai_critical'].values())=={403} and out['ai_approve'] in (401,403) and out['ai_unknown_op']==422
    and all(x['status']=='succeeded' for x in out['cycles']) and out['duplicate']=={'same_id':True,'second_flag':True,'executions':1}
    and out['heartbeat_age_s']<10)
out['RESULT']='PASS' if ok else 'FAIL'
print(json.dumps(out,ensure_ascii=False))
