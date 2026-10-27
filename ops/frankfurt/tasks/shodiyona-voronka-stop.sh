#!/usr/bin/env bash
# Франкфурт: ОСТАНОВКА Воронки Shodiyona (27.10, решение владельца): профиль shodiyona.mebel.uz новый, пароль сменён —
# пауза, чтобы Instagram не счёл авто-директ спамом. Paparazzi и GOLD WATER не трогаются. Страж по выключенной воронке молчит.
# Откат: papa-update shodiyona-voronka-start
set -Eeuo pipefail
systemctl disable --now papa-voronka-shodiyona 2>&1 | tail -2 || true
sleep 2
echo "papa-voronka-shodiyona: $(systemctl is-active papa-voronka-shodiyona || true) · enabled=$(systemctl is-enabled papa-voronka-shodiyona 2>/dev/null || true)"
echo "== SHODIYONA_VORONKA_STOPPED"
