#!/usr/bin/env bash
# Франкфурт: ОСТАНОВКА Воронки GOLD WATER (25.10, решение владельца): Instagram ограничил @goldwaterandijon (ссылки запрещены до 23.11) — авто-директ со ссылкой. Paparazzi и Shodiyona не трогаются. Откат: systemctl enable --now papa-voronka-goldwater
set -Eeuo pipefail
systemctl disable --now papa-voronka-goldwater 2>&1 | tail -2 || true
sleep 2
echo "papa-voronka-goldwater: $(systemctl is-active papa-voronka-goldwater || true) · enabled=$(systemctl is-enabled papa-voronka-goldwater 2>/dev/null || true)"
echo "papa-voronka (paparazzi): $(systemctl is-active papa-voronka 2>/dev/null || true) · shodiyona: $(systemctl is-active papa-voronka-shodiyona 2>/dev/null || true)"
echo "== GOLDWATER_VORONKA_STOPPED"
