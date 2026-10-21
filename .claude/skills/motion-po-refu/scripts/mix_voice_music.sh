#!/usr/bin/env bash
# Голос сверху, музыка под голосом (автоприглушение), итог −14 LUFS / пик −1 dBTP — норма YouTube/Instagram/Telegram.
# usage: mix_voice_music.sh <video_with_voice.mp4|voice.wav> <music.mp3> <out.mp4|out.m4a> [music_db=-18] [music_start_s=0]
# Видео на входе → видео на выходе (картинка копируется). Нет голоса — дайте только музыку как <voice> и пустую строку как music.
set -e
IN="$1"; MUS="$2"; OUT="$3"; MDB="${4:--18}"; MS="${5:-0}"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
F="[0:a]aformat=channel_layouts=stereo,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120[v];[v]asplit=2[v1][vk];"
F+="[1:a]atrim=start=$MS,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,volume=${MDB}dB,afade=t=out:st=$(python3 -c "print(max(0,$DUR-1.5))"):d=1.5[m];"
F+="[m][vk]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md];[v1][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1:LRA=11[a]"
case "$OUT" in
  *.mp4|*.mov) ffmpeg -v error -y -i "$IN" -stream_loop -1 -i "$MUS" -filter_complex "$F" -map 0:v? -map "[a]" -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DUR" -movflags +faststart "$OUT" ;;
  *) ffmpeg -v error -y -i "$IN" -stream_loop -1 -i "$MUS" -filter_complex "$F" -map "[a]" -c:a aac -b:a 256k -ar 48000 -t "$DUR" "$OUT" ;;
esac
ffmpeg -hide_banner -i "$OUT" -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tr -s ' ' | sed 's/^/итог: /'
