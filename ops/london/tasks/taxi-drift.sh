#!/usr/bin/env bash
# Только чтение (02.11, такси «бригадир + команда», шаг 1): совпадает ли живой код XOJAOBOD CITY 24 с GitHub.
# Печатает md5 файлов кода, маркер, службу, свежие изменения и счётчики такси. Секреты не печатаются, ничего не меняет.
set -uo pipefail
A=/opt/xojaobodcity24bot/app
echo "== служба: $(systemctl is-active xojaobodcity24bot) · $(systemctl show -p ActiveEnterTimestamp --value xojaobodcity24bot)"
echo "== DEPLOYED_COMMIT: $(cat /opt/xojaobodcity24bot/DEPLOYED_COMMIT 2>/dev/null)"
echo "== git в app: $(git -C $A rev-parse --short HEAD 2>/dev/null || echo нет)"
echo "== md5 кода:"
( cd $A && find . -name '*.py' -not -path './venv/*' -not -path './backups/*' -not -path './outputs/*' -not -path './data/*' \
  -not -path './nexus_control_center_v1/*' -not -path './tests/*' | sort | xargs md5sum )
echo "== свежие изменения (30 дней):"
( cd $A && find . -name '*.py' -not -path './venv/*' -mtime -30 -printf '%TY-%Tm-%Td %TH:%TM %p\n' | sort | tail -25 )
echo "== счётчики такси:"
DB=$(ls $A/data/*.db $A/data/*.sqlite3 2>/dev/null | head -1)
[[ -n "$DB" ]] && /opt/xojaobodcity24bot/venv/bin/python - "$DB" <<'PY'
import sqlite3,sys
db=sqlite3.connect(f"file:{sys.argv[1]}?mode=ro",uri=True)
for q in ("SELECT count(*) FROM taxi_drivers","SELECT count(*) FROM taxi_drivers WHERE is_active=1",
          "SELECT count(*) FROM taxi_orders","SELECT count(*) FROM taxi_orders WHERE created_at>=date('now','-30 day')"):
    try: print(q,"→",db.execute(q).fetchone()[0])
    except Exception as e: print(q,"→",e)
print("taxi_drivers cols:",[r[1] for r in db.execute("PRAGMA table_info(taxi_drivers)")])
PY
echo "== TAXI_DRIFT_DONE"
