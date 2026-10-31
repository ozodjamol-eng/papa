#!/usr/bin/env bash
# 🏠 Отдельный ПЛАТНЫЙ ключ Gemini только для картинок дизайна (лимит расходов владелец ставит в Google — $5/мес).
# Основной бесплатный ключ (ассистент, посты, разведка) НЕ трогается. Ключ вводит владелец — не виден, в чат/репо не попадает.
set -euo pipefail
read -rsp "Вставьте ключ для картинок (OpenRouter sk-or-... или Google AIza...) и нажмите Enter: " KEY; echo
[[ ${#KEY} -ge 30 ]] || { echo "Ключ слишком короткий — скопируйте целиком"; exit 1; }
install -d -m 700 /etc/papa-dizayn
umask 077
if [[ "$KEY" == sk-or-* ]]; then printf 'OPENROUTER_API_KEY=%s\n' "$KEY" > /etc/papa-dizayn/img.env; else printf 'GEMINI_API_KEY=%s\n' "$KEY" > /etc/papa-dizayn/img.env; fi
echo "✅ Ключ сохранён (только для картинок дизайна). Проверка — задача dizayn-img."
