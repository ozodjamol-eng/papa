#!/usr/bin/env bash
# 🌅 07.11 «Ramadan Kareem» в ноябрьском «Хайрли тонг»: убрать праздничные видео из пула (видео, отменённое владельцем,
# + видео с праздником в подписи источника), вернуть отменённое утро завтра на пересборку с другим видео
# (превью снова придёт владельцу на «✅ Утверждаю»). База копируется перед правкой.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-occasion-$(date +%F-%H%M)"
systemctl stop papa-genplan
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys, datetime as dt
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import store, morning
store.connect(sys.argv[1]).close()
db = sqlite3.connect(sys.argv[1]); db.row_factory = sqlite3.Row
now = (dt.datetime.utcnow() + dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
bad = set()
for r in db.execute("SELECT source FROM fixed_posts WHERE key='greeting' AND status='cancelled' AND at>? AND source LIKE 'pool:%'", (now,)):
    bad.add(r["source"].split(":", 1)[1])
for r in db.execute("SELECT key, text FROM morning_pool WHERE status IN ('ok','new')"):
    if morning.occasion_in(r["text"]):
        bad.add(r["key"])
for k in bad:
    db.execute("UPDATE morning_pool SET status='rejected', reason='праздник не по дате (07.11)' WHERE key=?", (k,))
print("убрано из пула:", len(bad), sorted(bad)[:10])
n = db.execute("UPDATE fixed_posts SET status='pending', prepared=0, redo=1, tries=0, next_try=NULL, hub_msg=NULL, "
               "preview_sent=0, approved=0, source=NULL, error=NULL WHERE key='greeting' AND status='cancelled' AND at>?",
               (now,)).rowcount
db.commit(); print("утро на пересборку:", n)
PY
systemctl start papa-genplan; sleep 150
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
for r in db.execute("SELECT channel, day, substr(at,12,5), status, prepared, coalesce(source,'') FROM fixed_posts "
                    "WHERE key='greeting' AND day>=date('now','+5 hours') ORDER BY day, channel"):
    print("  ", *r)
PY
echo "== MORNING_FIX_OCCASION_DONE"
