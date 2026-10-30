#!/usr/bin/env bash
# 🔑 Ключ Apify (Instagram-тренды, 30.10). Вводит владелец в консоли Франкфурта — на экране не виден,
# в чат и репозиторий не попадает. Проверяет ключ и сохраняет в /etc/papa-razvedka/apify.env (0640).
set -euo pipefail
read -rsp "Вставьте ключ Apify (apify_api_...) и нажмите Enter: " KEY; echo
[[ ${#KEY} -ge 20 ]] || { echo "Ключ слишком короткий — скопируйте целиком"; exit 1; }
WHO=$(curl -fsS -H "Authorization: Bearer $KEY" https://api.apify.com/v2/users/me | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(d.get("username","?"), "| план:", (d.get("plan") or {}).get("id","?"))') \
  || { echo "APIFY_BAD — ключ не подошёл, скопируйте заново"; exit 1; }
echo "Apify: $WHO"
install -d -m 0750 -o root -g papa-razvedka /etc/papa-razvedka
umask 027
printf 'APIFY_TOKEN=%s\n' "$KEY" > /etc/papa-razvedka/apify.env
chown root:papa-razvedka /etc/papa-razvedka/apify.env; chmod 0640 /etc/papa-razvedka/apify.env
unset KEY
echo "== APIFY_OK"
