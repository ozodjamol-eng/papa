# Диагностика (только чтение): права аккаунта PAPA в Хўжаобод Сити 24. Ничего не публикует и не меняет.
set -Eeuo pipefail
[[ -s /etc/papa-tg/publisher.env ]] || { echo "NO_ACCOUNT"; exit 1; }
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xojaobod_check.py
