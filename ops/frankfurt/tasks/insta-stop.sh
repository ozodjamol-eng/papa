#!/usr/bin/env bash
# ⏸ Остановить агента Instagram-трендов (12.11, владелец: «останови»). Таймер выключен, текущий прогон прерван.
# Обратно: papa-update insta-install. Ничего не удаляет.
set -uo pipefail
systemctl disable --now papa-insta.timer 2>&1 | tail -2
systemctl stop papa-razvedka@insta.service 2>/dev/null || true
echo "таймер: $(systemctl is-enabled papa-insta.timer 2>/dev/null) / $(systemctl is-active papa-insta.timer 2>/dev/null)"
echo "прогон: $(systemctl is-active papa-razvedka@insta.service 2>/dev/null)"
echo "== INSTA_STOP_DONE"
