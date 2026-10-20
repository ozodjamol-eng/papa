#!/usr/bin/env bash
# 🎬 Проверка ролика погоды (только чтение): Франкфурт скачивает сегодняшний MP4 из ветки motion так же, как GENPLAN в 07:00.
set -Eeuo pipefail
D=$(TZ=Asia/Tashkent date +%F); T=$(mktemp); trap 'rm -f "$T"' EXIT
U="https://raw.githubusercontent.com/ozodjamol-eng/papa/motion/xojaobod-weather-$D.mp4"
if curl -sS -L --fail --max-time 60 -o "$T" "$U"; then
  echo "ролик $D: $(stat -c %s "$T") байт, сигнатура: $(head -c 8 "$T" | tail -c 4)"
else echo "❌ ролика $D нет: $U"; fi
cd /opt/papa/modules/genplan && /opt/papa-venv/razvedka/bin/python -c "import telethon; print('telethon', telethon.__version__)"
grep -n 'video = true' config.toml | head -2
echo "== MOTION_CHECK_DONE"
