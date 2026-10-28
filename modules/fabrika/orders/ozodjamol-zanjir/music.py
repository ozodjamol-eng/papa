import numpy as np, wave
SR = 44100
BPM = 112
beat = 60 / BPM
DUR = 29.0
n = int(SR * DUR)
out = np.zeros((n, 2))
t_all = np.arange(n) / SR

def note(f, start, length, amp, kind="pluck", pan=0.0):
    s = int(start * SR); L = int(length * SR)
    if s >= n: return
    L = min(L, n - s)
    t = np.arange(L) / SR
    if kind == "pluck":
        w = (np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2*f*t) + 0.12*np.sin(2*np.pi*3*f*t))
        env = np.exp(-t * 5.5) * np.minimum(1, t / 0.004)
    elif kind == "pad":
        w = sum(np.sin(2*np.pi*f*d*t) for d in (1, 1.004, 0.996)) / 3
        env = np.minimum(1, t / 0.25) * np.minimum(1, (length - t) / 0.3).clip(0)
    elif kind == "bass":
        w = np.sin(2*np.pi*f*t) + 0.2*np.sin(2*np.pi*2*f*t)
        env = np.exp(-t * 3.0) * np.minimum(1, t / 0.006)
    sig = w * env * amp
    out[s:s+L, 0] += sig * (1 - pan) ; out[s:s+L, 1] += sig * (1 + pan)

def kick(start, amp=0.8):
    s = int(start*SR); L = int(0.25*SR)
    if s >= n: return
    L = min(L, n-s); t = np.arange(L)/SR
    f = 50 + 90*np.exp(-t*30)
    sig = np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t*14) * amp
    out[s:s+L] += sig[:, None]

rng = np.random.default_rng(1)
def hat(start, amp=0.08, pan=0.3):
    s = int(start*SR); L = int(0.05*SR)
    if s >= n: return
    L = min(L, n-s); t = np.arange(L)/SR
    nz = rng.standard_normal(L); nz = np.diff(np.concatenate([[0], nz]))
    sig = nz * np.exp(-t*80) * amp
    out[s:s+L, 0] += sig*(1-pan); out[s:s+L, 1] += sig*(1+pan)

def clap(start, amp=0.18):
    s = int(start*SR); L = int(0.15*SR)
    if s >= n: return
    L = min(L, n-s); t = np.arange(L)/SR
    sig = rng.standard_normal(L) * np.exp(-t*25) * amp
    out[s:s+L] += sig[:, None]

def hz(m): return 440 * 2 ** ((m - 69) / 12)
# C - G - Am - F
prog = [(60, [60, 64, 67]), (55, [59, 62, 67]), (57, [57, 60, 64]), (53, [57, 60, 65])]
bar = 4 * beat
nbars = int(DUR / bar) + 1
for b in range(nbars):
    root, ch = prog[b % 4]
    t0 = b * bar
    note(hz(root - 24), t0, bar, 0.0)  # placeholder
    for k in range(8):  # bass on 8ths pattern
        if k in (0, 3, 4, 6):
            note(hz(root - 24), t0 + k*beat/2, beat/2, 0.32, "bass")
    for m in ch:
        note(hz(m), t0, bar, 0.05, "pad", pan=0.1)
    # pluck arpeggio 16ths-ish
    arp = ch + [ch[0] + 12, ch[1] + 12]
    for k in range(8):
        note(hz(arp[k % len(arp)] + 12), t0 + k*beat/2, beat, 0.07, "pluck", pan=(-0.4 if k % 2 else 0.4))
    for k in range(4):
        kick(t0 + k*beat, 0.55)
        if k in (1, 3): clap(t0 + k*beat)
    for k in range(8):
        hat(t0 + k*beat/2 + beat/4, 0.06)

# fade in/out
fi = np.minimum(1, t_all / 0.4); fo = np.clip((DUR - t_all) / 1.5, 0, 1)
out *= (fi * fo)[:, None]
out /= np.abs(out).max() * 1.05
with wave.open("/home/claude/zanjir/music.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype("<i2").tobytes())
print("ok")
