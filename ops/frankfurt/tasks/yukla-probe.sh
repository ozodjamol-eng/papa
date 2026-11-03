#!/usr/bin/env bash
# Только чтение: проходят ли ссылки с Франкфурта БЕЗ прокси (решение о покупке прокси $5). Ничего не скачивает целиком.
set -uo pipefail
Y=/opt/papa-venv/yukla/bin/yt-dlp
[[ -x $Y ]] || { echo "нет yt-dlp — сначала yukla-bot-token"; exit 1; }
probe() { if timeout 60 $Y --no-warnings -q --skip-download --print "%(extractor)s %(duration)s сек" "$2" >/tmp/yp.out 2>/tmp/yp.err; then
    echo "✅ $1: $(cat /tmp/yp.out)"; else echo "❌ $1: $(tail -1 /tmp/yp.err | cut -c1-160)"; fi; }
probe "YouTube"        "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
probe "TikTok"         "https://www.tiktok.com/@scout2015/video/6718335390845095173"
probe "Instagram reel" "https://www.instagram.com/reel/DfPdNZNN75p/"
echo "== YUKLA_PROBE_DONE"
