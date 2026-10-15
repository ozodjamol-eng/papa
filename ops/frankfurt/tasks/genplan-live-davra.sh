#!/usr/bin/env bash
# КАТТА ДАВРА → рабочий режим (mode="live" в config.toml). Тестовые материалы из очереди Давры, добавленные ДО перехода,
# снимаются (status=rejected), чтобы тесты не вышли в настоящий канал. Откат: mode="shadow" и genplan-restart.
set -euo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-$(date +%F-%H%M)"
echo "Снимаю тестовые материалы из очереди КАТТА ДАВРА:"
sqlite3 "$DB" "SELECT id, rubric, substr(replace(text,char(10),' '),1,50) FROM materials WHERE channel='davra' AND status IN ('queued','draft');" || true
sqlite3 "$DB" "UPDATE materials SET status='rejected' WHERE channel='davra' AND status IN ('queued','draft');"
( cd /opt/papa/modules/genplan && /opt/papa-venv/razvedka/bin/python -m unittest -q tests/test_genplan.py tests/test_hub_service.py 2>&1 | tail -1 )
grep -n 'mode = "live"' /opt/papa/modules/genplan/config.toml
systemctl restart papa-genplan; sleep 5
systemctl is-active papa-genplan
( cd /opt/papa/modules/genplan && sudo -u papa-genplan env PAPA_GENPLAN_DB=$DB /opt/papa-venv/razvedka/bin/python -m genplan plan 2>/dev/null | head -3 ) || true
echo "== DAVRA_LIVE_DONE"
