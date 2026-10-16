"""NEXUS Connect: OAuth 2.1 (DCR + PKCE) authorization for AI connectors + a minimal MCP server.
Exposes ONLY safe NEXUS operations by calling the NEXUS V2 gateway with its scoped AI role.
No shell, no file access, no critical actions."""
from __future__ import annotations
import base64, re, hashlib, hmac, html, json, os, secrets, sqlite3, time
from collections import deque
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl
import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

PROTOCOL_VERSIONS = ('2025-06-18', '2025-03-26', '2024-11-05')
ALLOWED_REDIRECT_HOSTS = ('claude.ai', 'claude.com', 'chatgpt.com', 'chat.openai.com', 'openai.com')
CHECK_OPS = {'gateway_health': 'Диагностика шлюза', 'host_health': 'Диагностика сервера', 'policy_verify': 'Проверка правил шлюза'}
ACCESS_TTL = 3600
REFRESH_TTL = 30 * 86400
CODE_TTL = 120
MAX_CLIENTS = 20

def now(): return time.time()
def h(s: str) -> str: return hashlib.sha256(s.encode()).hexdigest()
def b64url(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b'=').decode()

def label_for(redirect_uri: str) -> str:
    host = (urlparse(redirect_uri).hostname or '').lower()
    if host.endswith('claude.ai') or host.endswith('claude.com'): return 'Claude'
    if host.endswith('chatgpt.com') or host.endswith('openai.com'): return 'ChatGPT'
    return 'unknown'

def redirect_ok(uri: str) -> bool:
    try: p = urlparse(uri)
    except ValueError: return False
    host = (p.hostname or '').lower()
    return p.scheme == 'https' and not p.username and any(host == d or host.endswith('.' + d) for d in ALLOWED_REDIRECT_HOSTS)

class Config:
    def __init__(self, base_url=None, db=None, owner_hash=None, ai_token=None, gateway=None, secret=None):
        self.base_url = (base_url or os.getenv('NEXUS_CONNECT_BASE_URL', '')).rstrip('/')
        self.db = Path(db or os.getenv('NEXUS_CONNECT_DB', '/var/lib/nexus-connect/connect.sqlite3'))
        self.owner_hash = owner_hash or os.getenv('NEXUS_OWNER_PASSWORD_HASH', '')
        self.ai_token = ai_token or os.getenv('NEXUS_AI_TOKEN', '')
        self.gateway = (gateway or os.getenv('NEXUS_GATEWAY_URL', 'http://127.0.0.1:8788')).rstrip('/')
        self.secret = (secret or os.getenv('NEXUS_CONNECT_SECRET', '')).encode()
        if not self.base_url.startswith('https://'): raise RuntimeError('NEXUS_CONNECT_BASE_URL must be https')
        if not self.owner_hash or len(self.ai_token) < 32 or len(self.secret) < 32: raise RuntimeError('missing_secrets')

class Store:
    def __init__(self, path: Path):
        self.path = path; path.parent.mkdir(parents=True, exist_ok=True)
        with self.c() as d:
            d.execute('PRAGMA journal_mode=WAL')
            d.execute('CREATE TABLE IF NOT EXISTS clients(id TEXT PRIMARY KEY, name TEXT, label TEXT, redirect_uris TEXT, created REAL, approved INTEGER DEFAULT 0, scopes TEXT DEFAULT "", revoked INTEGER DEFAULT 0)')
            d.execute('CREATE TABLE IF NOT EXISTS codes(code_hash TEXT PRIMARY KEY, client_id TEXT, redirect_uri TEXT, challenge TEXT, scopes TEXT, resource TEXT, expires REAL)')
            d.execute('CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY, kind TEXT, client_id TEXT, scopes TEXT, expires REAL)')
            d.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, who TEXT, action TEXT, info TEXT)')
    def c(self):
        x = sqlite3.connect(str(self.path), timeout=10); x.row_factory = sqlite3.Row; return x
    def log(self, who, action, info=''):
        with self.c() as d:
            d.execute('INSERT INTO audit(ts,who,action,info) VALUES(?,?,?,?)', (now(), who, action, str(info)[:300]))
            d.execute('DELETE FROM audit WHERE id <= (SELECT COALESCE(MAX(id),0) FROM audit) - 20000')

def create_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or Config()
    st = Store(cfg.db)
    ph = PasswordHasher()
    fails: deque = deque()
    regs: deque = deque()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = st; app.state.cfg = cfg
    RESOURCE = cfg.base_url + '/mcp'
    META = cfg.base_url + '/.well-known/oauth-protected-resource'

    async def read_form(request: Request) -> dict:
        raw = await request.body()
        if len(raw) > 16384: return {}
        return dict(parse_qsl(raw.decode('utf-8', 'replace'), keep_blank_values=True))

    def sign(*parts) -> str:
        return hmac.new(cfg.secret, '|'.join(parts).encode(), hashlib.sha256).hexdigest()

    @app.middleware('http')
    async def headers(request: Request, call_next):
        r = await call_next(request)
        r.headers['Cache-Control'] = 'no-store'; r.headers['X-Content-Type-Options'] = 'nosniff'
        r.headers['Referrer-Policy'] = 'no-referrer'; r.headers['X-Frame-Options'] = 'DENY'
        r.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self' https:; frame-ancestors 'none'; base-uri 'none'"
        return r

    # ---------- discovery ----------
    def resource_meta():
        return {'resource': RESOURCE, 'authorization_servers': [cfg.base_url], 'scopes_supported': ['nexus.read', 'nexus.checks'],
                'bearer_methods_supported': ['header'], 'resource_name': 'NEXUS Frankfurt'}
    @app.get('/.well-known/oauth-protected-resource')
    def prm(): return resource_meta()
    @app.get('/.well-known/oauth-protected-resource/mcp')
    def prm2(): return resource_meta()
    def as_meta():
        b = cfg.base_url
        return {'issuer': b, 'authorization_endpoint': b + '/authorize', 'token_endpoint': b + '/token',
                'registration_endpoint': b + '/register', 'response_types_supported': ['code'],
                'grant_types_supported': ['authorization_code', 'refresh_token'], 'code_challenge_methods_supported': ['S256'],
                'token_endpoint_auth_methods_supported': ['none'], 'scopes_supported': ['nexus.read', 'nexus.checks']}
    @app.get('/.well-known/oauth-authorization-server')
    def asm(): return as_meta()
    @app.get('/.well-known/oauth-authorization-server/mcp')
    def asm2(): return as_meta()
    @app.get('/.well-known/openid-configuration')
    def oidc(): return as_meta()

    # ---------- dynamic client registration ----------
    @app.post('/register')
    async def register(request: Request):
        t = now()
        while regs and regs[0] < t - 3600: regs.popleft()
        if len(regs) >= 10: return JSONResponse({'error': 'temporarily_unavailable'}, 429)
        try: body = await request.json()
        except Exception: return JSONResponse({'error': 'invalid_client_metadata'}, 400)
        uris = body.get('redirect_uris') or []
        if not isinstance(uris, list) or not uris or len(uris) > 5 or not all(isinstance(u, str) and redirect_ok(u) for u in uris):
            return JSONResponse({'error': 'invalid_redirect_uri', 'error_description': 'redirect host not allowed'}, 400)
        with st.c() as d:
            if d.execute('SELECT COUNT(*) FROM clients WHERE revoked=0').fetchone()[0] >= MAX_CLIENTS:
                return JSONResponse({'error': 'temporarily_unavailable'}, 429)
            cid = 'nxc_' + secrets.token_urlsafe(18); name = str(body.get('client_name') or '')[:80]
            label = label_for(uris[0])
            d.execute('INSERT INTO clients(id,name,label,redirect_uris,created) VALUES(?,?,?,?,?)', (cid, name, label, json.dumps(uris), t))
        regs.append(t); st.log(label, 'client_registered', cid)
        return JSONResponse({'client_id': cid, 'client_name': name, 'redirect_uris': uris, 'grant_types': ['authorization_code', 'refresh_token'],
                             'response_types': ['code'], 'token_endpoint_auth_method': 'none', 'client_id_issued_at': int(t)}, 201)

    def get_client(cid):
        with st.c() as d:
            return d.execute('SELECT * FROM clients WHERE id=? AND revoked=0', (cid,)).fetchone()

    # ---------- authorize (owner login + consent) ----------
    def page(title, body, status=200):
        return HTMLResponse(f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
body{{margin:0;background:#fff3e8;font:16px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1b1410}}
.hero{{background:#ff4d0d;color:#fff;padding:28px 20px 60px;border-radius:0 0 40px 40px;text-align:center}}
.hero b{{font-size:34px;letter-spacing:-1px}}.hero p{{margin:6px 0 0;opacity:.9}}
.card{{max-width:440px;margin:-36px auto 24px;background:#fff;border-radius:26px;padding:22px;box-shadow:0 10px 28px rgba(255,77,13,.12);border:1px solid #f6dcc4}}
h2{{margin:0 0 6px;font-size:21px}}ul{{padding-left:20px;margin:8px 0}}li{{margin:4px 0}}.muted{{color:#6f625a;font-size:14px}}
input[type=password]{{width:100%;box-sizing:border-box;padding:14px;border-radius:16px;border:1px solid #f6dcc4;background:#fdebd8;font-size:16px;margin:8px 0}}
.row{{display:flex;gap:10px;margin-top:14px}}button{{flex:1;border:0;border-radius:18px;padding:14px;font-weight:700;font-size:16px}}
.rev{{flex-direction:row-reverse}}.ok{{background:#ff4d0d;color:#fff}}.no{{background:#fdebd8;color:#1b1410}}.err{{color:#d4380d;font-weight:600}}
label.ck{{display:flex;gap:8px;align-items:center;margin:6px 0}}</style></head><body>
<div class="hero"><b>NEXUS</b><p>Подключение ИИ к шлюзу</p></div><div class="card">{body}</div></body></html>''', status)

    def bad(msg): return page('NEXUS — ошибка', f'<h2>Запрос отклонён</h2><p class="err">{html.escape(msg)}</p>', 400)

    def check_params(q):
        cid = q.get('client_id', ''); ru = q.get('redirect_uri', '')
        cl = get_client(cid)
        if not cl: return None, 'Неизвестное приложение'
        if ru not in json.loads(cl['redirect_uris']): return None, 'Адрес возврата не совпадает'
        if q.get('response_type') != 'code': return None, 'Неподдерживаемый тип ответа'
        if q.get('code_challenge_method') != 'S256' or not (43 <= len(q.get('code_challenge', '')) <= 128): return None, 'Требуется PKCE S256'
        res = q.get('resource')
        if res and res.rstrip('/') not in (RESOURCE, cfg.base_url): return None, 'Неверный ресурс'
        return cl, ''

    FIELDS = ('client_id', 'redirect_uri', 'response_type', 'code_challenge', 'code_challenge_method', 'state', 'resource', 'scope')

    def consent_form(q, cl, error=''):
        hidden = ''.join(f'<input type="hidden" name="{f}" value="{html.escape(q.get(f, ""))}">' for f in FIELDS)
        ts = str(int(now())); sig = sign(ts, q.get('client_id', ''), q.get('redirect_uri', ''), q.get('code_challenge', ''))
        who = html.escape(cl['label'] if cl['label'] != 'unknown' else (cl['name'] or 'Приложение'))
        err = f'<p class="err">{html.escape(error)}</p>' if error else ''
        return page('NEXUS — разрешить доступ', f'''<h2>{who} просит доступ к NEXUS</h2>
<p class="muted">Приложение: {html.escape(cl['name'] or '—')}</p>
<ul><li>Смотреть статус сервера, задачи, журнал и устройства</li></ul>
<label class="ck"><input type="checkbox" name="allow_checks" value="1" checked form="f"> Запускать безопасные проверки (диагностика, правила)</label>
<p class="muted">Деплой, перезапуски, публикации и удаление — запрещены всегда.</p>{err}
<form id="f" method="post" action="/authorize">{hidden}<input type="hidden" name="ts" value="{ts}"><input type="hidden" name="sig" value="{sig}">
<input type="password" name="password" autocomplete="current-password" placeholder="Пароль владельца NEXUS" required>
<div class="row rev"><button class="ok" name="decision" value="allow">Разрешить</button><button class="no" name="decision" value="deny" formnovalidate>Отклонить</button></div></form>''')

    @app.get('/authorize')
    def authorize_get(request: Request):
        q = dict(request.query_params); cl, err = check_params(q)
        if not cl: return bad(err)
        return consent_form(q, cl)

    @app.post('/authorize')
    async def authorize_post(request: Request):
        form = await read_form(request); q = {k: str(form.get(k, '')) for k in FIELDS}
        cl, err = check_params(q)
        if not cl: return bad(err)
        ts = str(form.get('ts', '')); sig = str(form.get('sig', ''))
        if not ts.isdigit() or now() - int(ts) > 600 or not hmac.compare_digest(sig, sign(ts, q['client_id'], q['redirect_uri'], q['code_challenge'])):
            return bad('Форма устарела, начните подключение заново')
        def back(params):
            params = {k: v for k, v in params.items() if v}
            sep = '&' if '?' in q['redirect_uri'] else '?'
            return RedirectResponse(q['redirect_uri'] + sep + urlencode(params), 303)
        if form.get('decision') != 'allow':
            st.log(cl['label'], 'consent_denied', cl['id']); return back({'error': 'access_denied', 'state': q['state']})
        t = now()
        while fails and fails[0] < t - 900: fails.popleft()
        if len(fails) >= 5: return consent_form(q, cl, 'Слишком много попыток. Подождите 15 минут.')
        try: ph.verify(cfg.owner_hash, str(form.get('password', '')))
        except (VerifyMismatchError, VerificationError):
            fails.append(t); st.log(cl['label'], 'owner_password_failed', cl['id']); return consent_form(q, cl, 'Неверный пароль')
        scopes = 'nexus.read nexus.checks' if form.get('allow_checks') == '1' else 'nexus.read'
        code = secrets.token_urlsafe(32)
        with st.c() as d:
            d.execute('INSERT INTO codes VALUES(?,?,?,?,?,?,?)', (h(code), cl['id'], q['redirect_uri'], q['code_challenge'], scopes, q['resource'], t + CODE_TTL))
            d.execute('UPDATE clients SET approved=1, scopes=? WHERE id=?', (scopes, cl['id']))
        st.log(cl['label'], 'consent_granted', scopes)
        return back({'code': code, 'state': q['state'], 'iss': cfg.base_url})

    # ---------- token ----------
    def issue(client_id, scopes):
        at, rt = 'nxa_' + secrets.token_urlsafe(32), 'nxr_' + secrets.token_urlsafe(32)
        with st.c() as d:
            d.execute('DELETE FROM tokens WHERE expires<?', (now(),))
            d.execute('INSERT INTO tokens VALUES(?,?,?,?,?)', (h(at), 'access', client_id, scopes, now() + ACCESS_TTL))
            d.execute('INSERT INTO tokens VALUES(?,?,?,?,?)', (h(rt), 'refresh', client_id, scopes, now() + REFRESH_TTL))
        return JSONResponse({'access_token': at, 'token_type': 'Bearer', 'expires_in': ACCESS_TTL, 'refresh_token': rt, 'scope': scopes})

    def oerr(e, desc=''): return JSONResponse({'error': e, 'error_description': desc}, 400)

    @app.post('/token')
    async def token(request: Request):
        f = await read_form(request); gt = f.get('grant_type'); cid = str(f.get('client_id', ''))
        cl = get_client(cid)
        if not cl: return JSONResponse({'error': 'invalid_client'}, 401)
        if gt == 'authorization_code':
            code = str(f.get('code', '')); ver = str(f.get('code_verifier', ''))
            with st.c() as d:
                row = d.execute('SELECT * FROM codes WHERE code_hash=?', (h(code),)).fetchone()
                d.execute('DELETE FROM codes WHERE code_hash=? OR expires<?', (h(code), now()))
            if not row or row['client_id'] != cid or row['expires'] < now(): return oerr('invalid_grant', 'code')
            if str(f.get('redirect_uri', row['redirect_uri'])) != row['redirect_uri']: return oerr('invalid_grant', 'redirect_uri')
            if not (43 <= len(ver) <= 128) or not hmac.compare_digest(b64url(hashlib.sha256(ver.encode()).digest()), row['challenge']):
                return oerr('invalid_grant', 'pkce')
            st.log(cl['label'], 'token_issued', cid); return issue(cid, row['scopes'])
        if gt == 'refresh_token':
            rt = str(f.get('refresh_token', ''))
            with st.c() as d:
                row = d.execute("SELECT * FROM tokens WHERE token_hash=? AND kind='refresh'", (h(rt),)).fetchone()
                d.execute('DELETE FROM tokens WHERE token_hash=?', (h(rt),))
            if not row or row['client_id'] != cid or row['expires'] < now(): return oerr('invalid_grant', 'refresh')
            st.log(cl['label'], 'token_refreshed', cid); return issue(cid, row['scopes'])
        return oerr('unsupported_grant_type')

    # ---------- MCP ----------
    def auth(request: Request):
        hdr = request.headers.get('authorization', '')
        tok = hdr[7:] if hdr.startswith('Bearer ') else ''
        if not tok: return None
        with st.c() as d:
            row = d.execute("SELECT t.*, c.label FROM tokens t JOIN clients c ON c.id=t.client_id WHERE t.token_hash=? AND t.kind='access' AND t.expires>? AND c.revoked=0",
                            (h(tok), now())).fetchone()
        return row

    def unauthorized():
        return JSONResponse({'error': 'invalid_token'}, 401, headers={'WWW-Authenticate': f'Bearer resource_metadata="{META}", scope="nexus.read nexus.checks"'})

    TOOLS = [
        {'name': 'nexus_status', 'title': 'Статус NEXUS', 'description': 'Состояние шлюза NEXUS Frankfurt: очередь задач, устройства, режим. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}, 'annotations': {'readOnlyHint': True}, 'scope': 'nexus.read'},
        {'name': 'nexus_tasks', 'title': 'Задачи NEXUS', 'description': 'Последние задачи шлюза и их результаты. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}}, 'additionalProperties': False},
         'annotations': {'readOnlyHint': True}, 'scope': 'nexus.read'},
        {'name': 'nexus_audit', 'title': 'Журнал NEXUS', 'description': 'Журнал действий шлюза (кто, когда, что). Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}}, 'additionalProperties': False},
         'annotations': {'readOnlyHint': True}, 'scope': 'nexus.read'},
        {'name': 'nexus_devices', 'title': 'Устройства NEXUS', 'description': 'Подключённые агенты-устройства. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}, 'annotations': {'readOnlyHint': True}, 'scope': 'nexus.read'},
        {'name': 'nexus_run_check', 'title': 'Запустить проверку', 'description': 'Запускает безопасную проверку на сервере и возвращает результат. Доступно: '
         + ', '.join(f'{k} ({v})' for k, v in CHECK_OPS.items()) + '. Ничего не меняет в production.',
         'inputSchema': {'type': 'object', 'properties': {'check': {'type': 'string', 'enum': list(CHECK_OPS)}}, 'required': ['check'], 'additionalProperties': False},
         'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': True}, 'scope': 'nexus.checks'},
        {'name': 'nexus_genplan', 'title': 'GENPLAN Лондон', 'description': 'Состояние GENPLAN и ботов на сервере Лондон: службы, ошибки в журнале за час, последняя публикация и последняя ошибка публикации, очередь постов, ресурсы сервера. Только чтение: ничего не публикует и не перезапускает. Ответ через агент, 5-25 секунд.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
         'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}, 'scope': 'nexus.checks'},
        {'name': 'nexus_razvedka', 'title': 'Отчёт Разведки', 'description': 'Последний отчёт Разведки PAPA по каналам-источникам и конкурентам в Telegram: лучшие часы и дни, форматы, лидеры по просмотрам и ERR, вероятная реклама у конкурентов, самые сильные посты, свои каналы. Обновляется каждый день в 06:10 по Ташкенту. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
         'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}, 'scope': 'nexus.read'},
        {'name': 'nexus_voronka', 'title': 'Воронка Instagram', 'description': 'Состояние Voronka PAPA: режим (работа/проверка), сколько комментариев под постами @paparazzi.uz обработано и сколько директов со ссылкой отправлено за час/сутки/всего, пропуски (спам, дубли), ошибки и паузы Meta, заявки в Telegram, посты под наблюдением. Обновляется каждые 2 минуты. Без личных данных. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
         'annotations': {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}, 'scope': 'nexus.read'},
        {'name': 'nexus_papa_task', 'title': 'Автопилот PAPA (Франкфурт / Лондон)',
         'description': 'Выполнить задачу PAPA на сервере — то же, что владелец делает командой papa-update <задача>. '
                        'server=frankfurt (по умолчанию) — задачи ops/frankfurt/tasks; server=london — задачи ops/london/tasks (GENPLAN 5, '
                        'боты Хўжаобода), их выполняет исполнитель papa-runner на Лондоне. Решает автопилот по ops/<сервер>/autopilot/allow.json: '
                        'безопасные задачи — сразу; остальные — только после кнопки «✅ Разрешить» владельца в Telegram; '
                        'задачи с секретами и входом в аккаунты — запрещены. Ждёт до 40 с; дальше результат — nexus_papa_result.',
         'inputSchema': {'type': 'object', 'properties': {
             'task': {'type': 'string', 'pattern': '^[a-z0-9][a-z0-9-]{1,48}$', 'description': 'имя задачи из ops/<сервер>/tasks без .sh'},
             'server': {'type': 'string', 'enum': ['frankfurt', 'london'], 'description': 'сервер; по умолчанию frankfurt'},
             'reason': {'type': 'string', 'maxLength': 300, 'description': 'зачем — коротко по-русски, владелец видит это в Telegram'}},
             'required': ['task', 'reason'], 'additionalProperties': False},
         'annotations': {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': False, 'openWorldHint': False}, 'scope': 'nexus.checks'},
        {'name': 'nexus_papa_result', 'title': 'Результат задачи автопилота', 'description': 'Статус и вывод задачи автопилота PAPA по её task_id. Только чтение.',
         'inputSchema': {'type': 'object', 'properties': {'task_id': {'type': 'string', 'pattern': '^[a-f0-9]{8,40}$'}},
                         'required': ['task_id'], 'additionalProperties': False},
         'annotations': {'readOnlyHint': True}, 'scope': 'nexus.read'},
    ]
    TOOL_BY = {t['name']: t for t in TOOLS}

    def gw(method, path, **kw):
        with httpx.Client(base_url=cfg.gateway, timeout=10, trust_env=False) as c:
            r = c.request(method, path, headers={'Authorization': 'Bearer ' + cfg.ai_token}, **kw)
            r.raise_for_status(); return r.json()
    app.state.gw = gw

    def call_tool(name, args, who):
        g = app.state.gw
        lim = args.get('limit', 10)
        if not isinstance(lim, int) or not 1 <= lim <= 50: lim = 10
        if name == 'nexus_status': return g('GET', '/api/status')
        if name == 'nexus_devices': return g('GET', '/api/devices')
        if name == 'nexus_razvedka': return g('GET', '/api/razvedka')
        if name == 'nexus_voronka': return g('GET', '/api/voronka')
        if name == 'nexus_tasks': return {'tasks': g('GET', '/api/tasks')['tasks'][:lim]}
        if name == 'nexus_audit': return {'events': g('GET', '/api/audit')['events'][:lim]}
        if name == 'nexus_run_check':
            op = args.get('check')
            if op not in CHECK_OPS: raise ValueError('check_not_allowed')
            created = g('POST', '/api/tasks', json={'operation': op, 'idempotency_key': f'mcp-{who}-{secrets.token_hex(8)}'})
            tid = created['id']; t0 = time.time(); row = None
            while time.time() - t0 < 12:
                row = next((x for x in g('GET', '/api/tasks')['tasks'] if x['id'] == tid), None)
                if row and row['status'] in ('succeeded', 'failed'): break
                time.sleep(0.4)
            if not row or row['status'] not in ('succeeded', 'failed'):
                return {'task_id': tid, 'status': row['status'] if row else 'unknown', 'note': 'ещё выполняется, проверьте nexus_tasks'}
            return {'task_id': tid, 'check': op, 'status': row['status'], 'verified_result': json.loads(row['result'] or '{}')}
        if name == 'nexus_genplan':
            created = g('POST', '/api/tasks', json={'operation': 'genplan_status', 'target': 'london', 'idempotency_key': f'mcp-{who}-{secrets.token_hex(8)}'})
            tid = created['id']; t0 = time.time(); row = None
            while time.time() - t0 < 25:
                row = next((x for x in g('GET', '/api/tasks')['tasks'] if x['id'] == tid), None)
                if row and row['status'] in ('succeeded', 'failed'): break
                time.sleep(0.5)
            if not row or row['status'] not in ('succeeded', 'failed'):
                online = any(d['id'] == 'london' and d['online'] for d in g('GET', '/api/devices')['devices'])
                return {'task_id': tid, 'status': row['status'] if row else 'unknown', 'london_agent_online': online,
                        'note': 'агент Лондона не ответил за 25 с; результат появится в nexus_tasks' if online else 'агент Лондона офлайн'}
            return {'task_id': tid, 'status': row['status'], 'source': 'london_agent', 'verified_result': json.loads(row['result'] or '{}')}
        if name == 'nexus_papa_task':
            task, reason = args.get('task'), args.get('reason', '')
            if not isinstance(task, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,48}', task): raise ValueError('bad_task')
            if not isinstance(reason, str) or len(reason) > 300: raise ValueError('bad_reason')
            server = args.get('server', 'frankfurt')
            if server not in ('frankfurt', 'london'): raise ValueError('bad_server')
            created = g('POST', '/api/tasks', json={'operation': 'papa_task', 'target': server, 'payload': {'task': task, 'reason': reason},
                                                     'idempotency_key': f'mcp-{who}-{secrets.token_hex(8)}'})
            tid = created['id']; t0 = time.time(); row = None
            while time.time() - t0 < 40:
                row = g('GET', f'/api/tasks/{tid}')
                if row['status'] in ('succeeded', 'failed', 'expired'): break
                time.sleep(1)
            return papa_view(row or {'id': tid, 'status': 'unknown'})
        if name == 'nexus_papa_result':
            tid = args.get('task_id')
            if not isinstance(tid, str) or not re.fullmatch(r'[a-f0-9]{8,40}', tid): raise ValueError('bad_task_id')
            return papa_view(g('GET', f'/api/tasks/{tid}'))
        raise ValueError('unknown_tool')

    def papa_view(row):
        res = json.loads(row.get('result') or '{}') if isinstance(row.get('result'), str) else (row.get('result') or {})
        hint = {'queued': 'в очереди у исполнителя', 'running': 'выполняется',
                'awaiting_owner': 'ждёт кнопку владельца в Telegram',
                'ready': 'разрешено, ждёт исполнителя на Лондоне'}.get(row.get('status'), '')
        return {'task_id': row.get('id'), 'status': row.get('status'), 'server': row.get('target'), 'hint': hint, **res}

    def rpc_result(i, result): return {'jsonrpc': '2.0', 'id': i, 'result': result}
    def rpc_error(i, code, msg): return {'jsonrpc': '2.0', 'id': i, 'error': {'code': code, 'message': msg}}

    async def handle(msg, tok):
        if not isinstance(msg, dict) or msg.get('jsonrpc') != '2.0': return rpc_error(None, -32600, 'invalid request')
        mid, method, params = msg.get('id'), msg.get('method'), msg.get('params') or {}
        if mid is None: return None  # notification
        scopes = set(tok['scopes'].split())
        if method == 'initialize':
            req = params.get('protocolVersion'); ver = req if req in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
            return rpc_result(mid, {'protocolVersion': ver, 'capabilities': {'tools': {'listChanged': False}},
                                    'serverInfo': {'name': 'nexus-frankfurt', 'title': 'NEXUS Frankfurt', 'version': '1.0.0'},
                                    'instructions': 'Шлюз NEXUS Frankfurt. Доступны только чтение и безопасные проверки. Критические действия запрещены и выполняются только владельцем.'})
        if method == 'ping': return rpc_result(mid, {})
        if method == 'tools/list':
            return rpc_result(mid, {'tools': [{k: v for k, v in t.items() if k != 'scope'} for t in TOOLS if t['scope'] in scopes]})
        if method == 'tools/call':
            name = params.get('name'); args = params.get('arguments') or {}
            t = TOOL_BY.get(name)
            if not t or t['scope'] not in scopes:
                st.log(tok['label'], 'tool_denied', name); return rpc_error(mid, -32602, f'tool not allowed: {name}')
            if not isinstance(args, dict): return rpc_error(mid, -32602, 'arguments must be object')
            try:
                import anyio
                out = await anyio.to_thread.run_sync(call_tool, name, args, tok['label'])
                st.log(tok['label'], 'tool_call', name)
                return rpc_result(mid, {'content': [{'type': 'text', 'text': json.dumps(out, ensure_ascii=False)}], 'structuredContent': out, 'isError': False})
            except Exception as e:
                st.log(tok['label'], 'tool_error', f'{name}:{type(e).__name__}')
                return rpc_result(mid, {'content': [{'type': 'text', 'text': f'Ошибка: {type(e).__name__}'}], 'isError': True})
        if method in ('resources/list', 'prompts/list'): return rpc_result(mid, {method.split('/')[0]: []})
        return rpc_error(mid, -32601, 'method not found')

    @app.post('/mcp')
    async def mcp(request: Request):
        tok = auth(request)
        if not tok: return unauthorized()
        try: body = await request.json()
        except Exception: return JSONResponse(rpc_error(None, -32700, 'parse error'), 400)
        if isinstance(body, list):
            out = [r for r in [await handle(m, tok) for m in body[:20]] if r]
            return JSONResponse(out) if out else Response(status_code=202)
        r = await handle(body, tok)
        return JSONResponse(r) if r else Response(status_code=202)

    @app.get('/mcp')
    def mcp_get(request: Request):
        if not auth(request): return unauthorized()
        return Response(status_code=405, headers={'Allow': 'POST'})
    @app.delete('/mcp')
    def mcp_del(): return Response(status_code=405)

    @app.get('/')
    def root(): return page('NEXUS Connect', '<h2>NEXUS Connect</h2><p class="muted">Адрес подключения для ChatGPT и Claude:</p><p><b>' + html.escape(RESOURCE) + '</b></p>')
    return app

def cli():
    import sys
    st = Store(Path(os.getenv('NEXUS_CONNECT_DB', '/var/lib/nexus-connect/connect.sqlite3')))
    cmd = sys.argv[1:] or ['list']
    with st.c() as d:
        if cmd[0] == 'list':
            for r in d.execute('SELECT id,label,name,approved,scopes,revoked,created FROM clients ORDER BY created'):
                print(f"{r['id']}  {r['label']:8} approved={r['approved']} revoked={r['revoked']} scopes='{r['scopes']}' name='{r['name']}' created={time.strftime('%Y-%m-%d %H:%M', time.gmtime(r['created']))}")
        elif cmd[0] == 'revoke' and len(cmd) == 2:
            d.execute('UPDATE clients SET revoked=1 WHERE id=? OR label=?', (cmd[1], cmd[1]))
            d.execute('DELETE FROM tokens WHERE client_id IN (SELECT id FROM clients WHERE revoked=1)'); print('REVOKED', cmd[1])
        elif cmd[0] == 'audit':
            for r in d.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 30'):
                print(time.strftime('%m-%d %H:%M:%S', time.gmtime(r['ts'])), r['who'], r['action'], r['info'])
        else: print('usage: python -m nexus_connect.app [list | revoke <client_id|Claude|ChatGPT> | audit]')

app = None
if __name__ == '__main__': cli()
