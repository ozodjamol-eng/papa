#!/usr/bin/env bash
# 03.11 СРОЧНО (владелец: «да»): XOJAOBOD CITY 24 показывал время намаза от 15.10 (из остановленного GENPLAN 5).
# Записать в его источник (prayer_schedules, confirmed=1) время, которое владелец ввёл в PAPA: с 29.10 — 06:00 12:45 15:40 17:25 18:55.
# Код бота не меняется. Копия базы перед записью; откат: papa-update city24-namaz-rollback (london).
set -uo pipefail
cd /opt/xojaobodcity24bot/app
DB=$(sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python -c "import os;os.environ.setdefault('BOT_TOKEN','0:x');from bot.handlers import prayer as P;print(P.GENPLAN_PRAYER_DB)")
[[ -f "$DB" ]] || { echo "СТОП: нет базы времени намаза"; exit 2; }
BK=/opt/xojaobodcity24bot/deploy-backups; mkdir -p $BK
cp -a "$DB" "$BK/namaz-$(date +%Y%m%d-%H%M%S).db" && ls -t $BK/namaz-*.db | head -1 > $BK/namaz-LAST && echo "копия: готово"
python3 - "$DB" <<'PY'
import sqlite3, sys, datetime as dt
db = sqlite3.connect(sys.argv[1]); db.row_factory = sqlite3.Row
cols = db.execute("PRAGMA table_info(prayer_schedules)").fetchall()
print("колонки:", [c["name"] for c in cols])
now = dt.datetime.now().isoformat(timespec="seconds")
rows = [("2026-10-23", "05:55", "12:45", "15:50", "17:35", "19:00"), ("2026-10-29", "06:00", "12:45", "15:40", "17:25", "18:55")]
for day, b, p, a, s, x in rows:
    if db.execute("SELECT 1 FROM prayer_schedules WHERE confirmed=1 AND effective_date=? AND bomdod=? AND asr=?", (day, b, a)).fetchone():
        print("уже есть:", day); continue
    val = {"effective_date": day, "valid_until": None, "confirmed": 1, "bomdod": b, "peshin": p, "asr": a, "shom": s, "xufton": x}
    for c in cols:
        n = c["name"]
        if n in val or n == "id" or c["pk"]:
            continue
        if c["notnull"] and c["dflt_value"] is None:
            low = n.lower()
            val[n] = now if ("at" in low or "time" in low or "date" in low) else ("papa-namaz-markazi" if c["type"].upper().startswith("TEXT") else 0)
    keys = list(val)
    db.execute(f"INSERT INTO prayer_schedules ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})", [val[k] for k in keys])
    print("записано:", day, b, p, a, s, x)
db.commit()
PY
cd /opt/xojaobodcity24bot/app && sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python -c "
import os,datetime as dt;os.environ.setdefault('BOT_TOKEN','0:x');from bot.handlers import prayer as P
print('бот теперь показывает сегодня:', P.confirmed_prayer_timings(dt.date.today()))"
echo "== CITY24_NAMAZ_FIX_DONE"
