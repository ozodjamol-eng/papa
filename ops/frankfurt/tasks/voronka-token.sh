# Voronka: сохранить токен Instagram (вводится скрыто, в чат не копировать) и проверить его.
# Повторная проверка без ввода: papa-update voronka-check
set -Eeuo pipefail
python3 /opt/papa/ops/frankfurt/voronka_token.py
echo "== VORONKA_TOKEN_SAVED (/etc/papa-voronka/instagram.env, 0600)"
