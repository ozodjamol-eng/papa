#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: полный текст утреннего поста 07:00 и «Якуний пост» 22:00 GENPLAN 5 + как выбирается Якуний (пресет).
set -uo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
python3 - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
for sk in ("system_morning", "final_post"):
    print(f"== {sk} (последние 3)")
    for r in db.execute("SELECT scheduled_at, kind, caption, media_refs IS NOT NULL AND media_refs<>'[]' has_media FROM scheduled_posts WHERE slot_key=? ORDER BY scheduled_at DESC LIMIT 3", (sk,)):
        print(f"--- {r['scheduled_at']} · {r['kind']} · медиа={r['has_media']}\n{r['caption']}")
print("== fixed_slots final_post")
for r in db.execute("SELECT slot_key, label, default_time, content_kind, substr(coalesce(content_caption,''),1,300) cap, content_media_refs IS NOT NULL m FROM fixed_slots"):
    print(dict(r))
PY
echo "== final_post.py (начало)"; sed -n 1,60p $G/genplan_v3/final_post.py | cut -c1-160
echo "== GENPLAN5_PARITY2_DONE"
