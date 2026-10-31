#!/usr/bin/env bash
# Только чтение: утренние посты сегодня — с видео или текстом, ошибка, источник; журнал утра. Ничего не меняет.
set -uo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
sudo -u papa-genplan /opt/papa-venv/razvedka/bin/python - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for r in db.execute("SELECT channel, key, substr(at,1,16), status, prepared, tries, coalesce(source,''), coalesce(hub_msg,''), "
                    "coalesce(error,''), substr(coalesce(text,''),1,60) FROM fixed_posts "
                    "WHERE substr(at,1,10) IN (date('now','+5 hours'), date('now','+5 hours','-1 day')) ORDER BY at"):
    print(" | ".join(str(x) for x in r))
try:
    print("пул:", dict(db.execute("SELECT status, count(*) FROM morning_pool GROUP BY status").fetchall()))
    import os
    from pathlib import Path
    d = Path("/var/lib/papa-genplan/pool")
    rows = db.execute("SELECT key, file, msg_id, weekday, season FROM morning_pool WHERE status='ok'").fetchall()
    on = sum(1 for r in rows if r[1] and (d / r[1]).exists())
    mid = sum(1 for r in rows if r[2])
    print(f"годные: {len(rows)} · файл на сервере: {on} · есть пост в пуле (msg_id): {mid} · папка {d} есть: {d.is_dir()}")
    print("годные по дню/сезону:", dict(db.execute("SELECT coalesce(weekday,'общ')||'/'||coalesce(season,'neutral'), count(*) FROM morning_pool WHERE status='ok' GROUP BY 1").fetchall()))
except sqlite3.OperationalError as e:
    print("пул:", e)
PY
echo "== журнал утра"
journalctl -u papa-genplan -u papa-fabrika --since "-14h" --no-pager -o cat | grep -iE "morning|утр|хайрли|видео|pool|vision" | tail -40
echo "== ошибки подготовки (morning:)"
journalctl -u papa-genplan -u papa-fabrika --since "-20h" --no-pager -o cat | grep -E "^morning:|Видео не получилось|нет годного" | sort | uniq -c | sort -rn | head -25
echo "== MORNING_WHY_DONE"
