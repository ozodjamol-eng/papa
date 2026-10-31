#!/usr/bin/env bash
# 31.10 владелец: «мы же планировали это для дизайна». $5 OpenRouter — ТОЛЬКО на 3D-дизайн (dizayn-img берёт ключ сам).
# Агенты каналов — снова только бесплатный Google, как до 13:30. Прокси выключен. Ключ остаётся на сервере (для дизайна).
set -euo pipefail
rm -f /etc/papa-gemini-proxy/on
systemctl disable -q --now papa-gemini-proxy 2>/dev/null || true
echo "агенты каналов: только бесплатный Google · прокси: $(systemctl is-active papa-gemini-proxy || true)"
echo "ключ OpenRouter для дизайна: $([[ -s /etc/papa-gemini-proxy/env ]] && echo есть || echo НЕТ)"
echo "== GEMINI_PROXY_OFF_DONE"
