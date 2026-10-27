#!/usr/bin/env bash
# Франкфурт: ВКЛЮЧЕНИЕ Воронки Shodiyona после паузы (сначала новый токен: shodiyona-voronka-token). Paparazzi и GOLD WATER не трогаются.
set -Eeuo pipefail
systemctl enable --now papa-voronka-shodiyona 2>&1 | tail -2 || true
sleep 4
echo "papa-voronka-shodiyona: $(systemctl is-active papa-voronka-shodiyona || true) · $(grep '^dry_run' /opt/papa/modules/voronka/shodiyona.toml || true)"
echo "== SHODIYONA_VORONKA_STARTED"
