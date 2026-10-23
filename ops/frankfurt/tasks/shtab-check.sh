#!/usr/bin/env bash
# 🏛 Только чтение: ключ PAPA ШТАБ сохранён? бот живой? админ PAPA HUB? Токен не печатается.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
[ -n "${SHTAB_BOT_TOKEN:-}" ] || { echo "❌ ключ PAPA ШТАБ не сохранён"; echo "== SHTAB_CHECK_DONE"; exit 0; }
$PY - <<'PY'
import json, os, urllib.request, urllib.parse, urllib.error
tok, hub = os.environ["SHTAB_BOT_TOKEN"], os.environ["HUB_CHAT_ID"]
def tg(m, **p):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}?" + urllib.parse.urlencode(p), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")
print("✅ ключ сохранён, бот @%s (%s)" % (me["result"]["username"], me["result"]["first_name"]) if me.get("ok") else "❌ ключ не принят Telegram")
if me.get("ok"):
    st = (tg("getChatMember", chat_id=hub, user_id=me["result"]["id"]).get("result") or {}).get("status", "нет")
    print(("✅" if st == "administrator" else "❌"), "админ PAPA HUB:", st)
PY
echo "== SHTAB_CHECK_DONE"
