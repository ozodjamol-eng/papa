#!/usr/bin/env bash
# Франкфурт: перезапуск Воронки GOLD WATER после изменения goldwater.toml (режим/тексты меняются в репозитории). Paparazzi не трогается.
set -Eeuo pipefail
systemctl restart papa-voronka-goldwater; sleep 4
echo "papa-voronka-goldwater: $(systemctl is-active papa-voronka-goldwater) · $(grep '^dry_run' /opt/papa/modules/voronka/goldwater.toml)"
echo "== GOLDWATER_VORONKA_RESTARTED"
