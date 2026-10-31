#!/usr/bin/env bash
# 📚 Отдел Архив (31.10): таймер 00:40 · 03:40 · 12:40 + первый прогон сейчас. Только чтение наших каналов + посты в хабы банка.
# Откат: systemctl disable --now papa-archive.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_archive 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-archive.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-archive.timer
for u in collect run curate hunt pain sources insta; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — первый прогон по таймеру"; echo "== ARCHIVE_INSTALL_DONE"; exit 0; fi
done
systemctl start papa-razvedka@archive.service || true
journalctl -u papa-razvedka@archive.service -n 60 -o cat --no-pager | tail -n 50
echo "== ARCHIVE_INSTALL_DONE"
