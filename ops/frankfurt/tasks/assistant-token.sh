#!/usr/bin/env bash
# 🤖 ИИ-ассистент личного Telegram (@Ozodjamol) через Telegram Business — решение владельца 17.10.
# Токен вводит владелец сам (на экране не виден, в чат и репозиторий не попадает). Ставит службу papa-assistant.
# Откат: systemctl disable --now papa-assistant  (и в Telegram: Настройки → Telegram для бизнеса → Чат-боты → отключить)
set -euo pipefail
read -rsp "Вставьте токен бота-ассистента (из @BotFather) и нажмите Enter: " TOK; echo
[[ "$TOK" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{30,}$ ]] || { echo "Это не похоже на токен — скопируйте целиком из @BotFather"; exit 1; }
TOK="$TOK" python3 - <<'PY'
import json, os, sys, urllib.request, urllib.error
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{os.environ['TOK']}/getMe", timeout=20) as r:
        me = json.loads(r.read())["result"]
except Exception as e:
    sys.exit(f"❌ Токен не принят Telegram: {e}")
print(f"✅ бот @{me['username']} ({me['first_name']})")
print("✅ режим Business включён" if me.get("can_connect_to_business") else
      "⚠️ Режим Business у бота ВЫКЛЮЧЕН: @BotFather → /mybots → бот → Bot Settings → Business Mode → Turn on")
PY
id -u papa-assistant >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin papa-assistant
install -d -m 0750 -o root -g papa-assistant /etc/papa-assistant
umask 077
printf 'ASSISTANT_BOT_TOKEN=%s\n' "$TOK" > /etc/papa-assistant/bot.env
chown root:papa-assistant /etc/papa-assistant/bot.env; chmod 0640 /etc/papa-assistant/bot.env
unset TOK
( cd /opt/papa/modules/reklama && python3 -I -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-assistant.service /etc/systemd/system/papa-assistant.service
systemctl daemon-reload
systemctl enable -q --now papa-assistant; systemctl restart papa-assistant; sleep 5
echo "assistant: $(systemctl is-active papa-assistant)"
journalctl -u papa-assistant -n 5 --no-pager -o cat | grep -v "^$" || true
echo "📱 Дальше в Telegram: Настройки → Telegram для бизнеса → Чат-боты → выберите этого бота."
echo "   Затем откройте бота и нажмите «Старт» — сюда будут приходить уведомления."
echo "== ASSISTANT_DONE"
