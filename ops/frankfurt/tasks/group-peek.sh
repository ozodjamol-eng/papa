#!/usr/bin/env bash
# Только чтение: что за сообщения в группе Хўжаобод (по id и поиск рекламы/Якуний). Ничего не публикует.
set -uo pipefail
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/group_peek.py
