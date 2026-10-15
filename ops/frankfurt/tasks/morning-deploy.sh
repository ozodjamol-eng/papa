#!/usr/bin/env bash
# 🌅 Утренний блок: копия базы → тесты → перезапуск GENPLAN и Fabrika → проверка прав бота в каналах и Pixabay →
# план утра на завтра. Fabrika сама подготовит посты и пришлёт владельцу предпросмотр (5–10 минут).
# Откат: в config.toml убрать строки morning = {...} (или enabled = false) и papa-update genplan-restart.
set -euo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
PY=/opt/papa-venv/razvedka/bin/python
cp -a "$DB" "$DB.bak-morning-$(date +%F-%H%M)"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
# неудачные попытки подготовки (до исправления) обнуляем; «Хайрли тонг», ушедший в запасной текст, — снова на видео
sudo -u papa-genplan $PY - "$DB" <<'PY' || true
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
try:
    a = db.execute("UPDATE fixed_posts SET tries=0, next_try=NULL WHERE status='pending' AND prepared=0").rowcount
    b = db.execute("UPDATE fixed_posts SET prepared=0, tries=0, next_try=NULL, preview_sent=0 "
                   "WHERE status='pending' AND key='greeting' AND hub_msg IS NULL AND prepared=1").rowcount
    db.commit(); print(f"попытки сброшены: {a + b}")
except sqlite3.OperationalError:
    pass
PY
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
import sys; sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import morning
key = os.environ.get("PIXABAY_API_KEY", "")
try:
    j = morning._http_json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": "autumn morning", "per_page": 3}))
    print(f"✅ Pixabay: {j.get('totalHits')} видео")
except Exception as e:
    print(f"❌ Pixabay: {e}")
print("ИИ:", "✅ Gemini" if os.environ.get("GEMINI_API_KEY") else "— нет ключа (будет шаблон)")
PY
sleep 90
echo "== Утро на завтра (prepared 1 = готово, предпросмотр у вас в боте):"
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
for r in db.execute("SELECT channel, key, substr(at,12,5), status, prepared, coalesce(error,'') FROM fixed_posts "
                    "WHERE day=date('now','+5 hours','+1 day') ORDER BY at, channel"):
    print("  ", *r)
PY
journalctl -u papa-fabrika -n 5 --no-pager -o cat
echo "== MORNING_DEPLOY_DONE"
