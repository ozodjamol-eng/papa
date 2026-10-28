import numpy as np, subprocess, json
SR = 44100
tl = json.load(open("/home/claude/viv/timeline.json"))
TOTAL = tl["TOTAL"]
N = int(SR * TOTAL)
def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
def put(buf, a, t, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(a))
    if s < len(buf): buf[s:e] += a[:e - s] * g

voice = np.zeros((N, 2)); sfx = np.zeros((N, 2))
for z, t in tl["V"].items():
    put(voice, load(f"/home/claude/viv/voice/{z}.wav"), t, 1.0)
S = "/home/claude/zanjir/src/"
wh = load(S + "soundreality-whoosh-transition-6-220294.mp3")
pop = load(S + "soundreality-ui-pop-up-clear-391155.mp3")
err = load(S + "soundreality-notification-error-427345.mp3")
ding = load(S + "soundreality-ding-sound-effect-613874.mp3")
for name, s0, s1 in tl["SC"][1:]:
    put(sfx, wh, s0 - 0.12, 0.35)
for t in tl["role_t"]:
    put(sfx, pop, t, 0.30)
put(sfx, err, tl["brk"], 0.45)
put(sfx, pop, tl["V"]["Z05"], 0.3); put(sfx, pop, tl["V"]["Z05"] + 3.78, 0.25); put(sfx, pop, tl["V"]["Z05"] + 4.7, 0.25)
put(sfx, ding, tl["tg"], 0.4)

pr = load("/home/claude/viv/presto.wav")
OFF = 1.30; BLEN = 5.0; BSRC = 170.6; XF = 0.6
A = pr[int(OFF * SR):int(OFF * SR) + N].copy()
A = np.pad(A, ((0, max(0, N - len(A))), (0, 0)))[:N]
B = pr[int(BSRC * SR):int((BSRC + BLEN) * SR)].copy()
bs = N - len(B)
ramp = np.linspace(1, 0, int(XF * SR))
A[bs:bs + len(ramp)] *= ramp[:, None]; A[bs + len(ramp):] = 0
B[:len(ramp)] *= ramp[::-1][:, None]
mus = A; mus[bs:bs + len(B)] += B
mus *= 1.6
# ducking by voice envelope
env = np.abs(voice).max(1)
win = int(0.15 * SR)
env = np.convolve(env, np.ones(win) / win, "same")
duck = np.where(env > 0.01, 0.32, 0.85)
duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), "same")
mix = voice * 1.0 + sfx + mus[:, :] * duck[:, None] * 0.55
mix /= max(1.0, np.abs(mix).max() / 0.98)
mix.astype("<f4").tofile("/home/claude/viv/mix.f32")
print("ok", np.abs(mix).max())
