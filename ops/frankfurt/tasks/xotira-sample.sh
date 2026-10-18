#!/usr/bin/env bash
# Только чтение: образцы подписей канала ХОТИРА.
set -euo pipefail
set -a; . /etc/papa-razvedka/telegram.env; set +a
/opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xotira_sample.py
echo "== XOTIRA_SAMPLE_DONE"
