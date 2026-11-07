#!/usr/bin/env bash
# Франкфурт: ВКЛЮЧЕНИЕ Воронки PAPA (@paparazzi.uz → КАТТА ДАВРА) по команде владельца. Клиентские воронки не трогаются.
set -Eeuo pipefail
systemctl enable --now papa-voronka 2>&1 | tail -2 || true
sleep 6
echo "papa-voronka: $(systemctl is-active papa-voronka || true)"
journalctl -u papa-voronka -n 5 --no-pager -o cat | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g'
echo "== VORONKA_STARTED"
