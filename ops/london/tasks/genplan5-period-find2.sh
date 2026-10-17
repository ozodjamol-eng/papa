#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ (шаг 2): правила времени GENPLAN 5 — почему «Фойдали» ушёл на завтра 09:00. Ничего не меняет.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; G=$D/genplan_v3
cd "$D" || { echo "NO_DIR $D"; exit 1; }
F=$(grep -rl --include=*.py "def next_allowed_start" $G | head -1); echo "== $F"
sed -n '1,140p' "$F" | cut -c1-190
echo "== дневные лимиты рубрик:"
grep -rn --include=*.py -iE "(daily|per_day|max_per|limit).{0,40}(useful|news|entertain|educat)|(useful|news|entertain|educat).{0,40}(daily|per_day|max|limit)" $G | grep -iv test | cut -c1-200 | head -20
echo "== посты сегодня/завтра по рубрикам:"
python3 - "$D/data/genplan_v3_production.db" <<'P'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for r in c.execute("select substr(scheduled_at,1,10) d, rubric, status, count(*) from scheduled_posts where scheduled_at>=date('now','-1 day') and source='inbox' group by d, rubric, status order by d"):
    print("  ", r)
for r in c.execute("select id, created_at, scheduled_at, rubric, subtype from scheduled_posts where source='inbox' order by id desc limit 3"):
    print("  последний:", r)
P
echo "== DONE_FIND2"
