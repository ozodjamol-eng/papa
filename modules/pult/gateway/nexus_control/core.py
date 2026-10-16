"""Persistent task engine. No arbitrary shell, root access or publishing paths."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, shutil, sqlite3, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

SAFE_SERVER = frozenset({'gateway_health','policy_verify','policy_repair','genplan_probe','urgent_prepare','host_health'})
SAFE_AGENT = frozenset({'device_health','startup_audit','process_snapshot','genplan_status'})
RESTRICTED = frozenset({'deploy_request','restart_service_request','os_repair_request','telegram_publish_request','delete_data_request','rotate_secret_request'})
# Автопилот PAPA: задачу ops/frankfurt/tasks/<имя>.sh выполняет root-исполнитель papa-autopilot на Франкфурте.
# Шлюз проверяет только форму; что можно сразу, что — по кнопке владельца в Telegram, что запрещено —
# решает исполнитель по ops/frankfurt/autopilot/allow.json (граница безопасности — там).
RUNNER = frozenset({'papa_task'})
OPERATIONS = SAFE_SERVER | SAFE_AGENT | RESTRICTED | RUNNER
MAX_ATTEMPTS=3
TASK_TTL_SECONDS=3600
QUEUE_LIMIT=200
AUDIT_KEEP=20000
FINISHED_KEEP_DAYS=30
def _ph(n): return ','.join('?'*n)
def _cutoff(seconds):
    from datetime import timedelta
    return (datetime.now(timezone.utc)-timedelta(seconds=seconds)).isoformat()
POLICY = {'revision':'2.0', 'mode':'autonomous_safe','owner':'sole_human_owner',
 'urgent':'explicit_urgent_bypasses_genplan', 'real_publishing':False,
 'remote_shell':False, 'critical_actions_require_owner_approval':True,
 'safe_server_actions':sorted(SAFE_SERVER),'safe_device_actions':sorted(SAFE_AGENT),
 'restricted_actions':sorted(RESTRICTED)}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def j(s): return json.dumps(s,sort_keys=True,separators=(',',':'),ensure_ascii=False)

class Store:
    def __init__(self, db_file: Path, state_dir: Path):
        self.db_file, self.state_dir = Path(db_file), Path(state_dir)
        self.db_file.parent.mkdir(parents=True,exist_ok=True)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self.bootstrap()
    def conn(self):
        c=sqlite3.connect(str(self.db_file),timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA busy_timeout=10000')
        c.execute('PRAGMA foreign_keys=ON')
        return c
    def bootstrap(self):
        with self.conn() as d:
            d.execute('PRAGMA journal_mode=WAL')
            d.execute('''CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, operation TEXT NOT NULL, target TEXT NOT NULL,
              priority INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
              idempotency TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
              result TEXT, requested_by TEXT NOT NULL, approved_by TEXT,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL, lease_until REAL)''')
            if 'attempts' not in {r[1] for r in d.execute('PRAGMA table_info(tasks)')}:
                d.execute('ALTER TABLE tasks ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
            d.execute('''CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL,
              action TEXT NOT NULL, subject TEXT NOT NULL, info TEXT NOT NULL)''')
            d.execute('''CREATE TABLE IF NOT EXISTS sessions (
              token_hash TEXT PRIMARY KEY, csrf_hash TEXT NOT NULL,
              expires REAL NOT NULL, created_at TEXT NOT NULL)''')
            d.execute('''CREATE TABLE IF NOT EXISTS devices (
              id TEXT PRIMARY KEY, platform TEXT NOT NULL, hostname TEXT NOT NULL,
              last_seen REAL NOT NULL, details TEXT NOT NULL)''')
            # recover ONLY side-effect-free tasks; never auto-requeue external operations
            ph=_ph(len(SAFE_SERVER))
            d.execute(f"UPDATE tasks SET status='failed', result=?, lease_until=NULL WHERE status='running' AND attempts>=? AND operation IN ({ph})",(j({'error':'max_attempts'}),MAX_ATTEMPTS,*sorted(SAFE_SERVER)))
            d.execute(f"UPDATE tasks SET status='queued', lease_until=NULL WHERE status='running' AND operation IN ({ph})",tuple(sorted(SAFE_SERVER)))
        self.policy_path=self.state_dir/'policy.json'
        if not self.policy_path.exists(): self.policy_path.write_text(j(POLICY)+'\n',encoding='utf-8')
    def event(self, db, actor, action, subject='', info=''):
        db.execute('INSERT INTO audit(ts,actor,action,subject,info) VALUES(?,?,?,?,?)',
                   (utc(),actor,action,str(subject)[:160],str(info)[:500]))
    def create(self, actor, operation, payload=None, target='cloud', idempotency=None):
        if operation not in OPERATIONS: raise ValueError('operation_not_allowed')
        if payload is None: payload={}
        if not isinstance(payload,dict) or len(j(payload).encode())>8192: raise ValueError('invalid_payload')
        if not isinstance(target,str) or not (1<=len(target)<=80) or not target.replace('-','').replace('_','').isalnum():
            raise ValueError('invalid_target')
        if operation in SAFE_SERVER and target!='cloud': raise ValueError('wrong_target')
        if operation in SAFE_AGENT and target=='cloud': raise ValueError('agent_target_required')
        if operation=='urgent_prepare' and (type(payload.get('post_id')) is not int or payload['post_id']<=0):
            raise ValueError('explicit_post_id_required')
        if operation in RESTRICTED and not payload.get('reason'): raise ValueError('reason_required')
        if operation in RUNNER:
            import re
            if target!='frankfurt': raise ValueError('runner_target_frankfurt')
            if set(payload)-{'task','reason'} or not isinstance(payload.get('task'),str) \
                    or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,48}',payload['task']):
                raise ValueError('invalid_task_name')
            if not isinstance(payload.get('reason',''),str) or len(payload.get('reason',''))>300: raise ValueError('invalid_reason')
        key=idempotency or secrets.token_hex(16)
        if not isinstance(key,str) or not (4<=len(key)<=120): raise ValueError('invalid_idempotency')
        fingerprint=sha(j({'operation':operation,'target':target,'payload':payload}))
        status='awaiting_approval' if operation in RESTRICTED else 'queued'
        task_id=secrets.token_hex(12)
        priority=100 if operation=='urgent_prepare' else 20 if operation in SAFE_SERVER else 10
        if operation in RUNNER:
            with self.conn() as d:
                busy=d.execute("SELECT COUNT(*) FROM tasks WHERE operation IN ('papa_task') AND status IN ('queued','running','awaiting_owner')").fetchone()[0]
            if busy>=5: raise ValueError('runner_queue_full')
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            old=d.execute('SELECT id,status,fingerprint FROM tasks WHERE idempotency=?',(key,)).fetchone()
            if old:
                if not hmac.compare_digest(old['fingerprint'],fingerprint): raise ValueError('idempotency_conflict')
                return {'id':old['id'],'status':old['status'],'duplicate':True}
            pending=d.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued','running','awaiting_approval')").fetchone()[0]
            if pending>=QUEUE_LIMIT: raise ValueError('queue_full')
            d.execute('''INSERT INTO tasks (id,operation,target,priority,status,payload,idempotency,fingerprint,
                         requested_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                      (task_id,operation,target,priority,status,j(payload),key,fingerprint,actor,utc(),utc()))
            self.event(d,actor,'task_created',task_id,operation+':'+status)
        return {'id':task_id,'status':status,'duplicate':False,'approval_required':operation in RESTRICTED}
    def tasks(self,limit=60):
        with self.conn() as d:
            return [dict(r) for r in d.execute('''SELECT id,operation,target,status,priority,requested_by,
                 approved_by,created_at,updated_at,result FROM tasks ORDER BY created_at DESC LIMIT ?''',(min(limit,200),))]
    def get(self,task_id):
        with self.conn() as d:
            r=d.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
            return dict(r) if r else None
    def approve(self,task_id, actor, confirmation):
        if actor!='owner': raise PermissionError('owner_only')
        if not hmac.compare_digest(confirmation,f'APPROVE:{task_id}'): raise ValueError('bad_confirmation')
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            row=d.execute('SELECT operation,status FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not row: raise ValueError('task_not_found')
            if row['operation'] not in RESTRICTED or row['status']!='awaiting_approval': raise ValueError('not_awaiting_approval')
            d.execute("UPDATE tasks SET status='approved_not_executable',approved_by=?,updated_at=? WHERE id=?",(actor,utc(),task_id))
            self.event(d,actor,'critical_approved_not_executable',task_id)
        return {'id':task_id,'status':'approved_not_executable','executed':False}
    def claim_server(self):
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            d.execute("UPDATE tasks SET status='expired',updated_at=? WHERE status='queued' AND created_at<?",(utc(),_cutoff(TASK_TTL_SECONDS)))
            ph=_ph(len(SAFE_SERVER))
            r=d.execute(f'''SELECT * FROM tasks WHERE status='queued' AND target='cloud' AND attempts<?
              AND operation IN ({ph}) ORDER BY priority DESC,created_at ASC LIMIT 1''',(MAX_ATTEMPTS,*sorted(SAFE_SERVER))).fetchone()
            if not r: return None
            d.execute("UPDATE tasks SET status='running',attempts=attempts+1,updated_at=? WHERE id=?",(utc(),r['id']))
            self.event(d,'cloud-worker','claimed',r['id'])
            return dict(r)
    def finish(self,task_id,status,result,actor='cloud-worker'):
        if status not in ('succeeded','failed'):raise ValueError('bad_status')
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            cur=d.execute("UPDATE tasks SET status=?,result=?,updated_at=?,lease_until=NULL WHERE id=? AND status='running'",
                          (status,j(result),utc(),task_id))
            if cur.rowcount!=1: raise ValueError('not_running')
            self.event(d,actor,status,task_id)
    def next_agent(self,device_id):  # R4_AGENT_PLACEHOLDERS
        ops=tuple(sorted(SAFE_AGENT)); ph=_ph(len(ops))
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            # overdue, read-only device probes can safely be retried
            d.execute(f"UPDATE tasks SET status='failed',result=?,lease_until=NULL WHERE status='running' AND target=? AND lease_until IS NOT NULL AND lease_until<? AND attempts>=? AND operation IN ({ph})",
                     (j({'error':'max_attempts'}),device_id,time.time(),MAX_ATTEMPTS,*ops))
            d.execute(f"UPDATE tasks SET status='queued',lease_until=NULL WHERE status='running' AND target=? AND lease_until IS NOT NULL AND lease_until<? AND operation IN ({ph})",
                     (device_id,time.time(),*ops))
            d.execute("UPDATE tasks SET status='expired',updated_at=? WHERE status='queued' AND target=? AND created_at<?",(utc(),device_id,_cutoff(TASK_TTL_SECONDS)))
            r=d.execute(f'''SELECT * FROM tasks WHERE status='queued' AND target=?
                   AND operation IN ({ph}) ORDER BY priority DESC, created_at ASC LIMIT 1''',
                   (device_id,*ops)).fetchone()
            if not r:return None
            d.execute("UPDATE tasks SET status='running',attempts=attempts+1,lease_until=?,updated_at=? WHERE id=?",(time.time()+120,utc(),r['id']))
            self.event(d,device_id,'agent_claimed',r['id'])
            return {'id':r['id'],'operation':r['operation'],'payload':json.loads(r['payload'])}
    def agent_finish(self,device_id,task_id,ok,result):
        if not isinstance(result,dict) or len(j(result).encode())>16384: raise ValueError('invalid_result')
        ops=tuple(sorted(SAFE_AGENT)); ph=_ph(len(ops))
        with self.conn() as d:
            d.execute('BEGIN IMMEDIATE')
            cur=d.execute(f'''UPDATE tasks SET status=?,result=?,updated_at=?,lease_until=NULL
                               WHERE id=? AND target=? AND status='running' AND operation IN ({ph})''',
                         ('succeeded' if ok else 'failed',j(result),utc(),task_id,device_id,*ops))
            if cur.rowcount!=1: raise ValueError('task_not_claimed')
            self.event(d,device_id,'agent_finished',task_id,'ok' if ok else 'failed')
    def seen(self,device_id,platform,hostname,details):
        if not isinstance(details,dict) or len(j(details).encode())>4096:raise ValueError('invalid_details')
        with self.conn() as d:
            d.execute('''INSERT INTO devices(id,platform,hostname,last_seen,details) VALUES(?,?,?,?,?)
                  ON CONFLICT(id) DO UPDATE SET platform=excluded.platform,hostname=excluded.hostname,
                   last_seen=excluded.last_seen,details=excluded.details''',
                  (device_id,str(platform)[:50],str(hostname)[:90],time.time(),j(details)))
    def devices(self):
        with self.conn() as d:
            return [{**dict(r),'online':time.time()-r['last_seen']<90} for r in d.execute('SELECT * FROM devices ORDER BY id')]
    def housekeeping(self):
        with self.conn() as d:
            d.execute('DELETE FROM audit WHERE id <= (SELECT COALESCE(MAX(id),0) FROM audit) - ?',(AUDIT_KEEP,))
            d.execute("DELETE FROM tasks WHERE status IN ('succeeded','failed','expired') AND updated_at<?",(_cutoff(FINISHED_KEEP_DAYS*86400),))
            d.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
    def counts(self):
        with self.conn() as d:
            rows=d.execute('SELECT status,COUNT(*) n FROM tasks GROUP BY status').fetchall()
            return {r['status']:r['n'] for r in rows}
    def audit(self,limit=50):
        with self.conn() as d:
            return [dict(r) for r in d.execute('SELECT * FROM audit ORDER BY id DESC LIMIT ?',(limit,))]
    def new_session(self,ttl=8*3600):
        token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
        with self.conn() as d:
            d.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            d.execute('INSERT INTO sessions VALUES(?,?,?,?)',(sha(token),sha(csrf),time.time()+ttl,utc()))
            self.event(d,'owner','login')
        return token,csrf
    def session(self,token):
        if not token:return None
        with self.conn() as d:
            return d.execute('SELECT * FROM sessions WHERE token_hash=? AND expires>?',(sha(token),time.time())).fetchone()
    def logout(self,token):
        with self.conn() as d:
            d.execute('DELETE FROM sessions WHERE token_hash=?',(sha(token),))
            self.event(d,'owner','logout')
    def verify_csrf(self, token,csrf):
        s=self.session(token)
        return bool(s and csrf and hmac.compare_digest(s['csrf_hash'],sha(csrf)))
    def policy(self):
        p=self.policy_path
        if p.is_symlink():return {'ok':False,'reason':'symlink_rejected'}
        try: ok=json.loads(p.read_text(encoding='utf-8'))==POLICY
        except (FileNotFoundError,ValueError,UnicodeError):ok=False
        return {'ok':ok,'reason':'compliant' if ok else 'drift_or_missing'}
    def repair_policy(self):
        p=self.policy_path
        if p.is_symlink():raise ValueError('symlink_rejected')
        if self.policy()['ok']:return {'repaired':False,'verified':True}
        if p.exists():
            # local config only: write backup before atomic swap
            shutil.copyfile(p,self.state_dir/('policy.backup.'+secrets.token_hex(5)+'.json'))
        tmp=self.state_dir/('.policy.'+secrets.token_hex(5)+'.tmp')
        try:
            with tmp.open('x',encoding='utf-8') as f:
                f.write(j(POLICY)+'\n');f.flush();os.fsync(f.fileno())
            os.replace(tmp,p)
            if not self.policy()['ok']:raise RuntimeError('verification_failed')
            return {'repaired':True,'verified':True}
        finally:
            tmp.unlink(missing_ok=True)

def safe_server_execute(store: Store,op:str,payload:dict,allow_local_probes:bool=False):
    if op not in SAFE_SERVER:raise PermissionError('operation_not_safe')
    if op=='host_health':
        from .diagnostics import host_health
        return host_health(store.state_dir)
    if op=='gateway_health':return {'scope':'this_gateway','healthy':True,'production_genplan_verified':False}
    if op=='policy_verify':return store.policy()
    if op=='policy_repair':return store.repair_policy()
    if op=='urgent_prepare':return {'post_id':payload['post_id'],'route':'urgent','bypasses_genplan':True,
                                  'published':False,'telegram_ack':None,'notice':'publisher_not_connected'}
    if op=='genplan_probe':
        if not allow_local_probes:
            return {'connected':False,'reason':'local_probes_disabled','production_genplan_verified':False}
        out={}
        for name in ('xojaobod-genplan-v3.service','nexus-mcp.service','ozod-nexus-control-api.service'):
            try:
                r=subprocess.run(['systemctl','is-active',name],capture_output=True,text=True,timeout=3,check=False)
                out[name]='active' if r.returncode==0 and r.stdout.strip()=='active' else 'inactive_or_missing'
            except (OSError,subprocess.TimeoutExpired):out[name]='unavailable'
        return {'connected':True,'services':out,'note':'fixed read-only systemd probe only; not full GENPLAN audit'}
    raise AssertionError('unreachable')
