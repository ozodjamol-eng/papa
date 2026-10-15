# Тестовый контур: закрытый канал «PAPA TEST» + тестовый бот (через профиль владельца, по его разрешению).
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN"; exit 1; }
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/test_setup.py
echo "== TEST_SETUP_DONE (токен бота — только в /etc/papa-test/bot.env, 0600)"
