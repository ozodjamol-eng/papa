# Тест: публикация в группе от имени самой группы (анонимный админ-бот). Только тестовая группа, рабочие каналы не трогаются.
set -Eeuo pipefail
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/anon_test.py
