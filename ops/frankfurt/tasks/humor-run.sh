#!/usr/bin/env bash
# 😂 Разведчик приколов (30.10): поиск каналов приколов (узбекские и международные) → проверка кадров на чужое лого →
# чистые сами подключаются источниками КАТТА ДАВРА (рубрика кулги). Подписок не делает, в каналы не пишет.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_scout 2>&1 | tail -1 )
set -a; . /etc/papa-razvedka/telegram.env; [[ -f /etc/papa-genplan/ai.env ]] && . /etc/papa-genplan/ai.env; set +a
export PYTHONUNBUFFERED=1
( cd /opt/papa/modules/razvedka && runuser -u papa-razvedka -- $PY -m razvedka humor ) | tail -n 40
echo "== HUMOR_DONE"
