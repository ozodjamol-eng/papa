#!/usr/bin/env bash
# Переход Хўжаобода на PAPA (решение владельца 20.10). Запускать ПОСЛЕ genplan5-stop на Лондоне.
# Копия базы → перенос рекламы/Якуний/очистка тестовых остатков → флаг Куратора → перезапуск PAPA (config: mode=live, свой бот).
# Откат: cp копию базы обратно, rm /etc/papa-curator-xojaobod, в config.toml xojaobod без mode/bot_token_env, genplan-restart; Лондон genplan5-start.
set -Eeuo pipefail
grep -q '^XOJAOBOD_BOT_TOKEN=' /etc/papa-genplan/bots.env || { echo "❌ нет токена бота Хўжаобода"; exit 1; }
[[ -s /opt/papa/ops/frankfurt/xojaobod-handover.json ]] || { echo "❌ нет данных перехода"; exit 1; }
DB=/var/lib/papa-genplan/genplan.sqlite3; B=/var/backups/papa/genplan-before-xojaobod-live-$(date +%Y%m%d-%H%M).sqlite3
mkdir -p /var/backups/papa
systemctl stop papa-genplan papa-fabrika
cp -a "$DB" "$B"; echo "копия базы: $B"
# скрипт читает сессию аккаунта (root) и пишет базу — потом права файла базы возвращаются службе
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xojaobod_golive.py
chown papa-genplan:papa-genplan "$DB" "$DB"-wal "$DB"-shm 2>/dev/null || true
touch /etc/papa-curator-xojaobod; echo "Куратор Хўжаобода: включён"
TOK=$(grep -E '^XOJAOBOD_BOT_TOKEN=' /etc/papa-genplan/bots.env | cut -d= -f2-)
echo "вебхук GENPLAN 5 снят: $(curl -s "https://api.telegram.org/bot$TOK/deleteWebhook" | grep -o '"ok":[a-z]*')"; unset TOK
systemctl start papa-genplan papa-fabrika; sleep 8
echo "genplan: $(systemctl is-active papa-genplan) · fabrika: $(systemctl is-active papa-fabrika)"
journalctl -u papa-genplan -n 8 --no-pager -o cat | grep -v '^$' || true
echo "== XOJAOBOD_GOLIVE_DONE"
