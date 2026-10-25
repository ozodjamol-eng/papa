V=$1; case $V in 1) I=50;; 2) I=52;; 3) I=56;; esac
D=$(python3 -c "print(int(($I/30+0.3)*1000))")
ffmpeg -y -loglevel error -framerate 30 -i C$V/c%03d.png -i s$V.wav -i /home/claude/ad/vo_bas.mp3 -filter_complex "[2:a]atrim=8.22:9.44,asetpts=PTS-STARTPTS,highpass=f=60,equalizer=f=3000:t=q:w=1:g=2,volume=1.6,adelay=${D}|${D}[vo];[1:a]volume=0.8[sx];[sx][vo]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1:LRA=9,alimiter=limit=0.95[a]" -map 0:v -map "[a]" -c:v libx264 -crf 15 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart OZOD_JAMOL_KONCOVKA_3D_$V.mp4
