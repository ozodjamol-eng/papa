#!/usr/bin/env bash
# Только чтение: ХАБы каналов — узнал ли бот свой хаб, админ ли он там, сколько материала пришло из хаба.
# Ничего не публикует и не перезапускает. Токены не печатаются.
set -uo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
sudo -E -u papa-genplan $PY - "$DB" <<'PY'
import json, os, sqlite3, sys, urllib.parse, urllib.request
db = sqlite3.connect(sys.argv[1]); db.row_factory = sqlite3.Row
def tg(tok, m, **p):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}?" + urllib.parse.urlencode(p), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
for name, key, var in (("КАТТА ДАВРА", "davra", "GENPLAN_BOT_TOKEN"), ("PaparazziUZ", "paparazzi", "PAPARAZZI_BOT_TOKEN"), ("Хўжаобод", "xojaobod", "GENPLAN_BOT_TOKEN")):
    tok = os.environ.get(var)
    row = db.execute("SELECT v FROM kv WHERE k=?", (f"hub_{key}",)).fetchone()
    hid = row["v"] if row else None
    print(f"== {name}")
    if not hid:
        print("   хаб ещё не узнан — бот узнаёт его по первому посту в хабе")
    elif tok:
        me = tg(tok, "getMe")["result"]
        chat = tg(tok, "getChat", chat_id=hid).get("result") or {}
        st = (tg(tok, "getChatMember", chat_id=hid, user_id=me["id"]).get("result") or {})
        ok = st.get("status") == "administrator"
        print(f"   хаб: «{chat.get('title', '?')}» · @{me['username']}: {'✅ админ' if ok else '❌ ' + str(st.get('status'))}")
    n = db.execute("SELECT status, stock, count(*) c FROM materials WHERE channel=? AND hub_chat=? GROUP BY status, stock",
                   (key, hid or "x")).fetchall()
    print("   материал из хаба:", ", ".join(f"{r['status']}{'/запас' if r['stock'] else ''}: {r['c']}" for r in n) or "пока нет")
PY
echo "== последние строки журнала про хабы:"
journalctl -u papa-genplan --since "-2h" --no-pager -o cat | grep -iE "hub|хаб|album" | tail -10
echo "== HUBS_CHECK_DONE"
