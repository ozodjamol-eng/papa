#!/usr/bin/env python3
"""Звук ролика: музыка (Pixabay «Smooth Soul», −27 LUFS, петля с кроссфейдом) + голос (обработка бренда, −16) + свои SFX → −14 LUFS.
usage: make_audio.py <comp_dir> <music.mp3> <out.wav>   (comp_dir: timeline.js, voice.wav)"""
import json, re, subprocess, sys, wave, numpy as np
comp, mus, out = sys.argv[1:4]
tl = json.loads(re.sub(r'^window.TL = |;\s*$', '', open(f'{comp}/timeline.js').read())); L = tl['lines']; D = tl['dur']
st = lambda i: L[i]['t0']; en = lambda i: L[i]['t1']
T_FILL = st(2) - 0.1; EVERY = (en(2) - st(2) + 1.0) / 12
wipes = [st(3) - 0.65, st(4) - 0.6] + [st(5 + c) - 0.6 for c in range(5)] + [st(10) - 0.8]
sr = 48000; a = np.zeros(int(sr * D))
def pop(t0, f=700, d=0.1, g=0.25):
    i = int(t0 * sr); m = int(d * sr); tt = np.arange(m) / sr; s = g * np.sin(2 * np.pi * f * tt * (1 + 1.5 * np.exp(-tt * 40))) * np.exp(-tt * 30); a[i:i + m] += s[:len(a[i:i + m])]
def whoosh(t0, d=0.6, g=0.12):
    i = int(t0 * sr); m = int(d * sr); r = np.random.default_rng(int(t0 * 100)).standard_normal(m); r = np.convolve(r, np.ones(40) / 40, 'same'); env = np.sin(np.pi * np.arange(m) / m) ** 2; a[i:i + m] += (g * r * env * 5)[:len(a[i:i + m])]
whoosh(0.45, 0.7)
for i in range(12): pop(T_FILL + i * EVERY + 0.8, 480 + i * 30)
for w in wipes: whoosh(w, 0.6)
for c in range(6): pop(st(4 + c) - 0.25, 1100, 0.07, 0.12)
w = wave.open('sfx.wav', 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
sh = lambda *c: subprocess.run(['ffmpeg', '-v', 'error', '-y', *c], check=True)
sh('-i', mus, '-i', mus, '-filter_complex', f'[0:a][1:a]acrossfade=d=2[m];[m]atrim=0:{D},afade=t=in:d=1,afade=t=out:st={D-2.5}:d=2.5,loudnorm=I=-27:TP=-3[mm]', '-map', '[mm]', '-ar', '48000', '-ac', '2', 'music.wav')
sh('-i', f'{comp}/voice.wav', '-af', 'highpass=f=80,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=4000:t=q:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5', '-ar', '48000', '-ac', '2', 'voice_p.wav')
sh('-i', 'music.wav', '-i', 'voice_p.wav', '-i', 'sfx.wav', '-filter_complex', '[2:a]aresample=48000,volume=0.6[s];[0:a][1:a][s]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.9,loudnorm=I=-14:TP=-1[o]', '-map', '[o]', '-ar', '48000', '-ac', '2', out)
print('ok', D)
