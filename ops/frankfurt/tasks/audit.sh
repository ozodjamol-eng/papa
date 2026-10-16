#!/usr/bin/env bash
# 🩺 Аудит PAPA вне расписания (полный, с отчётом в пульт).
set -Eeuo pipefail
systemctl start papa-audit@full.service || true
journalctl -u papa-audit@full.service -n 40 --no-pager -o cat | grep -v '^papa-audit' || true
echo "== AUDIT_DONE"
