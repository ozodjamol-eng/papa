#!/usr/bin/env bash
# Поиск «мёртвых» кусков: кадр не меняется дольше порога (по умолчанию 1 с; короткие паузы для чтения — норма).
# Использование: dead_frames.sh video.mp4 [порог_сек]
# Работает за секунды (ffmpeg freezedetect), ничего не рендерит заново.
set -euo pipefail
v="$1"; d="${2:-1.0}"
ffmpeg -hide_banner -nostats -i "$v" -vf "freezedetect=n=-55dB:d=$d" -map 0:v -f null - 2>&1 \
 | awk '/freeze_start/{s=$NF} /freeze_end/{printf "МЁРТВО: %6.2f – %6.2f с\n", s, $NF; n++} END{if(!n) print "Мёртвых кусков нет ✅"}'
