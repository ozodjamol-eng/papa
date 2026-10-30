#!/usr/bin/env bash
# 🔭 Разведчик каналов (30.10): глобальный поиск Telegram → большие каналы для папки XOJAOBOD RAQIB, которых нет
# в папках владельца. Только чтение: ничего не подписывает, не пишет. Откат не нужен.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_scout 2>&1 | tail -1 )
set -a; . /etc/papa-razvedka/telegram.env; set +a
export PYTHONUNBUFFERED=1
( cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -m razvedka scout ) | tail -n 40
echo "== SCOUT_DONE"
