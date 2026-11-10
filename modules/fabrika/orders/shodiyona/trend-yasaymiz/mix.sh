#!/usr/bin/env bash
# mix.sh vid.mp4 out.mp4 — голос p1..p6 по V из timing.json + музыка (dayjest music_tong, −12 дБ под голосом) → −14 LUFS; + концовка OZOD JAMOL белая
set -euo pipefail
V=$1; O=$2; D=$(cd "$(dirname "$0")" && pwd); M=$D/../../../motion/dayjest/assets/music_tong.mp3; E=$D/../../../../../docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_BELAYA.mp4
read -r d1 d2 d3 d4 d5 d6 < <(python3 -c "import json;v=json.load(open('$D/timing.json'))['V'];print(*[int(v[p]*1000) for p in ['p1','p2','p3','p4','p5','p6']])")
T=$(mktemp -d)
ffmpeg -loglevel error -y -i "$V" -stream_loop 1 -i "$M" -i $D/voice/p1.mp3 -i $D/voice/p2.mp3 -i $D/voice/p3.mp3 -i $D/voice/p4.mp3 -i $D/voice/p5.mp3 -i $D/voice/p6.mp3 -filter_complex \
"[2]adelay=$d1|$d1[a1];[3]adelay=$d2|$d2[a2];[4]adelay=$d3|$d3[a3];[5]adelay=$d4|$d4[a4];[6]adelay=$d5|$d5[a5];[7]adelay=$d6|$d6[a6];\
[a1][a2][a3][a4][a5][a6]amix=inputs=6:normalize=0,aformat=channel_layouts=stereo,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120[vo];[vo]asplit[vo1][vo2];\
[1]atrim=0:34,afade=t=in:d=0.8,afade=t=out:st=32.3:d=1.7,volume=0.32,aformat=channel_layouts=stereo[mu];[mu][vo2]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];\
[vo1][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5,aresample=48000[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 34 $T/main.mp4
ffmpeg -loglevel error -y -i $T/main.mp4 -i "$E" -f lavfi -t 2.3 -i anullsrc=r=48000:cl=stereo -filter_complex "[0:v]fps=30,format=yuv420p[v0];[1:v]fps=30,format=yuv420p,scale=1080:1920[v1];[v0][0:a][v1][2:a]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k "$O"
rm -rf $T
