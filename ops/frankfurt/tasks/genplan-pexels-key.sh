#!/usr/bin/env bash
# Ключ Pexels (бесплатно) для утреннего пула: чистые сезонные видео. Ключ не виден на экране и не попадает в чат/репозиторий.
set -euo pipefail
read -rsp "Вставьте ключ Pexels и нажмите Enter: " KEY; echo
[[ ${#KEY} -ge 20 ]] || { echo "Ключ слишком короткий — скопируйте целиком"; exit 1; }
code=$(curl -s -o /tmp/pexels.json -w '%{http_code}' -H "Authorization: $KEY" \
       "https://api.pexels.com/videos/search?query=autumn%20morning&per_page=3&orientation=portrait")
[[ "$code" == 200 ]] || { echo "PEXELS_BAD (ответ $code) — проверьте ключ"; rm -f /tmp/pexels.json; exit 1; }
echo "найдено осенних утренних видео: $(python3 -c 'import json;print(json.load(open("/tmp/pexels.json")).get("total_results","?"))')"
rm -f /tmp/pexels.json
umask 077
touch /etc/papa-genplan/ai.env
grep -v '^PEXELS_API_KEY=' /etc/papa-genplan/ai.env > /etc/papa-genplan/ai.env.new || true
printf 'PEXELS_API_KEY=%s\n' "$KEY" >> /etc/papa-genplan/ai.env.new
mv /etc/papa-genplan/ai.env.new /etc/papa-genplan/ai.env
chown root:papa-genplan /etc/papa-genplan/ai.env; chmod 0640 /etc/papa-genplan/ai.env
unset KEY
echo "== PEXELS_OK"
