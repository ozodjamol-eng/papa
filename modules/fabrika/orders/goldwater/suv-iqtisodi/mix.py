import subprocess, sys
K = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
M = "/mnt/user-data/uploads/Downloads/aurec-smooth-soul-613829.mp3"
DUR = {1: 5.8, 2: 8.5, 3: 7.4}; MS = {1: 0, 2: 30, 3: 60}
for k, D in DUR.items():
    ms = int(0.4 * 1000)
    flt = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad=whole_dur={D},atrim=0:{D},aecho=0.8:0.5:40:0.12,asplit=2[vo][sc];"
           f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{D},afade=t=in:d=0.3,afade=t=out:st={D-1.0}:d=1.0,volume=0.10[mu];"
           "[mu][sc]sidechaincompress=threshold=0.03:ratio=3:attack=20:release=400[du];"
           "[vo][du]amix=inputs=2:normalize=0[m];"
           "[2:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.6[ko];"
           "[m][ko]concat=n=2:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f"vo/S{k}.mp3", "-ss", str(MS[k]), "-i", M, "-i", K,
                    "-filter_complex", flt, "-map", "[a]", "-ar", "48000", f"a{k}.wav"], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f"v{k}.mp4", "-i", f"a{k}.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", f"GW_Suv_iqtisodi_{k}.mp4"], check=True)
