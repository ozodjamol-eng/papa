"""Outbound-only Windows/Mac/Linux agent; no arbitrary shell, no root requirement."""
from __future__ import annotations
import json, os, platform, shutil, socket, sys, time
from pathlib import Path
import httpx
from .core import SAFE_AGENT

def perform(operation:str,payload:dict):
    if operation not in SAFE_AGENT:raise PermissionError('agent_operation_denied')
    if operation=='device_health':
        usage=shutil.disk_usage(Path.home())
        return {'os':platform.system(),'release':platform.release(),
                'disk_free_gb':round(usage.free/1e9,1),'disk_total_gb':round(usage.total/1e9,1),
                'hostname':socket.gethostname(),'source':'local_agent'}
    if operation=='startup_audit':
        # Read-only startup inventory: no administrative privileges or binary execution.
        locations=[]
        if sys.platform=='win32':
            roaming=Path(os.getenv('APPDATA',str(Path.home())))
            locations=[roaming/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Startup']
        elif sys.platform=='darwin':
            locations=[Path.home()/'Library'/'LaunchAgents']
        else:
            locations=[Path.home()/'.config'/'autostart']
        entries=[]
        for folder in locations:
            if folder.is_dir():entries.extend([{'name':p.name,'kind':'startup_entry'} for p in sorted(folder.iterdir()) if not p.is_symlink()][:100])
        return {'checked':True,'entries':entries,'scope':'per-user directories only; read-only'}
    if operation=='process_snapshot':
        try:
            import psutil
        except ImportError:
            return {'available':False,'reason':'psutil_optional_dependency_missing'}
        processes=[]
        for proc in psutil.process_iter(attrs=['pid','name','memory_info']):
            try:
                info=proc.info
                processes.append({'pid':info['pid'],'name':str(info['name'])[:80],
                                  'memory_mb':round(info['memory_info'].rss/1048576,1)})
            except (psutil.NoSuchProcess,psutil.AccessDenied,TypeError,AttributeError):continue
        return {'available':True,'processes':sorted(processes,key=lambda p:p['memory_mb'],reverse=True)[:30]}
    if operation=='genplan_status':return {'available':False,'reason':'not_a_genplan_host'}
    raise ValueError('unknown_operation')

def main():
    url=os.getenv('NEXUS_GATEWAY_URL','').rstrip('/')
    device_id=os.getenv('NEXUS_AGENT_ID','')
    token=os.getenv('NEXUS_AGENT_TOKEN','')
    if not url or not device_id or len(token)<24:raise SystemExit('Missing URL / agent id / agent token')
    if not url.startswith('https://') and not url.startswith('http://127.0.0.1:'):
        raise SystemExit('HTTPS required for remote gateway')
    client=httpx.Client(base_url=url,headers={'Authorization':f'Bearer {token}','X-Device-ID':device_id},timeout=12)
    print('NEXUS agent started:',device_id,flush=True)
    while True:
        try:
            r=client.post('/api/agent/hello',json={'platform':platform.system(),'hostname':socket.gethostname(),'details':{'version':'2.0'}})
            r.raise_for_status()
            res=client.post('/api/agent/next');res.raise_for_status()
            task=res.json().get('task')
            if task:
                try: result=perform(task['operation'],task['payload']);ok=True
                except Exception as exc:result={'error':type(exc).__name__,'message':str(exc)[:120]};ok=False
                done=client.post('/api/agent/result',json={'task_id':task['id'],'ok':ok,'result':result})
                done.raise_for_status()
        except (httpx.HTTPError,ValueError) as exc:
            print('Agent temporarily disconnected:',type(exc).__name__,flush=True)
        time.sleep(5)
if __name__=='__main__':main()
