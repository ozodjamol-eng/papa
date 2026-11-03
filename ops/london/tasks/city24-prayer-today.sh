#!/usr/bin/env bash
# Только чтение (03.11): какое время намаза XOJAOBOD CITY 24 показывает людям СЕГОДНЯ (кнопка и напоминания) + файл замены.
set -uo pipefail
A=/opt/xojaobodcity24bot/app
cd $A && sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python - <<'PY' 2>&1 | tail -15
import datetime as dt, json, os
os.environ.setdefault("BOT_TOKEN", "0:x")
from bot.handlers import prayer as P
today = dt.date.today()
print("confirmed_prayer_timings(сегодня):", P.confirmed_prayer_timings(today))
print("WEEKLY (запасное):", P.WEEKLY_DISPLAY_DATE, P.WEEKLY_TIMINGS)
try:
    print("reference.display_date:", P.load_mosque_reference().display_date)
except Exception as e:
    print("reference:", e)
PY
echo "== data/prayer_reference.json:"; cat $A/data/prayer_reference.json | head -30
echo "== prayer_override.json:"; cat /var/lib/xojaobodcity24bot/prayer_override.json 2>/dev/null | head -30
echo "== prayer_admin: rewrite"; sed -n 100,135p $A/prayer_admin.py
echo "== CITY24_PRAYER_TODAY_DONE"
