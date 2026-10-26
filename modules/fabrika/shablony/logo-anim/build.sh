#!/usr/bin/env bash
# Склейка: ролик + музыка + SFX + концовка OZOD JAMOL. Звук строится ОТДЕЛЬНО с точной длиной (26.10: amix/loudnorm обрезали звук на ~3 с раньше концовки).
# build.sh <видео.mp4> <музыка> <sfx.wav> <длина_ролика_с> <концовка.mp4> <выход.mp4>
set -euo pipefail
v=$1; mus=$2; sfx=$3; dur=$4; outro=$5; out=$6; fo=$(python3 -c "print($dur-0.6)")
ffmpeg -v error -y -i "$mus" -i "$sfx" -filter_complex "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:$dur,asetpts=PTS-STARTPTS,loudnorm=I=-17:TP=-2:LRA=11,aresample=48000,apad,atrim=0:$dur,afade=t=out:st=$fo:d=0.6[m];[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=0:$dur[s];[m][s]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.9,atrim=0:$dur" -ar 48000 -ac 2 /tmp/a_main.wav
od=$(ffprobe -v error -select_streams v -show_entries stream=duration -of csv=p=0 "$outro")
ffmpeg -v error -y -i "$outro" -vn -af "aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:$od" -ar 48000 -ac 2 /tmp/a_out.wav
ffmpeg -v error -y -i /tmp/a_main.wav -i /tmp/a_out.wav -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1" -ar 48000 /tmp/a_full.wav
ffmpeg -v error -y -i "$v" -i "$outro" -filter_complex "[0:v]fps=30,format=yuv420p,setsar=1,trim=0:$dur,setpts=PTS-STARTPTS[v0];[1:v]fps=30,format=yuv420p,setsar=1[v1];[v0][v1]concat=n=2:v=1:a=0[v]" -map "[v]" -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p /tmp/v_full.mp4
ffmpeg -v error -y -i /tmp/v_full.mp4 -i /tmp/a_full.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k "$out"
# Проверка: длина звука = длине видео (±0,05 с), иначе ошибка
ffprobe -v error -show_entries stream=codec_type,duration -of csv=p=0 "$out" | python3 -c "import sys;d={l.split(',')[0]:float(l.split(',')[1]) for l in sys.stdin if ','in l};assert abs(d['video']-d['audio'])<0.05,d;print('OK',d)"
