#!/usr/bin/env bash
# 🕌 23.10: пятничный пост PaparazziUZ (подготовлен juma-now) пропущен как «опоздание» — ensure_day вернул время 05:00.
# Публикует его СЕЙЧАС своим ботом-пультом PaparazziUZ в @ozodjamoll и отмечает done. Разово.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
sudo -u papa-genplan --preserve-env=PAPARAZZI_BOT_TOKEN,GENPLAN_BOT_TOKEN,HUB_CHAT_ID $PY - "$DB" <<'PY'
import datetime as dt, os, sys
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import morning as M, store, plan
from genplan.__main__ import cfg
from genplan.fabrika import upload_video
from genplan.service import share_button
C = cfg(); ch = C["channels"]["paparazzi"]
db = store.connect(sys.argv[1])
day = dt.datetime.now(plan.TZ).date()
r = db.execute("SELECT * FROM fixed_posts WHERE channel='paparazzi' AND day=? AND key='greeting'", (day.isoformat(),)).fetchone()
assert r and (r["source"] or "").startswith("juma:"), "нет пятничного поста PaparazziUZ"
assert r["status"] != "done", "уже опубликован"
f = M.own_file(r["id"])
assert f.exists(), f"нет файла видео {f}"
btn = share_button(ch)
res = upload_video(os.environ["PAPARAZZI_BOT_TOKEN"], "@" + ch["username"], f, r["text"] or "",
                   {"inline_keyboard": [[btn]]} if btn else None)
M.update(db, r["id"], status="done", message_id=int(res["message_id"]), error=None)
store.pulse_add(db, "paparazzi", dt.datetime.now(plan.TZ), "morning")
f.unlink(missing_ok=True)
print("PaparazziUZ: опубликовано, сообщение", res["message_id"])
PY
echo "== JUMA_PAPARAZZI_DONE"
