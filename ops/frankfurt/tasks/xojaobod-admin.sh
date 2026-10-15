# Путь А: аккаунт PAPA — анонимный админ Хўжаобод Сити 24 (по утверждению владельца). Ничего не публикует.
set -Eeuo pipefail
[[ -s /etc/papa-tg/publisher.env ]] || { echo "NO_ACCOUNT"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xojaobod_admin.py
