#!/usr/bin/env bash
# 🔎 Аудит контента (01.11, владелец: «зачем бот собирает такие вещи… разобраться по контенту, по тематике»).
# Только чтение (база read-only): материалы за 2 дня по каналам — источник, рубрика, статус, начало текста.
set -Eeuo pipefail
cd /opt/papa/modules/genplan
DB="${PAPA_GENPLAN_DB:-/var/lib/papa-genplan/genplan.sqlite3}" /opt/papa-venv/razvedka/bin/python - <<'PY'
import os, sqlite3, collections
db = sqlite3.connect(f"file:{os.environ['DB']}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
cols = {r[1] for r in db.execute("PRAGMA table_info(materials)")}
want = [c for c in ("id","channel","rubric","status","source","stock","auto","via","created_at","scheduled_at","text") if c in cols]
rows = db.execute(f"SELECT {','.join(want)} FROM materials WHERE created_at >= datetime('now','-2 day') ORDER BY id DESC").fetchall()
by = collections.Counter((r["channel"], r["source"] if "source" in cols else "", r["status"]) for r in rows)
print("== СВОДКА (канал · источник · статус: шт)")
for (c,s,st),n in by.most_common(80):
    print(f"  {c} · {s or '— (без источника)'} · {st}: {n}")
print("== ПОСЛЕДНИЕ 60")
for r in rows[:60]:
    t = (r["text"] or "").replace("\n"," ")[:90]
    print(f"  #{r['id']} {r['channel']} | {r['rubric']} | {r['status']} | src={r['source'] if 'source' in cols else ''} | via={r['via'] if 'via' in cols else ''} | {t}")
hit = db.execute("SELECT * FROM materials WHERE text LIKE '%МОБИЛ РАҚАМ%' ORDER BY id DESC LIMIT 3").fetchall()
print("== ПОСТ «МОБИЛ РАҚАМ»")
for r in hit:
    print("  ", {k: (str(r[k])[:120]) for k in r.keys() if k not in ("media",)})
PY
echo "== CONTENT_AUDIT_DONE"
