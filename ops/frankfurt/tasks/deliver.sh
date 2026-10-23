#!/usr/bin/env bash
# Отправить готовые видео владельцу в Telegram (личка от бота PAPA). Видео — в ветке outbox (кладёт ассистент).
set -Eeuo pipefail
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin outbox 2>/dev/null || { echo "NO_OUTBOX"; exit 1; }
git -C /opt/papa archive FETCH_HEAD | tar -x -C "$T"
[[ -d "$T/outbox" ]] || { echo "NO_VIDEO"; exit 1; }
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
python3 -I /opt/papa/ops/frankfurt/deliver.py "$T/outbox"
