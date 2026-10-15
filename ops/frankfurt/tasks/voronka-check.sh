# Voronka: проверить сохранённый токен Instagram (ничего не меняет).
set -Eeuo pipefail
[[ -s /etc/papa-voronka/instagram.env ]] || { echo "NO_TOKEN (сначала papa-update voronka-token)"; exit 1; }
python3 /opt/papa/ops/frankfurt/voronka_token.py check
