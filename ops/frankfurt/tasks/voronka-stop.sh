#!/usr/bin/env bash
# Франкфурт: ОСТАНОВКА Воронки PAPA (@paparazzi.uz → КАТТА ДАВРА) по команде владельца. Клиентские воронки не трогаются.
# Включить обратно: papa-update voronka-start
set -Eeuo pipefail
systemctl disable --now papa-voronka 2>&1 | tail -2 || true
echo "papa-voronka: $(systemctl is-active papa-voronka || true)"
echo "== VORONKA_STOPPED"
