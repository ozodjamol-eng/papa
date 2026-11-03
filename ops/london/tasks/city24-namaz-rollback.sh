#!/usr/bin/env bash
# Откат city24-namaz-fix: вернуть базу времени намаза из копии.
set -uo pipefail
cd /opt/xojaobodcity24bot/app
DB=$(sudo -u xojaobodbot /opt/xojaobodcity24bot/venv/bin/python -c "import os;os.environ.setdefault('BOT_TOKEN','0:x');from bot.handlers import prayer as P;print(P.GENPLAN_PRAYER_DB)")
F=$(cat /opt/xojaobodcity24bot/deploy-backups/namaz-LAST 2>/dev/null); [[ -f "$F" ]] || { echo "нет копии"; exit 1; }
cp -a "$F" "$DB" && echo "возвращено из $F"
echo "== CITY24_NAMAZ_ROLLBACK_DONE"
