#!/usr/bin/env bash
# Франкфурт: перезапуск Воронки Shodiyona Mebel после изменения shodiyona.toml (режим/тексты меняются в репозитории). Paparazzi не трогается.
set -Eeuo pipefail
systemctl restart papa-voronka-shodiyona; sleep 4
echo "papa-voronka-shodiyona: $(systemctl is-active papa-voronka-shodiyona) · $(grep '^dry_run' /opt/papa/modules/voronka/shodiyona.toml)"
echo "== SHODIYONA_VORONKA_RESTARTED"
