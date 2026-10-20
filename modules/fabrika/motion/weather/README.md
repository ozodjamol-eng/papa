# Моушн «Об-ҳаво Хўжаобод» (скилл vizavi-motion, тест 20.10.2026)

Вертикаль 1080×1920, 60 fps, 15 с, H.264 + AAC. Всё кодом: Canvas + Playwright + FFmpeg, музыка и звуки синтезируются (numpy). Расход 0 $.
Данные — объект `WEATHER` в scene.html (город, дата, сейчас/день/ночь, осадки, завтра, username) — позже подставлять автоматически из прогноза.

Сборка:
    python3 audio.py
    node render.mjs $PWD/scene.html video 60 video_raw.mp4
    ffmpeg -i video_raw.mp4 -i audio.wav -c:v copy -c:a aac -b:a 192k -shortest out.mp4
