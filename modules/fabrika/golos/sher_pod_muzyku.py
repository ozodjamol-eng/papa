# Стих ПОД МУЗЫКУ (01.11): строки (уже готовые *s.wav: тенор, atempo 0.92) ставятся на сетку музыки —
# строка начинается на ближайшую полудолю после (конец пред. строки + 0,5 с), куплет — на ближайший удар после (+1,1 с).
# Голос — зал; музыка не «нормализуется в ноль»: её кульминация держится на 9 дБ ниже голоса, тихое начало остаётся тихим.
# Запуск: python3 sher_pod_muzyku.py <музыка.mp3> <итог.mp3> [начало_голоса_с]
import glob, re, subprocess, sys
import numpy as np, librosa, soundfile as sf
mus, out = sys.argv[1], sys.argv[2]; START = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
SR = 44100
def load(f):
    x, _ = librosa.load(f, sr=SR, mono=False)
    return np.atleast_2d(x) if x.ndim > 1 else np.vstack([x, x])
m = load(mus)
tempo, beats = librosa.beat.beat_track(y=librosa.to_mono(m), sr=SR, start_bpm=66)
bt = 60.0 / float(np.atleast_1d(tempo)[0]); bts = librosa.frames_to_time(beats, sr=SR)
t0 = float(bts[len(bts) // 2]) % bt          # фаза сетки по середине трека (там удары уверенные)
grid = lambda t, step: t0 + np.ceil((t - t0) / step) * step
fs = sorted(glob.glob("T_*_*s.wav"), key=lambda f: tuple(int(x) for x in re.findall(r"_(\d+)", f)))
L = int((librosa.get_duration(path=mus) + 1) * SR); v = np.zeros((2, L), np.float32)
t = grid(START, bt); prev = None; log = []
for f in fs:
    st = re.findall(r"_(\d+)_", f)[0]
    if prev is not None:
        t = grid(t_end + (0.5 if st == prev else 1.1), bt / 2 if st == prev else bt)
    x = load(f); a = int(t * SR); v[:, a:a + x.shape[1]] += x[:, :max(0, L - a)]
    t_end = t + x.shape[1] / SR; prev = st; log.append(round(t, 2))
sf.write("vg.wav", v.T, SR)
HALL = ("asplit[d][w];[w]aecho=0.8:0.85:29|47|71|109|163|241|353|509|719|997:"
        "0.50|0.44|0.40|0.35|0.30|0.25|0.20|0.15|0.10|0.06,lowpass=f=4800,highpass=f=200,volume=0.18[r];"
        "[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11")
subprocess.run(f"ffmpeg -v error -y -i vg.wav -filter_complex '[0:a]{HALL}' -ar {SR} vh.wav", shell=True)
vh = load("vh.wav"); n = min(vh.shape[1], m.shape[1]); vh, mm = vh[:, :n], m[:, :n]
rms = lambda y: 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)
act = np.abs(librosa.to_mono(vh)) > 10 ** (-40 / 20)
voice_db = rms(vh[:, act])
win = SR * 5; peak = max(rms(mm[:, i:i + win]) for i in range(0, n - win, SR))
g = 10 ** ((voice_db - 9 - peak) / 20); mix = vh + mm * g
mix = mix / max(1.0, np.max(np.abs(mix)) / 0.89)
sf.write("mix.wav", mix.T, SR)
subprocess.run(f"ffmpeg -v error -y -i mix.wav -c:a libmp3lame -b:a 320k {out}", shell=True)
print(out, f"темп {60/bt:.0f} уд/мин, строк {len(fs)}, голос {log[0]}→{t_end:.1f} с из {n/SR:.0f} с, музыка {20*np.log10(g):+.1f} дБ")
