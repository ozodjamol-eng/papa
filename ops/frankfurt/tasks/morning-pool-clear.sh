#!/usr/bin/env bash
# 🌅 Очистить непроверенный запас утренних видео (после охоты со слишком широким поиском) и пересобрать утро на завтра.
# Уже проверенные Gemini и годные (status=ok) остаются.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
POOL=/var/lib/papa-genplan/pool
systemctl stop papa-razvedka@hunt.service 2>/dev/null || true
systemctl stop papa-fabrika
cp -a "$DB" "$DB.bak-poolclear-$(date +%F-%H%M)"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan; sleep 3
sudo -u papa-genplan $PY - "$DB" "$POOL" <<'PY'
import sqlite3, sys
from pathlib import Path
db, pool = sqlite3.connect(sys.argv[1]), Path(sys.argv[2])
try:
    keep = {r[0] for r in db.execute("SELECT file FROM morning_pool WHERE status='ok'")}
    db.execute("DELETE FROM morning_pool WHERE status<>'ok'")
except sqlite3.OperationalError:
    keep = set()
n = 0
for f in pool.glob("*.mp4") if pool.exists() else []:
    if f.name not in keep:
        f.unlink(); n += 1
for f in (pool / "index.jsonl", ):
    if f.exists():
        f.unlink()
r = db.execute("UPDATE fixed_posts SET prepared=0, redo=1, tries=0, next_try=NULL, hub_msg=NULL, preview_sent=0, approved=0 "
               "WHERE status='pending' AND day=date('now','+5 hours','+1 day')").rowcount
db.commit()
print(f"удалено непроверенных видео: {n} · оставлено годных: {len(keep)} · утро на завтра на пересборку: {r}")
PY
rm -f /var/lib/papa-razvedka-pub/morning/*.mp4 /var/lib/papa-razvedka-pub/morning/index.jsonl
systemctl start papa-fabrika
echo "Через 3–5 минут в боте — новые предпросмотры (видео Pixabay или годное из запаса + новый текст)."
echo "== MORNING_POOL_CLEAR_DONE"
