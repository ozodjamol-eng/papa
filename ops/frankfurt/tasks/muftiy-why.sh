#!/usr/bin/env bash
# 🔎 31.10 (только чтение): почему Муфтий сегодня вышел дважды в Хўжаобод и не вышел в КАТТА ДАВРА в 22:00.
# Посты Муфтия обоих каналов за 2 дня (статус, время, отпечаток fp, двойники), лимит 20 у Давры, журнал 20:00–22:30.
set -uo pipefail
cd /opt/papa/modules/genplan
DB="${PAPA_GENPLAN_DB:-/var/lib/papa-genplan/genplan.sqlite3}" /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, os, sqlite3, tomllib
from genplan import plan, smart, store
cfg = tomllib.loads(open("config.toml", encoding="utf-8").read())
db = sqlite3.connect(f"file:{os.environ['DB']}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
now = dt.datetime.now(plan.TZ)
since = (now - dt.timedelta(days=2)).isoformat()
cols = [r[1] for r in db.execute("PRAGMA table_info(materials)")]
src = "source" if "source" in cols else "NULL AS source"
print("== материалы Муфтия (рубрика или текст) за 2 дня:")
q = (f"SELECT id, channel, rubric, status, urgent, stock, scheduled_at, created_at, fp, {src}, substr(replace(text, char(10), ' '),1,70) t "
     "FROM materials WHERE created_at>=? AND (rubric='Муфтий минбари' OR lower(text) LIKE '%muftiy%' OR text LIKE '%МУФТИЙ%' "
     "OR text LIKE '%Муфтий%' OR lower(text) LIKE '%minbar%') ORDER BY created_at")
for r in db.execute(q, (since,)):
    m = dict(r)
    print(f"  #{m['id']} {m['channel']:9} {m['rubric'] or '—':16} {m['status']:9} urg={m['urgent']} stock={m['stock']} "
          f"sched={(m['scheduled_at'] or '')[5:16]} created={m['created_at'][5:16]} fp={(m['fp'] or '')[:10]} src={m['source']} | {m['t']}")
print("== публикации сегодня, где материал — Муфтий:")
for r in db.execute("SELECT p.channel, p.slot, p.status, p.at, p.material_id, p.error, m.fp, m.rubric FROM publications p "
                    "LEFT JOIN materials m ON m.id=p.material_id WHERE p.slot_date=? AND (m.rubric='Муфтий минбари' "
                    "OR lower(m.text) LIKE '%muftiy%' OR m.text LIKE '%МУФТИЙ%' OR m.text LIKE '%Муфтий%') ORDER BY p.at",
                    (now.date().isoformat(),)):
    print("  ", dict(r))
print("== один отпечаток (fp) у обоих каналов:")
for r in db.execute("SELECT fp, group_concat(channel||':'||id||':'||status, ', ') g FROM materials WHERE fp IS NOT NULL AND created_at>=? "
                    "AND rubric='Муфтий минбари' GROUP BY fp HAVING count(*)>1", (since,)):
    print("  ", r["fp"][:12], r["g"])
for c in ("davra", "xojaobod"):
    ch = cfg["channels"][c]
    st = [m for m in store.stock(db, c) if m["rubric"] == smart.MINBAR]
    print(f"== {c}: запас Муфтия {len(st)}:", [(m["id"], smart.minbar_ok(m), smart.twin_taken(db, c, m)) for m in st], "(id, урок?, двойник?)")
    for h in ("20:00", "20:30", "21:00", "21:30"):
        t = plan.slot_time(now.date(), h)
        print(f"   лимит дня на {h}: осталось", smart.day_room(db, cfg, c, t))
    n = db.execute("SELECT source, COUNT(*) FROM pulse WHERE channel=? AND at>=? GROUP BY source",
                   (c, plan.slot_time(now.date(), "00:00").isoformat())).fetchall()
    print("   пульс сегодня по источникам:", [tuple(x) for x in n])
PY
echo "== журнал GENPLAN 20:00–22:30:"
journalctl -u papa-genplan --since "$(date +%F) 20:00" --until "$(date +%F) 22:30" --no-pager -o short-iso \
  | grep -iE "davra|xojaobod|муфт|minbar|лимит|запас|stock|опубл|publish|ошиб|error" | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | cut -c1-260 | tail -60
echo "== MUFTIY_WHY_DONE"
