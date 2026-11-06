#!/usr/bin/env bash
# 🕌 06.11 владелец: новые шаблоны обоев (ChatGPT, на весь экран) утверждены — «пускай выходят все варианты».
# Перерисовывает обои ТЕКУЩЕЙ недели по новым шаблонам → альбом для поста намаза в группе (с завтрашнего утра),
# Юкла тоже получает новые. Время намаза не меняется. Откат: git revert + эта же задача (перерисует старыми).
set -Eeuo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
/opt/papa-venv/razvedka/bin/python - <<'PY'
import importlib.util, re, shutil, sqlite3, datetime as dt
from pathlib import Path
spec = importlib.util.spec_from_file_location("r", "/opt/papa/modules/namaz_oboi/render.py"); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
db = sqlite3.connect("/var/lib/papa-genplan/genplan.sqlite3"); db.row_factory = sqlite3.Row
today = dt.date.today().isoformat()
row = db.execute("SELECT * FROM namaz_schedule WHERE day<=? ORDER BY day DESC LIMIT 1", (today,)).fetchone()
nxt = db.execute("SELECT * FROM namaz_schedule WHERE day>? ORDER BY day", (today,)).fetchall()
for s in [row, *nxt]:
    if not s:
        continue
    out = Path(f"/var/lib/papa-genplan/namaz/album-{s['day']}-v3")
    if out.exists():
        shutil.rmtree(out)
    files = r.render({k: s[k] for k in ("day", "bomdod", "peshin", "asr", "shom", "xufton")}, out)
    cap = re.sub(r"<[^>]+>", "", (out / "caption.txt").read_text(encoding="utf-8"))
    (out / "caption.txt").unlink()
    db.execute("UPDATE namaz_schedule SET photo=?, caption=? WHERE day=?", (str(out), cap, s["day"]))
    print(f"с {s['day']}: обоев {len(files)} → {out}")
n = db.execute("DELETE FROM namaz_posts WHERE key='table' AND status='pending' AND channel='xojaobod'").rowcount
db.commit()
print("ожидающих постов-таблиц пересоздаётся:", n)
PY
chown -R papa-genplan:papa-genplan /var/lib/papa-genplan/namaz
systemctl start papa-namaz-export.service && echo "Юкла: $(cat /var/lib/papa-namaz/oboi/CURRENT) · файлов: $(ls /var/lib/papa-namaz/oboi/$(cat /var/lib/papa-namaz/oboi/CURRENT)/*.jpg | wc -l)"
echo "== NAMAZ_OBOI_V3_DONE"
