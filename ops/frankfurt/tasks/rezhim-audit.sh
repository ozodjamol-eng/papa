#!/usr/bin/env bash
# 🗓 Аудит режима дня (01.11, владелец: «изучить папку банка, аудит всех наших каналов, режим дня по конкурентам»).
# Только чтение: база Разведки (14 дней), папка KATTA BANK (аккаунт Разведки). Ничего не публикует и не шлёт.
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
cd /opt/papa/modules/razvedka
/opt/papa-venv/razvedka/bin/python - <<'PY'
import asyncio, datetime as dt, os, sqlite3
from collections import Counter, defaultdict
from statistics import median
from zoneinfo import ZoneInfo
from razvedka import analyze, daymap
TZ = ZoneInfo("Asia/Tashkent")
db = sqlite3.connect("file:" + os.environ.get("PAPA_RAZVEDKA_DB", "/var/lib/papa-razvedka/razvedka.sqlite3") + "?mode=ro", uri=True)
db.row_factory = sqlite3.Row
posts, chans = analyze.load(db, 14)
print("===== A. КОНКУРЕНТЫ (14 дней)")
print("\n".join(daymap.render(daymap.build(posts, chans))))
print("===== B. НАШИ КАНАЛЫ (14 дней): час → постов, медиана просмотров, рубрики")
own = {cid: c for cid, c in chans.items() if c.get("is_own")}
for cid, c in own.items():
    ps = [p for p in posts if p["channel_id"] == cid]
    if not ps:
        print(f"📺 {c['title']}: нет постов"); continue
    med = median([p["views"] for p in ps if p["views"]] or [1])
    print(f"📺 {c['title']} (@{c['username']}) подписчиков {c.get('subscribers')} · постов {len(ps)} · медиана просмотров {med:.0f}")
    byh = defaultdict(list); byr = defaultdict(list)
    for p in ps:
        h = dt.datetime.fromisoformat(p["date_utc"]).astimezone(TZ).hour
        r = daymap.rubric(p.get("text") or "", False, c["title"])
        byh[h].append((p["views"] or 0, r)); byr[r].append(p["views"] or 0)
    for h in sorted(byh):
        v = [x for x, _ in byh[h]]; rs = Counter(r for _, r in byh[h]).most_common(3)
        print(f"  {h:02d}:00 · {len(v)} · ×{median(v)/med:.2f} · " + ", ".join(f"{daymap.NAME.get(r, r)} {n}" for r, n in rs))
    print("  рубрики: " + " · ".join(f"{daymap.NAME.get(r, r)} {len(v)} ×{median(v)/med:.2f}" for r, v in sorted(byr.items(), key=lambda kv: -len(kv[1]))))
print("===== C. ПАПКА KATTA BANK")
from razvedka.telegram import client_from_env
from razvedka.curate import folder_peers
async def bank():
    c = client_from_env(); await c.connect()
    try:
        f = await folder_peers(c)
        name = next((k for k in f if "bank" in k.lower() or "банк" in k.lower()), None)
        print("папки:", ", ".join(f)); print("банк:", name)
        for p in f.get(name, []):
            try:
                e = await c.get_entity(p); cnt = Counter(); last = None; n = 0
                async for m in c.iter_messages(e, limit=300):
                    n += 1; last = last or m.date
                    cnt["видео" if m.video else "фото" if m.photo else "текст" if not m.media else "другое"] += 1
                    if m.video and m.file and m.file.size and m.file.size > 20*1024*1024: cnt[">20МБ"] += 1
                print(f"  🏦 {e.title}: {n} (из последних 300) · " + ", ".join(f"{k} {v}" for k, v in cnt.items())
                      + f" · последний {last.astimezone(TZ):%d.%m %H:%M}" if last else f"  🏦 {e.title}: пусто")
            except Exception as ex:
                print("  ⚠️", type(ex).__name__, ex)
    finally:
        await c.disconnect()
asyncio.run(bank())
PY
echo "== REZHIM_AUDIT_DONE"
