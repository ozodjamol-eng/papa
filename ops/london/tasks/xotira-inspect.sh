#!/usr/bin/env bash
# Только чтение: как устроен бот ХОТИРА (старый NEXUS, /opt/nexus-gitops). Секреты не печатаются.
set -uo pipefail
R=/opt/nexus-gitops/repo
echo "== служба:"; systemctl cat ozod-nexus-control-bot.service 2>/dev/null | grep -vE 'Environment=.*(TOKEN|KEY|SECRET)' | head -30
echo "== статус:"; systemctl is-active ozod-nexus-control-bot; systemctl is-enabled ozod-nexus-control-bot 2>&1
echo "== файлы:"; ls -la $R $R/bot $R/bot/handlers 2>/dev/null | head -60
echo "== переменные .env (только имена):"; for f in $R/.env /opt/nexus-gitops/.env; do [[ -r $f ]] && { echo "$f:"; sed -E 's/=.*/=…/' "$f"; }; done
echo "== config.py (без значений секретов):"; grep -nE 'XOTIRA|xotira|MEMORY|memory|CHANNEL|BOT' $R/config.py | sed -E 's/(TOKEN|KEY|SECRET)[^=]*=.*/\1=…/' | head -40
echo "== memory.py:"; sed -n 1,400p $R/bot/handlers/memory.py
echo "== памяти/диск:"; free -m | head -2; df -h / | tail -1
echo "== журнал до остановки:"; journalctl -u ozod-nexus-control-bot -n 15 --no-pager -o cat 2>/dev/null | sed -E 's/[0-9]{8,}:[A-Za-z0-9_-]{30,}/<токен>/g'
echo "== XOTIRA_INSPECT_DONE"
