#!/usr/bin/env bash
# Франкфурт: Воронка VOLIDAM (Умра) — отдельная служба, в РАБОТЕ (dry_run из volidam.toml). Paparazzi-Воронка не трогается.
set -Eeuo pipefail
[[ -s /etc/papa-voronka/volidam.env ]] || { echo "NO_TOKEN (сначала: papa-update volidam-voronka-token)"; exit 1; }
( cd /opt/papa/modules/voronka && python3 -m unittest -q tests/test_voronka.py 2>&1 | tail -1 )
install -d -m 700 -o papa-voronka -g papa-voronka /var/lib/papa-voronka/volidam-pub
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-voronka-volidam.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-voronka-volidam; systemctl restart papa-voronka-volidam; sleep 4
echo "papa-voronka-volidam: $(systemctl is-active papa-voronka-volidam) | paparazzi: $(systemctl is-active papa-voronka)"
systemd-run --quiet --wait --pipe -p User=papa-voronka \
  -p Environment="PAPA_VORONKA_CONFIG=/opt/papa/modules/voronka/volidam.toml PAPA_VORONKA_DB=/var/lib/papa-voronka/volidam.sqlite3 PAPA_VORONKA_IG_ENV=/etc/papa-voronka/volidam.env" \
  -p WorkingDirectory=/opt/papa/modules/voronka python3 -m voronka status 2>&1 | head -25
echo "== VOLIDAM_VORONKA_INSTALLED "
