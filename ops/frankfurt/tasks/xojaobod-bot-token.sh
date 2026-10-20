#!/usr/bin/env bash
# 🤖 Токен бота-пульта Хўжаобода (XOJAOBODCITYAVTOPOST24) для PAPA. Вводит ВЛАДЕЛЕЦ в консоли Франкфурта:
# токен на экране не виден, в чат и репозиторий не попадает. Службы НЕ перезапускает — бот включится при переходе,
# когда GENPLAN 5 на Лондоне будет остановлен (один бот не может слушать две системы).
set -euo pipefail
VAR=XOJAOBOD_BOT_TOKEN
read -rsp "Вставьте токен бота XOJAOBODCITYAVTOPOST24 (из @BotFather → /mybots → бот → API Token) и нажмите Enter: " TOK; echo
[[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
ME=$(curl -s "https://api.telegram.org/bot$TOK/getMe")
echo "$ME" | grep -q '"ok":true' || { echo "❌ Токен не принят Telegram"; exit 1; }
echo "✅ бот: $(echo "$ME" | sed -E 's/.*"username":"([^"]+)".*/@\1/')"
umask 077
touch /etc/papa-genplan/bots.env
grep -v "^$VAR=" /etc/papa-genplan/bots.env > /etc/papa-genplan/bots.env.new || true
printf '%s=%s\n' "$VAR" "$TOK" >> /etc/papa-genplan/bots.env.new
mv /etc/papa-genplan/bots.env.new /etc/papa-genplan/bots.env
chown root:papa-genplan /etc/papa-genplan/bots.env; chmod 0640 /etc/papa-genplan/bots.env
unset TOK ME
echo "✅ Токен сохранён. Бот включится в PAPA при переходе (после остановки GENPLAN 5) — больше ничего делать не нужно."
echo "== XOJAOBOD_BOT_TOKEN_DONE"
