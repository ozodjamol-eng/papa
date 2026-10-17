#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: как GENPLAN 5 (Хўжаобод) выбирает блок дня (утро/день/вечер/ночь) для поста из «➕ ПОСТ». Ничего не меняет.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; G=$D/genplan_v3
cd "$D" || { echo "NO_DIR $D"; exit 1; }
echo "== где выбирается период / блок дня:"
grep -rn --include=*.py -iE "period|ertalab|kunduz|kechqurun|утро|день|вечер|ночь|тонг|кечки|morning|evening|night" $G/telegram_ui.py | grep -iE "period|блок|block|утро|вечер" | cut -c1-200 | head -40
echo "== кнопки «➕ ПОСТ» / addroot:"
grep -n -E "addroot|Добавить пост|Время GENPLAN 5" $G/telegram_ui.py | cut -c1-220 | head -25
echo "== политика времени (content_time_policy / smart_queue):"
grep -rn --include=*.py -E "def (pick|choose|next|suggest|resolve)[a-z_]*\(|BLOCK|blocks|_PERIOD|PERIODS" $G/content_time_policy.py $G/smart_queue.py 2>/dev/null | cut -c1-200 | head -30
echo "== последние 15 запланированных постов (время, рубрика, статус):"
DB=$(ls $D/data/genplan_v3_production.db 2>/dev/null)
if [[ -n "$DB" ]]; then
  python3 - "$DB" <<'P'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table'")]
t = next((x for x in ("posts", "queue", "scheduled_posts") if x in tabs), None)
print("таблицы:", ", ".join(tabs)[:400])
if t:
    cols = [r[1] for r in c.execute(f"pragma table_info({t})")]
    print("колонки", t, ":", ", ".join(cols)[:400])
    tc = next((x for x in ("scheduled_at", "publish_at", "run_at", "due_at") if x in cols), None)
    keep = [x for x in (tc, "rubric", "status", "period", "slot_key", "source") if x and x in cols]
    if tc:
        for r in c.execute(f"select {','.join(keep)} from {t} order by {tc} desc limit 15"):
            print("  ", " | ".join(str(v) for v in r))
P
fi
echo "== журнал службы за час (время/период):"
journalctl -u xojaobod-genplan-v3 --since "-60 min" --no-pager -o cat 2>/dev/null | grep -iE "period|block|slot|schedul|запланир" | tail -15 | cut -c1-200
echo "== DONE_FIND"
