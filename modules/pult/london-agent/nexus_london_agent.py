#!/usr/bin/env python3
"""NEXUS London agent — READ-ONLY GENPLAN visibility for NEXUS V2.

Outbound only (polls the Frankfurt gateway over the tailnet). Standard library only.
Executes exactly two fixed operations and nothing else:
  genplan_status  - systemd state of the bots, error lines in the journal, publication
                    summary from the GENPLAN database (opened read-only), host resources
  device_health   - host resources only
No shell, no writes, no restarts, no Telegram, no captions/texts of posts, no secrets.
"""
import datetime as dt
import http.client
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = 'london-1.0'
UNIT_RE = re.compile(r'^(xojaobod|genplan|goldwater|nexus|ozod|ozixon|postgres|nginx)[\w@.\-]*\.service$')
GENPLAN_UNIT = os.getenv('GENPLAN_UNIT', 'xojaobod-genplan-v3.service')
ERR_RE = re.compile(r'Traceback|\bERROR\b|\bCRITICAL\b|Exception|OperationalError|Killed process|Out of memory')
SECRET_RES = [
    (re.compile(r'bot\d{6,}:[A-Za-z0-9_\-]{20,}'), 'bot<hidden>'),
    (re.compile(r'\d{6,}:[A-Za-z0-9_\-]{30,}'), '<token-hidden>'),
    (re.compile(r'(?i)(token|password|passwd|secret|api[_-]?key|authorization)(["\'\s:=]+)\S+'), r'\1\2<hidden>'),
    (re.compile(r'[A-Za-z0-9_\-]{40,}'), '<long-hidden>'),
]
SYSTEMCTL = shutil.which('systemctl') or '/usr/bin/systemctl'
JOURNALCTL = shutil.which('journalctl') or '/usr/bin/journalctl'


def redact(text, limit=220):
    text = str(text or '')
    for rx, rep in SECRET_RES:
        text = rx.sub(rep, text)
    return text[:limit]


def run(args, timeout=8):
    """Fixed argv only (never a shell); returns stdout or '' on any failure."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False,
                           env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'SYSTEMD_PAGER': ''})
        return r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def resources():
    out = {'hostname': socket.gethostname(), 'os': platform.platform()[:80]}
    try:
        mem = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            k, v = line.split(':', 1)
            mem[k] = int(v.split()[0]) * 1024
        out['mem_total_mb'] = mem.get('MemTotal', 0) // 1048576
        out['mem_available_mb'] = mem.get('MemAvailable', 0) // 1048576
        out['mem_used_pct'] = round(100 - 100 * mem.get('MemAvailable', 0) / max(mem.get('MemTotal', 1), 1), 1)
        out['swap_used_mb'] = (mem.get('SwapTotal', 0) - mem.get('SwapFree', 0)) // 1048576
        out['load_avg'] = [round(x, 2) for x in os.getloadavg()]
        out['cpus'] = os.cpu_count()
        out['uptime_h'] = round(float(Path('/proc/uptime').read_text().split()[0]) / 3600, 1)
    except (OSError, ValueError):
        out['proc'] = 'partial'
    d = shutil.disk_usage('/')
    out['disk_used_pct'] = round(100 * d.used / d.total, 1)
    out['disk_free_gb'] = round(d.free / 1e9, 1)
    return out


def unit_names():
    names = set()
    for args in ([SYSTEMCTL, 'list-units', '--type=service', '--all', '--no-legend', '--plain', '--no-pager'],
                 [SYSTEMCTL, 'list-unit-files', '--type=service', '--no-legend', '--no-pager']):
        for line in run(args).splitlines():
            parts = line.split()
            if parts and UNIT_RE.match(parts[0]) and '@.' not in parts[0]:
                names.add(parts[0])
    names.add(GENPLAN_UNIT)
    pri = lambda n: (0 if 'genplan' in n else 1 if n.startswith(('xojaobod', 'goldwater', 'nginx', 'postgres')) else 2, n)
    return sorted(names, key=pri)[:40]


PROPS = ['ActiveState', 'SubState', 'UnitFileState', 'NRestarts', 'ActiveEnterTimestamp', 'MemoryCurrent', 'MainPID', 'WorkingDirectory', 'LoadState']


def unit_info(name):
    raw = run([SYSTEMCTL, 'show', name, '--no-pager'] + ['-p' + p for p in PROPS])
    kv = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    info = {'active': kv.get('ActiveState', '?'), 'sub': kv.get('SubState', '?'), 'enabled': kv.get('UnitFileState', ''),
            'restarts': kv.get('NRestarts', ''), 'since': kv.get('ActiveEnterTimestamp', '')}
    mem = kv.get('MemoryCurrent', '')
    if mem.isdigit():
        info['mem_mb'] = round(int(mem) / 1048576, 1)
    return info, kv


def journal_errors(unit, since='-1h', keep=5):
    lines = run([JOURNALCTL, '-u', unit, '--since', since, '--no-pager', '-q', '-o', 'short-iso', '-n', '3000'], timeout=12).splitlines()
    hits = [l for l in lines if ERR_RE.search(l)]
    return {'window': since, 'lines_seen': len(lines), 'error_lines': len(hits), 'last': [redact(h) for h in hits[-keep:]]}


def open_ro(db):
    """Read-only open. Falls back to a private snapshot copy if WAL shm cannot be mapped read-only."""
    try:
        c = sqlite3.connect('file:%s?mode=ro' % db, uri=True, timeout=5)
        c.execute('PRAGMA query_only=1')
        c.execute('SELECT 1 FROM sqlite_master LIMIT 1').fetchone()
        return c, 'ro'
    except sqlite3.Error:
        tmp = Path(tempfile.mkdtemp(prefix='nla-'))
        for suf in ('', '-wal'):
            src = Path(str(db) + suf)
            if src.exists():
                shutil.copyfile(src, tmp / ('g.db' + suf))
        c = sqlite3.connect(str(tmp / 'g.db'), timeout=5)
        c.execute('PRAGMA query_only=1')
        return c, 'snapshot'


def one(c, sql, args=()):
    try:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None
    except sqlite3.Error as e:
        return {'error': type(e).__name__}


def genplan_db(workdir):
    override = os.getenv('GENPLAN_DB', '')
    candidates = [Path(override)] if override else []
    if workdir:
        candidates += [Path(workdir) / 'data' / 'genplan_v3_production.db', Path(workdir) / 'data' / 'genplan_v3.db']
    candidates += [Path('/opt/xojaobod-genplan-v5/data/genplan_v3_production.db'), Path('/opt/xojaobod-genplan-v5/data/genplan_v3.db'), Path('/opt/xojaobod-genplan-v3/data/genplan_v3.db')]
    db = next((p for p in candidates if p.is_file()), None)
    if not db:
        return {'found': False, 'checked': [str(p) for p in candidates]}
    c, mode = open_ro(db)
    c.row_factory = sqlite3.Row
    now = dt.datetime.now(dt.timezone.utc)
    day_ago = (now - dt.timedelta(hours=24)).isoformat()
    late = (now - dt.timedelta(minutes=15)).isoformat()
    st = os.stat(db)
    out = {'found': True, 'path': str(db), 'open_mode': mode, 'size_mb': round(st.st_size / 1048576, 2),
           'modified_utc': dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(timespec='seconds')}
    try:
        out['last_posted'] = one(c, "SELECT channel_id, post_type, rubric, planned_time, actual_time, telegram_message_id FROM publication_log WHERE result='posted' ORDER BY id DESC LIMIT 1")
        if not out['last_posted']:
            out['last_posted'] = one(c, "SELECT channel_id, rubric, source, scheduled_at AS planned_time, posted_at AS actual_time FROM scheduled_posts WHERE status='posted' ORDER BY posted_at DESC LIMIT 1")
            out['last_posted_source'] = 'scheduled_posts'
        out['oldest_overdue'] = (one(c, "SELECT MIN(scheduled_at) t FROM scheduled_posts WHERE status='pending' AND scheduled_at<=?", (late,)) or {}).get('t')
        lf = one(c, "SELECT channel_id, post_type, rubric, planned_time, actual_time, error FROM publication_log WHERE result='failed' ORDER BY id DESC LIMIT 1")
        if lf and lf.get('error') and 'actual_time' in lf:
            lf['error'] = redact(lf['error'])
        out['last_failed'] = lf
        try:
            out['log_24h'] = {r['result']: r['n'] for r in c.execute("SELECT result, COUNT(*) n FROM publication_log WHERE actual_time>=? GROUP BY result", (day_ago,))}
            out['queue'] = {r['status']: r['n'] for r in c.execute("SELECT status, COUNT(*) n FROM scheduled_posts GROUP BY status")}
        except sqlite3.Error as e:
            out['counts_error'] = type(e).__name__
        out['next_pending'] = one(c, "SELECT channel_id, rubric, source, scheduled_at FROM scheduled_posts WHERE status='pending' ORDER BY scheduled_at LIMIT 1")
        out['overdue_pending_15m'] = (one(c, "SELECT COUNT(*) n FROM scheduled_posts WHERE status='pending' AND scheduled_at<=?", (late,)) or {}).get('n')
        out['stuck_publishing'] = (one(c, "SELECT COUNT(*) n FROM scheduled_posts WHERE status='publishing'") or {}).get('n')
        out['channels'] = [dict(r) for r in c.execute("SELECT channel_id, title, active FROM channels ORDER BY channel_id LIMIT 10")]
    except sqlite3.Error as e:
        out['error'] = type(e).__name__
    finally:
        c.close()
    return out


def verdict(units, gp_unit, journal, db):
    problems = []
    if gp_unit.get('active') != 'active':
        problems.append('genplan_service_not_active')
    if str(gp_unit.get('restarts', '')).isdigit() and int(gp_unit.get('restarts')) >= 5:
        problems.append('genplan_crash_loop')
    if journal.get('error_lines'):
        problems.append('errors_in_journal_last_hour')
    if db.get('found') is False:
        problems.append('genplan_db_not_found')
    if db.get('overdue_pending_15m'):
        problems.append('overdue_posts')
    if db.get('stuck_publishing'):
        problems.append('posts_stuck_publishing')
    failed = [n for n, u in units.items() if u.get('active') == 'failed']
    if failed:
        problems.append('failed_units:' + ','.join(failed))
    return {'ok': not problems, 'problems': problems}


def genplan_status():
    units = {}
    gp_kv = {}
    for name in unit_names():
        info, kv = unit_info(name)
        if kv.get('LoadState') == 'not-found':
            continue
        units[name] = info
    gpn = [n for n in sorted(units) if 'genplan' in n]
    gp_name = GENPLAN_UNIT if GENPLAN_UNIT in units else next((n for n in gpn if units[n].get('active') == 'active'), gpn[0] if gpn else GENPLAN_UNIT)
    if gp_name in units:
        gp_kv = unit_info(gp_name)[1]
    gp = units.get(gp_name, {'active': 'missing'})
    journal = journal_errors(gp_name)
    db = genplan_db(gp_kv.get('WorkingDirectory', ''))
    res = {'scope': 'london_read_only', 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
           'genplan_unit': gp_name, 'genplan_service': gp, 'journal': journal, 'database': db,
           'services': units, 'host': resources(), 'telegram_contacted': False, 'changes_made': False}
    res['verdict'] = verdict(units, gp, journal, db)
    return shrink(res)


def shrink(res, limit=15000):
    if len(json.dumps(res, ensure_ascii=False).encode()) > limit:
        res['journal']['last'] = res['journal']['last'][-2:]
    if len(json.dumps(res, ensure_ascii=False).encode()) > limit:
        res['services'] = {k: {'active': v.get('active')} for k, v in res['services'].items()}
    return res


def perform(op, payload):
    if op == 'genplan_status':
        return genplan_status()
    if op == 'device_health':
        return {'source': 'london_agent', **resources()}
    raise PermissionError('operation_not_supported_on_london')


class TailnetHTTPS(http.client.HTTPSConnection):
    """HTTPS to the gateway's tailnet IP while verifying the certificate for its ts.net name."""
    def __init__(self, host, addr, port, context):
        super().__init__(host, port, context=context, timeout=15)
        self._addr = addr

    def connect(self):
        sock = socket.create_connection((self._addr or self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class Gateway:
    def __init__(self, url, addr, device, token):
        if not url.startswith('https://'):
            raise SystemExit('HTTPS required')
        hostport = url[len('https://'):].split('/', 1)[0]
        self.host, _, port = hostport.partition(':')
        self.port = int(port or 443)
        self.addr = addr
        self.ctx = ssl.create_default_context()
        self.headers = {'Authorization': 'Bearer ' + token, 'X-Device-ID': device, 'Content-Type': 'application/json',
                        'User-Agent': 'nexus-london-agent/' + VERSION}

    def post(self, path, body):
        c = TailnetHTTPS(self.host, self.addr, self.port, self.ctx)
        try:
            c.request('POST', path, body=json.dumps(body, ensure_ascii=False).encode(), headers=self.headers)
            r = c.getresponse()
            data = r.read(65536)
            if r.status != 200:
                raise RuntimeError('http_%d' % r.status)
            return json.loads(data or b'{}')
        finally:
            c.close()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'selftest':
        r = genplan_status()
        db = r['database']
        short = {'verdict': r['verdict'], 'genplan': r['genplan_service'], 'journal_errors_1h': r['journal']['error_lines'],
                 'db': {k: db.get(k) for k in ('found', 'open_mode', 'path')},
                 'last_posted': (db.get('last_posted') or {}).get('actual_time'), 'last_failed': (db.get('last_failed') or {}).get('actual_time'),
                 'queue': db.get('queue'), 'services': {k: v['active'] for k, v in r['services'].items()},
                 'host': {k: r['host'].get(k) for k in ('mem_used_pct', 'disk_used_pct', 'load_avg')},
                 'bytes': len(json.dumps(r, ensure_ascii=False).encode())}
        print(json.dumps(short, ensure_ascii=False))
        return
    url = os.getenv('NEXUS_GATEWAY_URL', '').rstrip('/')
    device = os.getenv('NEXUS_AGENT_ID', 'london')
    token = os.getenv('NEXUS_AGENT_TOKEN', '')
    if not url or len(token) < 24:
        raise SystemExit('Missing NEXUS_GATEWAY_URL / NEXUS_AGENT_TOKEN')
    gw = Gateway(url, os.getenv('NEXUS_GATEWAY_ADDR', ''), device, token)
    print('NEXUS London agent', VERSION, 'started', flush=True)
    backoff = 5
    while True:
        try:
            gw.post('/api/agent/hello', {'platform': 'Linux', 'hostname': socket.gethostname(),
                                         'details': {'version': VERSION, 'ops': ['genplan_status', 'device_health'], 'read_only': True}})
            task = gw.post('/api/agent/next', {}).get('task')
            if task:
                try:
                    result, ok = perform(task['operation'], task.get('payload') or {}), True
                except Exception as exc:  # report, never crash the loop
                    result, ok = {'error': type(exc).__name__, 'message': redact(exc, 120)}, False
                gw.post('/api/agent/result', {'task_id': task['id'], 'ok': ok, 'result': result})
                print('task', task['id'][:8], task['operation'], 'ok' if ok else 'failed', flush=True)
            backoff = 5
        except (OSError, RuntimeError, ValueError, http.client.HTTPException) as exc:
            print('gateway unreachable:', type(exc).__name__, redact(exc, 80), flush=True)
            backoff = min(backoff * 2, 60)
            time.sleep(backoff)
            continue
        time.sleep(5)


if __name__ == '__main__':
    main()
