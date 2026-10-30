#!/usr/bin/env bash
# 🕌 30.10 владелец: в КАТТА ДАВРА сейчас — урок Муфтия (#muftiy_minbari) из запаса, ОТЛИЧНЫЙ от постов Хўжаобода.
# Берёт один материал запаса рубрики «Муфтий минбари» (smart.minbar_ok + не twin_taken) и ставит срочным — выйдет на ближайшем тике.
# Нет подходящего урока — ничего не публикует.
set -Eeuo pipefail
cd /opt/papa/modules/genplan
DB="${PAPA_GENPLAN_DB:-/var/lib/papa-genplan/genplan.sqlite3}" /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, os
from genplan import plan, smart, store
db = store.connect(os.environ["DB"])
now = dt.datetime.now(plan.TZ)
c = "davra"
pool = [m for m in store.stock(db, c) if m["rubric"] == smart.MINBAR and smart.minbar_ok(m) and not smart.twin_taken(db, c, m)]
if not pool:
    print("⚠️ в запасе КАТТА ДАВРА нет урока Муфтия, отличного от Хўжаобода — ничего не отправлено")
else:
    m = pool[-1]                                   # самый свежий урок
    store.update(db, m["id"], status="queued", urgent=1, stock=0, scheduled_at=now.isoformat())
    print(f"✅ КАТТА ДАВРА: урок Муфтия #{m['id']} выйдет в ближайшую минуту — {smart.short(m['text'], 60)}")
PY
echo "== MUFTIY_NOW_DONE"
