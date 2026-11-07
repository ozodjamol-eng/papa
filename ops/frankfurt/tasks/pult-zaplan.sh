#!/usr/bin/env bash
# 🗓 07.11 владелец (путь А): готовый ролик Фабрики → очередь пульта канала на точное время, без ручной пересылки.
# Задание — ветка «pultq» (кладёт ассистент): pultq/job.json {channel, at "YYYY-MM-DDTHH:MM", rubric, text, video}
# + сам ролик (≤ 49 МБ). Бот канала шлёт ролик владельцу в личку (это и есть «источник» для copyMessage) →
# материал status=queued, scheduled_at=at, locked=1 → выходит по обычному протоколу пульта (подпись @канал добавит пульт).
# Публикует только в назначенное время; отменить — 🗑 в карточке пульта или задача заново с другим временем.
set -Eeuo pipefail
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin pultq 2>/dev/null || { echo "NO_PULTQ_BRANCH"; exit 1; }
git -C /opt/papa archive FETCH_HEAD | tar -x -C "$T"
[[ -f "$T/pultq/job.json" ]] || { echo "NO_JOB"; exit 1; }
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
cd /opt/papa/modules/genplan
JOB="$T/pultq" DB="${PAPA_GENPLAN_DB:-/var/lib/papa-genplan/genplan.sqlite3}" /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, json, os, tomllib, urllib.request, urllib.error, uuid
from pathlib import Path
from genplan import plan, store
job_dir = Path(os.environ["JOB"]); job = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
cfg = tomllib.loads(Path("config.toml").read_text(encoding="utf-8"))
ch = job["channel"]; chc = cfg["channels"][ch]
tok = os.environ.get(chc.get("bot_token_env") or "") or os.environ["GENPLAN_BOT_TOKEN"]
owner = int(os.environ["OWNER_IDS"].split(",")[0])
at = dt.datetime.fromisoformat(job["at"]).replace(tzinfo=plan.TZ)
now = dt.datetime.now(plan.TZ)
if at <= now + dt.timedelta(minutes=5):
    raise SystemExit(f"⛔ время {at:%d.%m %H:%M} уже прошло или слишком близко — ничего не поставлено")
vid = job_dir / job["video"]
if vid.stat().st_size > 49 * 1024 * 1024:
    raise SystemExit("⛔ ролик больше 49 МБ — бот не сможет его отправить")
b = uuid.uuid4().hex
cap = f"🗓 ФАБРИКА → пульт {chc['title']}: выйдет {at:%d.%m в %H:%M}"
parts = [f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
         for k, v in (("chat_id", str(owner)), ("caption", cap), ("supports_streaming", "true"),
                      ("width", "1080"), ("height", "1920"))]
parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{vid.name}\"\r\n"
             f"Content-Type: video/mp4\r\n\r\n".encode() + vid.read_bytes() + b"\r\n" + f"--{b}--\r\n".encode())
req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendVideo", data=b"".join(parts),
                             headers={"Content-Type": f"multipart/form-data; boundary={b}"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
except urllib.error.HTTPError as e:
    r = json.loads(e.read() or b"{}")
if not r.get("ok"):
    raise SystemExit(f"⛔ Telegram не принял ролик: {r.get('description')}")
msg = r["result"]; v = msg.get("video") or msg.get("document") or {}
media = [{"type": "video", "file_id": v.get("file_id"), "uid": v.get("file_unique_id")}]
db = store.connect(os.environ["DB"])
mid = store.add_material(db, owner, msg["message_id"], job["text"], True, media=media)
store.update(db, mid, channel=ch, rubric=job["rubric"], guessed=0, status="queued", locked=1,
             scheduled_at=at.isoformat(), via="fabrika")
print(f"✅ #{mid} {chc['title']}: «{job['text'].splitlines()[0][:50]}» → {at:%d.%m %H:%M} (рубрика {job['rubric']})")
lo, hi = (at - dt.timedelta(minutes=40)).isoformat(), (at + dt.timedelta(minutes=40)).isoformat()
for m in db.execute("SELECT id, rubric, scheduled_at, substr(text,1,40) t FROM materials WHERE channel=? AND status='queued' "
                    "AND scheduled_at BETWEEN ? AND ? AND id<>? ORDER BY scheduled_at", (ch, lo, hi, mid)).fetchall():
    print(f"   рядом в очереди: #{m['id']} {m['scheduled_at'][11:16]} {m['rubric']} — {m['t']!r}")
PY
echo "== PULT_ZAPLAN_DONE"
