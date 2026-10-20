#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: след рекламы GENPLAN 5 за 3 дня — что вышло, что нет и почему (campaigns, scheduled_posts, publication_log, журнал). Ничего не меняет.
set -uo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
hide(){ sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g' | cut -c1-260; }
python3 - "$DB" <<'PY' | hide
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
def cols(t): return [r[1] for r in db.execute(f"PRAGMA table_info('{t}')")]
print("== campaigns (активные):")
for r in db.execute("SELECT id,name,slot_time,start_date,end_date,weekdays,package_days,last_sent_date,last_error,preferred_daypart FROM campaigns WHERE active=1 AND deleted_at IS NULL"):
    print("  ", dict(r))
sc = cols("scheduled_posts")
print("== scheduled_posts рекламы с 2026-10-17:")
q = "SELECT id,kind,rubric,slot_key,source,subtype,scheduled_at,original_scheduled_at,status,posted_at,last_error,substr(caption,1,50) cap FROM scheduled_posts WHERE scheduled_at>='2026-10-17' AND (lower(coalesce(source,'')) LIKE '%camp%' OR lower(coalesce(rubric,'')) LIKE '%рек%' OR lower(coalesce(rubric,'')) LIKE '%rek%' OR lower(coalesce(subtype,'')) LIKE '%ad%' OR lower(coalesce(slot_key,'')) LIKE '%ad%' OR lower(coalesce(slot_key,'')) LIKE '%camp%' OR caption LIKE '%ЎТИН%' OR caption LIKE '%ИЖАРА%' OR caption LIKE '%РЕКЛАМА%') ORDER BY scheduled_at"
for r in db.execute(q): print("  ", dict(r))
pc = cols("publication_log"); print("== publication_log колонки:", ", ".join(pc))
tcol = next((c for c in pc if c in ("created_at", "published_at", "at", "ts")), pc[0])
for r in db.execute(f"SELECT * FROM publication_log WHERE {tcol}>='2026-10-18' ORDER BY {tcol}"):
    d = {k: (str(r[k])[:70] if r[k] is not None else None) for k in pc}
    s = " ".join(str(v) for v in d.values()).lower()
    if any(w in s for w in ("camp", "рек", "ad", "error", "fail")):
        print("  ", d)
PY
echo "== журнал GENPLAN 5 (реклама/ошибки, 3 дня):"
journalctl -u xojaobod-genplan-v3 --since "-3 days" --no-pager -o short-iso 2>/dev/null | grep -iE "campaign|кампан|реклам|ad_|Traceback|Error|Forbidden|failed" | hide | tail -60
echo "== GENPLAN5_ADS_TRACE_DONE"
