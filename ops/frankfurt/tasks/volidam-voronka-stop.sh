#!/usr/bin/env bash
# Франкфурт: остановка Воронки VOLIDAM. Другие воронки не трогаются. Откат: papa-update volidam-voronka-install
set -Eeuo pipefail
systemctl disable --now papa-voronka-volidam 2>&1 | tail -2 || true
echo "papa-voronka-volidam: $(systemctl is-active papa-voronka-volidam || true)"
echo "== VOLIDAM_VORONKA_STOPPED"
