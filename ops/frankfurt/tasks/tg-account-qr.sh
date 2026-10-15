# Вход нового аккаунта по QR-коду (если код не приходит). Сканируете QR телефоном с аккаунтом PAPA.
set -Eeuo pipefail
/opt/papa-venv/razvedka/bin/python -c 'import qrcode' 2>/dev/null || /opt/papa-venv/razvedka/bin/pip install -q qrcode
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/tg_account_qr.py
echo "== TG_ACCOUNT_SAVED (дальше: papa-update anon-test-account)"
