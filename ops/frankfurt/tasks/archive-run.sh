#!/usr/bin/env bash
# 📚 Архивариус — внеочередной прогон (31.10, план выходных: запас на 3 дня). Читает наши каналы, кладёт в хабы банка.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_archive 2>&1 | tail -1 )
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — повторить позже"; echo "== ARCHIVE_RUN_BUSY"; exit 0; fi
done
systemctl start papa-razvedka@archive.service || true
journalctl -u papa-razvedka@archive.service --since "-30 min" -o cat --no-pager | tail -n 60
echo "== ARCHIVE_RUN_DONE"
