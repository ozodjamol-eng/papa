#!/usr/bin/env bash
# 🩺 Ежедневный аудит PAPA: полный в 02:00, утренняя проверка в 05:30 (только при поломке). Протокол — docs/AUDIT.md.
# Откат: systemctl disable --now papa-audit-full.timer papa-audit-quick.timer
set -Eeuo pipefail
A=/opt/papa/ops/frankfurt/audit
PY=/opt/papa-venv/razvedka/bin/python
out=$($PY -I "$A/test_audit.py" 2>&1) || { echo "$out" | tail -15; echo "ТЕСТЫ НЕ ПРОШЛИ"; exit 1; }
echo "тесты аудита: $(echo "$out" | tail -1)"
install -m 644 "$A/papa-audit@.service" "$A/papa-audit-full.timer" "$A/papa-audit-quick.timer" "$A/papa-audit-watch.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-audit-full.timer papa-audit-quick.timer papa-audit-watch.timer
echo "таймеры: full=$(systemctl is-active papa-audit-full.timer) quick=$(systemctl is-active papa-audit-quick.timer) watch=$(systemctl is-active papa-audit-watch.timer)"
systemctl start papa-audit@watch.service || true   # первый снимок админов каналов
journalctl -u papa-audit@watch.service -n 5 --no-pager -o cat | grep -v "^papa-audit" || true
echo "первый аудит сейчас (1–3 минуты), отчёт придёт в пульт:"
systemctl start papa-audit@full.service || true
journalctl -u papa-audit@full.service -n 40 --no-pager -o cat | grep -v '^papa-audit' || true
echo "== AUDIT_INSTALL_DONE"
