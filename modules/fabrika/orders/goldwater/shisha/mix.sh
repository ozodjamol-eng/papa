#!/usr/bin/env bash
# Сведение: голос −16 LUFS, музыка ~−29 LUFS + приглушение под голосом, общий −14 LUFS; склейка частей + концовка OZOD JAMOL (чёрная).
set -euo pipefail
cd /home/claude/gw
END=/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4
ffmpeg -y -v error -i voice.wav -af "loudnorm=I=-16:TP=-2:LRA=11,aresample=48000" -ac 2 vo_n.wav
ffmpeg -y -v error -i music.wav -af "volume=-8.5dB" mu_n.wav
ffmpeg -y -v error -i mu_n.wav -i vo_n.wav -filter_complex \
 "[1:a]asplit=2[sc][vv];[0:a][sc]sidechaincompress=threshold=0.02:ratio=5:attack=25:release=400:makeup=1[md];[md][vv]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]" \
 -map "[a]" -t 29.9 film_audio.wav
# (видео уже склеено в film_v.mp4)

ffmpeg -y -v error -i film_v.mp4 -i film_audio.wav -i "$END" -filter_complex \
 "[0:v]fps=30,format=yuv420p,setsar=1[v0];[2:v]fps=30,format=yuv420p,setsar=1[v1];[1:a]aresample=48000,aformat=channel_layouts=stereo[a0];[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]" \
 -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart GOLD_WATER_SHISHA.mp4
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate -of compact GOLD_WATER_SHISHA.mp4
