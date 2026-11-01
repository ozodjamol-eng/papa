# Стих ФРАЗАМИ (01.11, эталон — образец владельца «Kecha bola edim…»): строка = одна музыкальная фраза.
# Слот строки = наименьшее число долей (кратно 2), куда влезает речь + вдох 1,2 с; строка стартует на начале слота.
# В конце куплета — ещё 2 доли («выдох»). Голос — зал; скрипки на 8 дБ ниже голоса на кульминации.
# Запуск: python3 sher_frazami.py <roles.json> <префикс> <музыка.mp3> <итог.mp3> [старт_с] [atempo]
import json, subprocess, sys
import numpy as np, librosa, soundfile as sf
roles, pre, mus, out = sys.argv[1:5]; START = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
AT = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0; SR = 44100; BREATH = 1.0
def load(f):
    x, _ = librosa.load(f, sr=SR, mono=False)
    return np.vstack([x, x]) if x.ndim == 1 else x
m = load(mus); mono = librosa.to_mono(m)
tempo, beats = librosa.beat.beat_track(y=mono, sr=SR)
bpm = float(np.atleast_1d(tempo)[0]); bpm = bpm / 2 if bpm > 100 else bpm      # медленная музыка: считаем по крупной доле
bt = 60 / bpm; bts = librosa.frames_to_time(beats, sr=SR); ph = float(bts[len(bts) // 2]) % bt
L = json.load(open(roles)); N = m.shape[1]; VN = N + 90 * SR; v = np.zeros((2, VN), np.float32)
t = ph + np.ceil((START - ph) / bt) * bt; log = []
for i, (b, l, r, tg, txt) in enumerate(L):
    f = f"{pre}_{b}_{l}"
    subprocess.run(f"ffmpeg -v error -y -i {f}.mp3 -af 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,"
                   f"areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.2,areverse,atempo={AT},aresample={SR}' -ac 2 {f}_p.wav", shell=True)
    x = load(f + "_p.wav"); d = x.shape[1] / SR
    a = int(t * SR); v[:, a:a + x.shape[1]] += x
    slot = bt * np.ceil((d + BREATH) / bt)
    last_in_stanza = i == len(L) - 1 or L[i + 1][0] != b
    log.append((round(t, 1), round(d, 1), round(slot, 1)))
    t += slot + (bt if last_in_stanza else 0)
end = log[-1][0] + log[-1][1]
need = int((end + 6) * SR)
if need > m.shape[1]:
    ext = need - m.shape[1] + int(2 * SR); a0 = int(m.shape[1] * 0.45); seg = m[:, a0:a0 + ext + int(2 * SR)]
    cf = int(2 * SR); w = np.linspace(0, 1, cf)
    cut = int(m.shape[1] * 0.70)                          # вставка до ухода в тихий финал
    head, tail = m[:, :cut], m[:, cut:]
    x1 = np.concatenate([head[:, :-cf], head[:, -cf:] * (1 - w) + seg[:, :cf] * w, seg[:, cf:-cf]], axis=1)
    mid_end = seg[:, -cf:]
    m = np.concatenate([x1, mid_end * (1 - w) + tail[:, :cf] * w, tail[:, cf:]], axis=1)
    N = m.shape[1]; print(f"музыка продлена до {N/SR:.0f} с")
sf.write("vg.wav", v.T, SR)
HALL = ("asplit[d][w];[w]aecho=0.8:0.85:29|47|71|109|163|241|353|509|719|997:"
        "0.50|0.44|0.40|0.35|0.30|0.25|0.20|0.15|0.10|0.06,lowpass=f=4800,highpass=f=200,volume=0.16[r];"
        "[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11")
subprocess.run(f"ffmpeg -v error -y -i vg.wav -filter_complex '[0:a]{HALL}' -ar {SR} vh.wav", shell=True)
vh = load("vh.wav"); n = min(vh.shape[1], N, int((end + 6) * SR)); vh, mm = vh[:, :n], m[:, :n].copy()
fade = int(4 * SR); mm[:, -fade:] *= np.linspace(1, 0, fade)
rms = lambda y: 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)
act = np.abs(librosa.to_mono(vh)) > 10 ** (-40 / 20); vdb = rms(vh[:, act])
win = SR * 5; peak = max(rms(mm[:, k:k + win]) for k in range(0, n - win, SR))
g = 10 ** ((vdb - 8 - peak) / 20); mix = vh + mm * g; mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
sf.write("mix.wav", mix.T, SR); subprocess.run(f"ffmpeg -v error -y -i mix.wav -c:a libmp3lame -b:a 320k {out}", shell=True)
print(out, f"доля {bt:.2f} с; голос до {end:.1f} с из музыки {N/SR:.0f} с; (старт, речь, слот):", log[:6], "…")
