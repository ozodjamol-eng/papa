#!/usr/bin/env bash
# 🔎 02.11 (только чтение): видят ли боты полки Маркировщика «· ГОТОВО» (посты КАТТА ДАВРА / PaparazziUZ падают «chat not found»).
set -uo pipefail
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
/opt/papa-venv/razvedka/bin/python - <<'PY'
import json, os, sqlite3, urllib.request
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True)
shelves = dict((k[13:], int(v)) for k, v in db.execute("SELECT k, v FROM kv WHERE k LIKE 'marker_shelf_%'"))
toks = {"main": os.environ.get("GENPLAN_BOT_TOKEN"), "xojaobod": os.environ.get("XOJAOBOD_BOT_TOKEN"),
        "paparazzi": os.environ.get("PAPARAZZI_BOT_TOKEN")}
def api(tok, m, **p):
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{m}", data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=20))
    except urllib.error.HTTPError as e:
        return json.load(e)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "description": type(e).__name__}
for name, tok in toks.items():
    if not tok:
        print(name, "— нет токена"); continue
    me = api(tok, "getMe").get("result", {})
    for code, sid in shelves.items():
        r = api(tok, "getChatMember", chat_id=sid, user_id=me.get("id"))
        print(f"бот {name} (@{me.get('username')}) → полка {code}: {r.get('result', {}).get('status') if r.get('ok') else r.get('description')}")
for code in shelves:
    n = db.execute("SELECT count(*) FROM materials WHERE channel=? AND hub_chat=? AND status IN ('queued','draft')", (code, shelves[code])).fetchone()[0]
    f = db.execute("SELECT count(*) FROM publications p JOIN materials m ON m.id=p.material_id WHERE p.channel=? AND m.hub_chat=? AND p.status='failed'",
                   (code, shelves[code])).fetchone()[0]
    print(f"{code}: ждут выхода с полки {n}, упали с полки {f}")
PY
echo "== MARKER_SHELF_CHECK_DONE"
