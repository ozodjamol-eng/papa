#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: всё для передачи Хўжаобода в PAPA — время намаза, что стоит в очереди GENPLAN 5, id опубликованных реклам.
set -uo pipefail
DB=/opt/xojaobod-genplan-v5/data/genplan_v3_production.db
python3 - "$DB" <<'PY' | sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g'
import sqlite3, sys, json
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
print("== NAMAZ_JSON")
print(json.dumps([dict(r) for r in db.execute("SELECT effective_date, valid_until, bomdod, peshin, asr, shom, xufton, confirmed FROM prayer_schedules ORDER BY effective_date")], ensure_ascii=False))
print("== PENDING")
for r in db.execute("SELECT id, kind, rubric, slot_key, source, scheduled_at, is_fixed, substr(replace(caption, char(10), ' '),1,70) cap FROM scheduled_posts WHERE status='pending' ORDER BY scheduled_at"):
    print("  ", dict(r))
print("== ADS_PUBLISHED")
for r in db.execute("SELECT id, slot_key, scheduled_at, status, published_message_id FROM scheduled_posts WHERE rubric='ad' AND scheduled_at>='2026-10-15' ORDER BY scheduled_at"):
    print("  ", dict(r))
print("== FIXED_SLOTS")
for r in db.execute("SELECT slot_key, kind, label, rubric, default_time, enabled FROM fixed_slots"):
    print("  ", dict(r))
PY
echo "== GENPLAN5_HANDOVER_DONE"
