#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ (19.10, владелец «можно»): рекламные кампании GENPLAN 5 перед переводом Хўжаобода на PAPA.
# Находит таблицы рекламы в базе GENPLAN 5, показывает колонки и активные/недавние кампании. Ничего не меняет.
set -uo pipefail
DB=/opt/xojaobod-genplan-v5/data/genplan_v3_production.db
python3 - "$DB" <<'PY'
import sqlite3, sys, re, datetime as dt
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
now = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=5))
print("сейчас (Ташкент):", now.strftime("%Y-%m-%d %H:%M"))
tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
ad = [t for t in tables if re.search(r"ad|rekl|reklam|campaign|elon|eʼlon|order|package|paket|sponsor", t, re.I)]
print("все таблицы:", ", ".join(tables))
print("таблицы рекламы:", ", ".join(ad) or "не найдены")
def short(v):
    s = "" if v is None else str(v).replace("\n", " ")
    s = re.sub(r"[0-9]{6,12}:[A-Za-z0-9_-]{30,}", "<скрыто>", s)
    return s[:90]
for t in ad:
    cols = [r[1] for r in db.execute(f"PRAGMA table_info('{t}')")]
    n = db.execute(f"SELECT count(*) FROM '{t}'").fetchone()[0]
    print(f"\n== {t}: строк {n}\n   колонки: {', '.join(cols)}")
    st = next((c for c in cols if c in ("status", "state", "is_active", "active")), None)
    end = next((c for c in cols if re.search(r"end|until|expire|finish|last_day|to_date", c, re.I)), None)
    order = next((c for c in cols if re.search(r"created|start|date|_at$", c, re.I)), cols[0])
    where, args = [], []
    if st:
        where.append(f"(lower(cast({st} as text)) IN ('active','running','pending','paid','approved','scheduled','1','true','new','queued'))")
    if end:
        where.append(f"({end} IS NULL OR {end} >= ?)"); args.append(now.strftime("%Y-%m-%d"))
    q = f"SELECT * FROM '{t}'" + (f" WHERE {' OR '.join(where)}" if where else "") + f" ORDER BY {order} DESC LIMIT 40"
    rows = db.execute(q, args).fetchall()
    print(f"   активные/текущие (по {st or '—'} / {end or '—'}): {len(rows)}")
    for r in rows:
        print("   •", " | ".join(f"{c}={short(r[c])}" for c in cols if r[c] not in (None, "")))
PY
echo "== GENPLAN5_ADS_LIST_DONE"
