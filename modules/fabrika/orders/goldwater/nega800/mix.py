import json, subprocess
tl = json.load(open("timeline.json")); T = tl["total"]; K = tl["kon"]
inp = ["-ss", "20", "-i", "/mnt/user-data/uploads/Downloads/aurec-sunset-house-598438.mp3"]; fl = []
for i, (n, at) in enumerate(tl["vo"]):
    inp += ["-i", f"vo/{n}.mp3"]; ms = int(at * 1000)
    fl.append(f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms},apad=whole_dur={T:.3f}[v{i}]")
k = len(tl["vo"]) + 1
inp += ["-i", "/home/claude/tz/seg/../../papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"]
fl.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(K*1000)}|{int(K*1000)},apad=whole_dur={T:.3f}[ko]")
vs = "".join(f"[v{i}]" for i in range(len(tl["vo"])))
fl.append(f"{vs}amix=inputs={len(tl['vo'])}:normalize=0,aecho=0.8:0.5:40:0.12,asplit=2[vo][sc]")
fl.append(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{K:.3f},afade=t=in:d=0.5,afade=t=out:st={K-1.6:.3f}:d=1.6,volume=0.11,apad=whole_dur={T:.3f}[m0]")
fl.append("[m0][sc]sidechaincompress=threshold=0.03:ratio=3:attack=20:release=400[md]")
fl.append("[vo][md][ko]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
subprocess.run(["ffmpeg","-nostdin","-v","error","-y",*inp,"-filter_complex",";".join(fl),"-map","[a]","-ar","48000","-t",f"{T:.3f}","mix.wav"], check=True)
