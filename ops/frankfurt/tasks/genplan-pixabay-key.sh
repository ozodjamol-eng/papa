#!/usr/bin/env bash
# Ключ Pixabay (бесплатно) для утреннего пула: чистые сезонные видео. Ключ не виден на экране и не попадает в чат/репозиторий.
set -euo pipefail
read -rsp "Вставьте ключ Pixabay и нажмите Enter: " KEY; echo
[[ ${#KEY} -ge 20 ]] || { echo "Ключ слишком короткий — скопируйте целиком"; exit 1; }
code=$(curl -s -o /tmp/pixabay.json -w "%{http_code}" \
       "https://pixabay.com/api/videos/?key=$KEY&q=autumn+morning&per_page=3")
[[ "$code" == 200 ]] || { echo "PIXABAY_BAD (ответ $code) — проверьте ключ"; rm -f /tmp/pixabay.json; exit 1; }
echo "найдено осенних утренних видео: $(python3 -c 'import json;print(json.load(open("/tmp/pixabay.json")).get("totalHits","?"))')"
rm -f /tmp/pixabay.json
umask 077
touch /etc/papa-genplan/ai.env
grep -v '^PIXABAY_API_KEY=' /etc/papa-genplan/ai.env > /etc/papa-genplan/ai.env.new || true
printf 'PIXABAY_API_KEY=%s\n' "$KEY" >> /etc/papa-genplan/ai.env.new
mv /etc/papa-genplan/ai.env.new /etc/papa-genplan/ai.env
chown root:papa-genplan /etc/papa-genplan/ai.env; chmod 0640 /etc/papa-genplan/ai.env
unset KEY
echo "== PIXABAY_OK"
