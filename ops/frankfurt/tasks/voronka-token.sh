# Voronka: сохранить токен Instagram (вводится скрыто, в чат не копировать) и проверить его.
# Повторная проверка без ввода: papa-update voronka-check
set -Eeuo pipefail
python3 /opt/papa/ops/frankfurt/voronka_token.py
if id papa-voronka >/dev/null 2>&1; then chown -R papa-voronka:papa-voronka /etc/papa-voronka; { systemctl is-enabled -q papa-voronka && systemctl restart papa-voronka; } || true; fi   # 27.10: и после паузы стража
echo "== VORONKA_TOKEN_SAVED (/etc/papa-voronka/instagram.env, 0600)"
