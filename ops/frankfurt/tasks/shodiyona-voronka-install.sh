#!/usr/bin/env bash
# Франкфурт: Воронка Shodiyona Mebel — отдельная служба, в РАБОТЕ (dry_run из shodiyona.toml). Paparazzi-Воронка не трогается.
set -Eeuo pipefail
[[ -s /etc/papa-voronka/shodiyona.env ]] || { echo "NO_TOKEN (сначала: papa-update shodiyona-voronka-token)"; exit 1; }
( cd /opt/papa/modules/voronka && python3 -m unittest -q tests/test_voronka.py 2>&1 | tail -1 )
install -d -m 700 -o papa-voronka -g papa-voronka /var/lib/papa-voronka/shodiyona-pub
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-voronka-shodiyona.service /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q papa-voronka-shodiyona; systemctl restart papa-voronka-shodiyona; sleep 4
echo "papa-voronka-shodiyona: $(systemctl is-active papa-voronka-shodiyona) | paparazzi: $(systemctl is-active papa-voronka)"
systemd-run --quiet --wait --pipe -p User=papa-voronka \
  -p Environment="PAPA_VORONKA_CONFIG=/opt/papa/modules/voronka/shodiyona.toml PAPA_VORONKA_DB=/var/lib/papa-voronka/shodiyona.sqlite3 PAPA_VORONKA_IG_ENV=/etc/papa-voronka/shodiyona.env" \
  -p WorkingDirectory=/opt/papa/modules/voronka python3 -m voronka status 2>&1 | head -25
echo "== SHODIYONA_VORONKA_INSTALLED "
