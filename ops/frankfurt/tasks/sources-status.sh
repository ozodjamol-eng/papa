#!/usr/bin/env bash
# 📡 Ход отбора источников (только чтение): состояние и последние строки журнала.
set -uo pipefail
echo "состояние: $(systemctl show -p ActiveState --value papa-razvedka@sources.service) · результат: $(systemctl show -p Result --value papa-razvedka@sources.service)"
journalctl -u papa-razvedka@sources.service --since "-6h" --no-pager -o cat | cut -c1-300 | tail -n "${1:-40}"
echo "== SOURCES_STATUS_DONE"
