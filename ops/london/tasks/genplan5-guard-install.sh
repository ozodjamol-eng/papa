#!/usr/bin/env bash
# 🛡 Страж рекламы GENPLAN 5: таймер каждые 10 мин. База — только чтение; GENPLAN 5 не трогается.
# Откат: systemctl disable --now papa-genplan5-guard.timer
set -Eeuo pipefail
A=/opt/papa/ops/london/guard
python3 -I "$A/test_guard.py" 2>&1 | tail -1
install -m 644 "$A/papa-genplan5-guard.service" "$A/papa-genplan5-guard.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-genplan5-guard.timer
echo "таймер: $(systemctl is-active papa-genplan5-guard.timer), следующий: $(systemctl show -p NextElapseUSecRealtime --value papa-genplan5-guard.timer)"
echo "== проверка сейчас (с отправкой тревоги владельцу, если есть беда):"
python3 -I "$A/genplan5_guard.py"
echo "== GENPLAN5_GUARD_INSTALL_DONE"
