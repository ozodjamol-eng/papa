# Стих «как человек» (01.11, владелец: «вздохи, выдохи — по музыке, по ритму сам определяй»).
# 1) темп строки по роли: n рассказ 0.96 · q вопрос 0.93 · a ответ 0.89 · f финал 0.86 (atempo, тембр не меняется);
# 2) пауза по смыслу: после рассказа короткая (0.35), после вопроса — «ждём ответа» (0.9), внутри ответа 0.6, между куплетами 1.4;
# 3) укладка: старт строки = ближайшая сильная доля музыки (onset) в окне [мин.пауза … мин.пауза+0.8 с] — вдох совпадает с вдохом музыки;
#    перед финальным куплетом — самый сильный onset в окне до +2.5 с (пауза-«вздох» перед кульминацией).
# Запуск: python3 sher_dyhanie.py <roles.json> <префикс> <музыка.mp3> <итог.mp3> [старт_с]
import json, subprocess, sys
import numpy as np, librosa, soundfile as sf
roles, pre, mus, out = sys.argv[1:5]; START = float(sys.argv[5]) if len(sys.argv) > 5 else 3.0
SR = 44100; TEMPO = {"n": 0.96, "q": 0.93, "a": 0.89, "f": 0.86}
AFTER = {"n": 0.35, "q": 0.9, "a": 0.6, "f": 0.8}
def load(f):
    x, _ = librosa.load(f, sr=SR, mono=False)
    return np.vstack([x, x]) if x.ndim == 1 else x
m = load(mus); mono = librosa.to_mono(m)
env = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=512); et = librosa.times_like(env, sr=SR, hop_length=512)
def best(t0, w):
    i0, i1 = np.searchsorted(et, t0), np.searchsorted(et, t0 + w)
    return float(et[i0 + int(np.argmax(env[i0:i1]))]) if i1 > i0 else t0
L = json.load(open(roles)); N = int(m.shape[1]) ; v = np.zeros((2, N), np.float32)
t = START; log = []
for i, (b, l, r, tg, txt) in enumerate(L):
    f = f"{pre}_{b}_{l}"
    subprocess.run(f"ffmpeg -v error -y -i {f}.mp3 -af 'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,"
                   f"areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.15,areverse,atempo={TEMPO[r]},aresample={SR}' -ac 2 {f}_h.wav", shell=True)
    x = load(f + "_h.wav")
    if i > 0:
        pb, pr = L[i - 1][0], L[i - 1][2]
        gap = 1.4 if b != pb else AFTER[pr]
        w = 2.5 if (b != pb and r == "f") else 0.8
        t = best(t_end + gap, w)
    a = int(t * SR); v[:, a:a + x.shape[1]] += x[:, :max(0, N - a)]
    t_end = t + x.shape[1] / SR; log.append(round(t, 1))
sf.write("vg.wav", v.T, SR)
HALL = ("asplit[d][w];[w]aecho=0.8:0.85:29|47|71|109|163|241|353|509|719|997:"
        "0.50|0.44|0.40|0.35|0.30|0.25|0.20|0.15|0.10|0.06,lowpass=f=4800,highpass=f=200,volume=0.18[r];"
        "[d][r]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11")
subprocess.run(f"ffmpeg -v error -y -i vg.wav -filter_complex '[0:a]{HALL}' -ar {SR} vh.wav", shell=True)
vh = load("vh.wav"); n = min(vh.shape[1], N); vh, mm = vh[:, :n], m[:, :n]
rms = lambda y: 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)
act = np.abs(librosa.to_mono(vh)) > 10 ** (-40 / 20); vdb = rms(vh[:, act])
win = SR * 5; peak = max(rms(mm[:, k:k + win]) for k in range(0, n - win, SR))
g = 10 ** ((vdb - 8 - peak) / 20); mix = vh + mm * g; mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
sf.write("mix.wav", mix.T, SR); subprocess.run(f"ffmpeg -v error -y -i mix.wav -c:a libmp3lame -b:a 320k {out}", shell=True)
print(out, "старты строк:", log, f"конец голоса {t_end:.1f} из {n/SR:.0f} с")
