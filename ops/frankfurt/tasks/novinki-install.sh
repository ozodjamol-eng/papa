#!/usr/bin/env bash
# 🤖 Наши инструменты (06.11 владелец: «Антропик выходит то, это… я должен быть в курсе; мы теперь часть их»):
# каждый день 13:40 Ташкент — новинки Anthropic/Claude (первым), Google Flow/Veo/Gemini, ElevenLabs, Higgsfield, Seedance…
# Бесплатный Gemini с поиском Google; если лимит — запасной OpenRouter с веб-поиском (≈ $0,02–0,03 за заход, выбор владельца «путь Б»).
# Нет новинок — сообщения нет. Первый выпуск — сразу. Откат: systemctl disable --now papa-novinki.timer
set -Eeuo pipefail
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-novinki.service /opt/papa/ops/frankfurt/systemd/papa-novinki.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-novinki.timer
echo "таймер: $(systemctl list-timers papa-novinki.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "ключ OpenRouter (запасной): $([ -f /etc/papa-gemini-proxy/env ] && echo есть || echo НЕТ)"
echo "первый выпуск сейчас (1–3 минуты):"
systemctl start papa-novinki.service || true
journalctl -u papa-novinki.service -n 40 -o cat --no-pager | tail -30
echo "== NOVINKI_INSTALL_DONE"
