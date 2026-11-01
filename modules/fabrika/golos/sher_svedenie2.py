# Сведение стиха v2 (01.11, урок «обрывается»): граница строки = разметка ElevenLabs (*.align.json),
# но разрез ставится в САМУЮ ТИХУЮ точку в окне ±0,35 с — слова не режутся. Без замедления.
# Запуск: python3 sher_svedenie2.py <префикс> <число_куплетов> <музыка.wav (уже −27 LUFS)> <итог.mp3>
import json, subprocess, sys
import numpy as np
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
pre, n, mus, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
LINE, ST, LEAD = 0.45, 1.1, 1.5
def pcm(f):
    return np.frombuffer(sh(f"ffmpeg -v error -i {f} -ac 1 -ar 16000 -f s16le -").stdout if False else
        subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout, np.int16).astype(np.float32)
def quiet(x, t, w=0.35):
    a, b = int(max(0, t - w) * 16000), int(min(len(x) / 16000, t + w) * 16000)
    win = 320  # 20 мс
    seg = x[a:b]; e = np.array([np.sqrt(np.mean(seg[i:i+win]**2)+1e-9) for i in range(0, max(1,len(seg)-win), 80)])
    return (a + int(np.argmin(e)) * 80 + win // 2) / 16000
for g, d in (("gl", LINE), ("gs", ST), ("g0", LEAD)):
    sh(f"ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t {d} {g}.wav")
parts = ["g0.wav"]
for k in range(1, n + 1):
    f = f"{pre}{k}"; a = json.load(open(f + ".align.json")); ch, s, e = a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]
    x = pcm(f + ".mp3"); D = len(x) / 16000
    cuts = []
    for i, c in enumerate(ch):
        if c == "\n":
            j = i - 1
            while not ch[j].strip(): j -= 1
            m = i + 1
            while not ch[m].strip(): m += 1
            cuts.append(quiet(x, (e[j] + s[m]) / 2))
    # начало: после тега [..] — первая тихая точка перед первым словом; конец — до конца файла
    pts = [0.0] + cuts + [D]
    sh(f"ffmpeg -v error -y -i {f}.mp3 -ar 44100 -ac 2 {f}w.wav")
    for q, (p0, p1) in enumerate(zip(pts, pts[1:])):
        sh(f"ffmpeg -v error -y -i {f}w.wav -ss {p0} -to {p1} -af 'silenceremove=start_periods=1:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_threshold=-48dB,areverse,afade=t=in:d=0.01' {f}_{q}.wav")
        parts += [f"{f}_{q}.wav", "gl.wav" if q < len(pts) - 2 else "gs.wav"]
open("l.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
sh("ffmpeg -v error -y -f concat -safe 0 -i l.txt -c:a pcm_s16le vd.wav")
ROOM = "asplit[d][w];[w]aecho=0.8:0.7:23|41|67|113|190|310:0.55|0.45|0.38|0.30|0.22|0.15,lowpass=f=5500,highpass=f=180,volume=0.11[r];[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7"
sh(f"ffmpeg -v error -y -i vd.wav -filter_complex '[0:a]{ROOM}' -ar 44100 v.wav")
D = float(sh("ffprobe -v error -show_entries format=duration -of csv=p=0 v.wav").stdout); L = D + 4.5
r = sh(f"ffmpeg -v error -y -i {mus} -i v.wav -filter_complex \"[0:a]atrim=0:{L},afade=t=out:st={D+0.5}:d=4[m];[m][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89,loudnorm=I=-16:TP=-1.5[o]\" -map \"[o]\" -c:a libmp3lame -b:a 320k {out}")
print(out, "голос", round(D, 1), "с", r.stderr)
