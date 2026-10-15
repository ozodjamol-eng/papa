#!/usr/bin/env bash
# Ключ ИИ (Anthropic) для Fabrika. Владелец вставляет ключ — он не показывается на экране и не попадает в чат/репозиторий.
set -euo pipefail
read -rsp "Вставьте ключ Anthropic (sk-ant-...) и нажмите Enter: " KEY; echo
[[ "$KEY" == sk-ant-* ]] || { echo "Это не похоже на ключ Anthropic (должен начинаться с sk-ant-)"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' https://api.anthropic.com/v1/models \
       -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01")
[[ "$code" == 200 ]] || { echo "AI_KEY_BAD (ответ $code) — проверьте ключ и пополнение баланса"; exit 1; }
umask 077
printf 'ANTHROPIC_API_KEY=%s\n' "$KEY" > /etc/papa-genplan/ai.env
chown root:papa-genplan /etc/papa-genplan/ai.env; chmod 0640 /etc/papa-genplan/ai.env
unset KEY
systemctl restart papa-fabrika papa-genplan; sleep 3
echo "fabrika: $(systemctl is-active papa-fabrika)"
echo "== AI_KEY_OK"
