#!/usr/bin/env bash
# Только чтение (03.11): исходник confirmed_prayer_timings в живом XOJAOBOD CITY 24 — откуда он берёт время.
set -uo pipefail
cd /opt/xojaobodcity24bot/app && sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python - <<'PY' 2>&1 | head -80
import inspect, os
os.environ.setdefault("BOT_TOKEN", "0:x")
from bot.handlers import prayer as P
print(inspect.getsource(P.confirmed_prayer_timings))
for name in dir(P):
    if "genplan" in name.lower() or "canonical" in name.lower() or name.isupper() and ("DB" in name or "PATH" in name):
        print(name, "=", getattr(P, name))
PY
grep -nE "genplan|sqlite|\.db|DB_PATH" /opt/xojaobodcity24bot/app/bot/handlers/prayer.py | head -20
echo "== CITY24_PRAYER_SRC_DONE"
