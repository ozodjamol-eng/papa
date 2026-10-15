#!/usr/bin/env bash
# 🌅 Утренний блок: копия базы → тесты → перезапуск GENPLAN и Fabrika → проверка прав бота в каналах и Pixabay →
# план утра на завтра. Fabrika сама подготовит посты и пришлёт владельцу предпросмотр (5–10 минут).
# Откат: в config.toml убрать строки morning = {...} (или enabled = false) и papa-update genplan-restart.
set -euo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
PY=/opt/papa-venv/razvedka/bin/python
cp -a "$DB" "$DB.bak-morning-$(date +%F-%H%M)"
( cd /opt/papa/modules/genplan && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan; systemctl restart papa-fabrika; sleep 6
echo "genplan: $(systemctl is-active papa-genplan) · fabrika: $(systemctl is-active papa-fabrika)"
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/ai.env ] && . /etc/papa-genplan/ai.env; set +a
$PY - <<'PY'
import json, os, urllib.request, urllib.parse
tok = os.environ["GENPLAN_BOT_TOKEN"]
def tg(m, **p):
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/{m}?" + urllib.parse.urlencode(p), timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")
me = tg("getMe")["result"]
for ch in ("@kattadavrauz", "@ozodjamoll"):
    r = tg("getChatMember", chat_id=ch, user_id=me["id"])
    st = (r.get("result") or {})
    ok = st.get("status") == "administrator" and st.get("can_post_messages")
    print(f"{'✅' if ok else '❌'} бот @{me['username']} в {ch}: {st.get('status', r.get('description'))}"
          + ("" if ok else "  ← нужно сделать админом с правом публикации"))
key = os.environ.get("PIXABAY_API_KEY", "")
try:
    with urllib.request.urlopen("https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": "autumn morning", "per_page": 3}), timeout=20) as r:
        print(f"✅ Pixabay: {json.loads(r.read()).get('totalHits')} видео")
except Exception as e:
    print(f"❌ Pixabay: {e}")
print("ИИ:", "✅ Gemini" if os.environ.get("GEMINI_API_KEY") else "— нет ключа (будет шаблон)")
PY
sleep 20
echo "== Утро на завтра:"
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
for r in db.execute("SELECT channel, key, substr(at,12,5), status, prepared, coalesce(error,'') FROM fixed_posts "
                    "WHERE day=date('now','+5 hours','+1 day') ORDER BY at, channel"):
    print("  ", *r)
PY
journalctl -u papa-fabrika -n 5 --no-pager -o cat
echo "== MORNING_DEPLOY_DONE"
