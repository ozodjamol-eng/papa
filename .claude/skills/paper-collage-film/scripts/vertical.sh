#!/usr/bin/env bash
# 9:16 из готового 16:9: рамка comp/vertical_frame.html (название сверху, @юзер и призыв снизу, рваное окно) + ролик во всю ширину.
# usage: tools/vertical.sh <in_16x9.mp4> [out_9x16.mp4]      (правьте слова в VCFG внутри comp/vertical_frame.html)
set -e
P="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"; IN="$1"; OUT="${2:-${IN%.mp4}_9x16.mp4}"
[ -f "$P/comp/vertical_frame.html" ] || cp "$(dirname "$(readlink -f "$0")")/../assets/template/comp/vertical_frame.html" "$P/comp/" 2>/dev/null || true
node "$P/tools/code_cutouts.mjs" "$P" --page vertical_frame.html --out review/vframe vframe >/dev/null
FR="$P/review/vframe/vframe.png"
ffmpeg -v error -y -i "$IN" -loop 1 -i "$FR" -filter_complex "color=c=#FBF8F1:s=1080x1920:r=24[bg];[0:v]scale=1080:608:flags=lanczos,setsar=1[v];[bg][v]overlay=0:656:shortest=1[b];[b][1:v]overlay=0:0:shortest=1,format=yuv420p[o]" -map "[o]" -map 0:a? -c:v libx264 -preset slow -b:v 16M -maxrate 24M -bufsize 24M -c:a copy -movflags +faststart "$OUT"
echo "$OUT"
