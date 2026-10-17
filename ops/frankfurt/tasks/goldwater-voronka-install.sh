#!/usr/bin/env bash
# Франкфурт: Воронка GOLD WATER — отдельная служба, в РАБОТЕ (dry_run из goldwater.toml). Paparazzi-Воронка не трогается.
set -Eeuo pipefail
[[ -s /etc/papa-voronka/goldwater.env ]] || { echo "NO_TOKEN (сначала: papa-update goldwater-voronka-token)"; exit 1; }
( cd /opt/papa/modules/voronka && python3 -m unittest -q tests/test_voronka.py 2>&1 | tail -1 )
install -d -m 700 -o papa-voronka -g papa-voronka /var/lib/papa-voronka/goldwater-pub
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-voronka-goldwater.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-voronka-goldwater; systemctl restart papa-voronka-goldwater; sleep 4
echo "papa-voronka-goldwater: $(systemctl is-active papa-voronka-goldwater) | paparazzi: $(systemctl is-active papa-voronka)"
systemd-run --quiet --wait --pipe -p User=papa-voronka \
  -p Environment="PAPA_VORONKA_CONFIG=/opt/papa/modules/voronka/goldwater.toml PAPA_VORONKA_DB=/var/lib/papa-voronka/goldwater.sqlite3 PAPA_VORONKA_IG_ENV=/etc/papa-voronka/goldwater.env" \
  -p WorkingDirectory=/opt/papa/modules/voronka python3 -m voronka status 2>&1 | head -25
echo "== GOLDWATER_VORONKA_INSTALLED "
