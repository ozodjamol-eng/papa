#!/usr/bin/env bash
# USTA: тесты → перезапуск службы papa-usta (после правок кода; токен не трогает). Откат: git revert + эта же задача.
set -euo pipefail
( cd /opt/papa/modules/usta && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-usta; sleep 3
echo "papa-usta: $(systemctl is-active papa-usta)"
journalctl -u papa-usta -n 5 -o cat --no-pager
echo "== USTA_RESTART_DONE"
