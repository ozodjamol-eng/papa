#!/usr/bin/env bash
# Свести голос + подложку + видео: mix.sh video_noaudio.mp4 bed.wav voice_dir out.mp4  (голос по V из demo.js, подложка −12 дБ под голосом, итог −14 LUFS / −1.5 dBTP)
set -euo pipefail
V=$1; B=$2; D=$3; O=$4
ffmpeg -loglevel error -y -i "$V" -i "$B" -i "$D/nomi1.mp3" -i "$D/nomi2.mp3" -i "$D/nomi3.mp3" -i "$D/nomi4.mp3" -filter_complex \
"[2]adelay=300|300[a1];[3]adelay=8700|8700[a2];[4]adelay=13900|13900[a3];[5]adelay=18800|18800[a4];\
[a1][a2][a3][a4]amix=inputs=4:normalize=0,aformat=channel_layouts=mono,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120[vo];\
[vo]asplit[vo1][vo2];[1]aformat=channel_layouts=mono[bd];[bd][vo2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[bdd];\
[vo1][bdd]amix=inputs=2:weights=1 0.7:normalize=0,loudnorm=I=-14:TP=-1.5,aresample=48000[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 30 "$O"
