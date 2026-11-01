# Сведение стиха v3 (01.11): каждая строка — отдельный tts (с previous_text/next_text), НИКАКИХ разрезов внутри.
# Файлы <голос>_<куплет>_<строка>.mp3; тишину по краям строки срезаем мягко (−50 дБ), паузы: строка 0,5 с, куплет 1,2 с.
# Запуск: python3 sher_po_strokam.py <голос> <музыка.wav −27 LUFS> <итог.mp3>
import glob, re, subprocess, sys
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)
v, mus, out = sys.argv[1:4]
LINE, ST, LEAD = 0.5, 1.2, 1.5
for g, d in (("gl", LINE), ("gs", ST), ("g0", LEAD)):
    sh(f"ffmpeg -v error -y -f lavfi -i anullsrc=r=44100:cl=stereo -t {d} {g}.wav")
fs = sorted(glob.glob(f"{v}_*_*.mp3"), key=lambda f: tuple(int(x) for x in re.findall(r"_(\d+)", f)))
parts = ["g0.wav"]
for i, f in enumerate(fs):
    w = f[:-4] + "c.wav"
    sh(f"ffmpeg -v error -y -i {f} -af 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.12,areverse,aresample=44100' -ac 2 {w}")
    parts.append(w)
    if i < len(fs) - 1:
        same = re.findall(r"_(\d+)_", f)[0] == re.findall(r"_(\d+)_", fs[i + 1])[0]
        parts.append("gl.wav" if same else "gs.wav")
open(f"l_{v}.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
sh(f"ffmpeg -v error -y -f concat -safe 0 -i l_{v}.txt -c:a pcm_s16le vd_{v}.wav")
ROOM = "asplit[d][w];[w]aecho=0.8:0.7:23|41|67|113|190|310:0.55|0.45|0.38|0.30|0.22|0.15,lowpass=f=5500,highpass=f=180,volume=0.11[r];[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=7"
sh(f"ffmpeg -v error -y -i vd_{v}.wav -filter_complex '[0:a]{ROOM}' -ar 44100 v_{v}.wav")
D = float(sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 v_{v}.wav").stdout); L = D + 4.5
r = sh(f"ffmpeg -v error -y -i {mus} -i v_{v}.wav -filter_complex \"[0:a]atrim=0:{L},afade=t=out:st={D+0.5}:d=4[m];[m][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89,loudnorm=I=-16:TP=-1.5[o]\" -map \"[o]\" -c:a libmp3lame -b:a 320k {out}")
print(out, len(fs), "строк, голос", round(D, 1), "с", r.stderr)
