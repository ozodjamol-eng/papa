# Вход в Telegram для Разведки. Всё вводится здесь, на сервере; в чат ничего не копировать.
set -Eeuo pipefail
cd /opt/papa/modules/razvedka
/opt/papa-venv/razvedka/bin/python -m razvedka login /etc/papa-razvedka/telegram.env
chmod 600 /etc/papa-razvedka/telegram.env
clear
echo "== LOGIN_SAVED (дальше: papa-update razvedka-collect)"
