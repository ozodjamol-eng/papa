"""21.10 ХОТИРА: фото канала (скачала xotira_scan.py) → отпечатки в базу бота, файлы удаляются.
Потом отчёт: какие люди УЖЕ повторяются в канале (то же фото или то же имя) — видно, как обходили проверку.
Запуск в venv с OpenCV: /opt/papa-venv/xotira/bin/python xotira_prints.py"""
import os
import sys
import time

sys.path.insert(0, "/opt/papa/modules/xotira")
from xotira import bot as B, core, photo as ph  # noqa: E402

DB = os.environ.get("XOTIRA_DB", "/var/lib/papa-xotira/xotira.sqlite3")
SCAN = os.environ.get("XOTIRA_SCAN", "/var/lib/papa-xotira/scan")
CH = os.environ.get("XOTIRA_CHANNEL", "@XOTIRAXOJAOBOD").lstrip("@")
link = lambda i: f"https://t.me/{CH}/{i}"  # noqa: E731

db = B.connect(DB)
ok = bad = 0
for f in sorted(os.listdir(SCAN)) if os.path.isdir(SCAN) else []:
    if not f.endswith(".jpg"):
        continue
    with open(os.path.join(SCAN, f), "rb") as fh:
        data = fh.read()
    if B.index_print(db, int(f[:-4]), data):
        ok += 1
    else:
        bad += 1
    os.remove(os.path.join(SCAN, f))
total = db.execute("SELECT COUNT(*) FROM prints").fetchone()[0]
print(f"отпечатков добавлено: {ok} · фото не разобрать: {bad} · всего фото в базе: {total}")

# --- уже существующие повторы в канале: тяжело (~10 мин CPU, 21.10 перегрузил сервер) — только по XOTIRA_REPORT=1 ---
if os.environ.get("XOTIRA_REPORT") != "1":
    raise SystemExit(0)
t = time.time()
rows = [(r["msg_id"], ph.unpack(r["fp"])) for r in db.execute("SELECT msg_id, fp FROM prints ORDER BY msg_id")]
same_photo = []
for i in range(len(rows)):
    for j in range(i + 1, len(rows)):
        n = ph.match(rows[i][1], rows[j][1])
        if n >= ph.MAYBE_POINTS:
            same_photo.append((rows[i][0], rows[j][0], n))
print(f"\n📸 ОДНО И ТО ЖЕ ФОТО в канале дважды: {len(same_photo)} пар (проверка {time.time() - t:.0f} с)")
names = {r["msg_id"]: f"{r['name']} {r['born']}-{r['died']}" for r in db.execute("SELECT * FROM posts")}
for a, b, n in same_photo[:40]:
    print(f"  #{a} {names.get(a, '—')}  ↔  #{b} {names.get(b, '—')}  ({n} точек)  {link(b)}")

posts = [dict(r) for r in db.execute("SELECT * FROM posts ORDER BY msg_id")]
same_name = []
for i in range(len(posts)):
    for j in range(i + 1, len(posts)):
        a, b = posts[i], posts[j]
        if a["msg_id"] != b["msg_id"] and core.compare(a, b):
            same_name.append((a, b, core.compare(a, b)))
print(f"\n🔎 ПОХОЖЕЕ ИМЯ в канале дважды: {len(same_name)} пар (same — то же имя и годы)")
for a, b, c in same_name[:40]:
    print(f"  [{c}] #{a['msg_id']} {a['name']} {a['born']}-{a['died']}  ↔  #{b['msg_id']} {b['name']} {b['born']}-{b['died']}")
