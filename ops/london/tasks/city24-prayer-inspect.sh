#!/usr/bin/env bash
# Только чтение (03.11, «🕌 Намоз маркази», шаг 1): откуда берёт время намаза XOJAOBOD CITY 24 (живой код). Ничего не меняет.
set -uo pipefail
A=/opt/xojaobodcity24bot/app
echo "== WEEKLY в prayer.py:"; grep -nE "WEEKLY_DISPLAY_DATE|WEEKLY_TIMINGS|^\s*\"(Fajr|Dhuhr|Asr|Maghrib|Isha|bomdod|peshin)" $A/bot/handlers/prayer.py | head -20
echo "== prayer_admin.py (команды и что меняет):"; grep -nE "def |CommandHandler|WEEKLY|json|write|open\(" $A/prayer_admin.py | head -40
echo "== кто ещё читает время:"; grep -rlnE "WEEKLY_TIMINGS|prayer_reference|aladhan" $A/bot $A/main.py $A/prayer_admin.py 2>/dev/null
echo "== напоминания (prayer_reminders):"; grep -nE "def |WEEKLY|timings|aladhan" $A/bot/services/prayer_reminders.py | head -20
ls -la $A/data/prayer_reference.json 2>/dev/null
echo "== CITY24_PRAYER_INSPECT_DONE"
