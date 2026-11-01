#!/usr/bin/env bash
# 🏷 Маркировщик — проба (01.11): метит 1 видео + 1 фото из очереди каждого канала и шлёт владельцу в PAPA ШТАБ.
# В каналы ничего не публикует, базу только читает.
set -Eeuo pipefail
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
/opt/papa-venv/razvedka/bin/python -I /opt/papa/ops/frankfurt/marker_probe.py
