# Вход нового рабочего аккаунта Telegram (для публикаций от имени группы и Разведки). Всё вводится здесь, на сервере.
set -Eeuo pipefail
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/tg_account_login.py
clear
echo "== TG_ACCOUNT_SAVED (дальше: papa-update anon-test-account)"
