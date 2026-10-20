#!/usr/bin/env bash
# 20.10 владелец: отчёты и одобрения — прямо в бот (главный пульт), без отдельных каналов.
# Делает /etc/papa-owner-bot.env (токен главного бота + id владельца — берутся из genplan.env на сервере, в чат не попадают),
# подключает его Разведке. Откат: rm /etc/papa-owner-bot.env (отчёты вернутся в «PAPA ОТЧЁТЫ»).
set -Eeuo pipefail
G=/etc/papa-genplan/genplan.env
TOK=$(grep -E '^GENPLAN_BOT_TOKEN=' "$G" | cut -d= -f2- | tr -d '"'"'"); IDS=$(grep -E '^OWNER_IDS=' "$G" | cut -d= -f2- | tr -d '"'"'")
[[ -n "$TOK" && -n "$IDS" ]] || { echo "НЕТ GENPLAN_BOT_TOKEN/OWNER_IDS в $G"; exit 1; }
( umask 027; printf 'OWNER_BOT_TOKEN=%s\nOWNER_IDS=%s\n' "$TOK" "$IDS" > /etc/papa-owner-bot.env )
chown root:papa-razvedka /etc/papa-owner-bot.env; chmod 640 /etc/papa-owner-bot.env
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /etc/systemd/system/
systemctl daemon-reload
for o in ${IDS//,/ }; do
  curl -s -o /dev/null -w "сообщение владельцу $o: HTTP %{http_code}\n" "https://api.telegram.org/bot$TOK/sendMessage" \
    --data-urlencode chat_id="$o" --data-urlencode text="📊 С сегодняшнего дня все отчёты (аудит, Разведка, Страж) приходят сюда, в бот. Каналы отчётов больше не нужны."
done
echo "== REPORTS_TO_BOT_DONE"
