# Путь А: проверка нового аккаунта как анонимного админа — только в тестовой группе PAPA TEST GROUP.
set -Eeuo pipefail
[[ -s /etc/papa-tg/publisher.env ]] || { echo "NO_ACCOUNT (сначала papa-update tg-account-login)"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/anon_test_account.py
