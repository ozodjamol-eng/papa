#!/usr/bin/env python3
"""Звук демо «Номи — аслида» (30 с, под озвучку): тихий тёплый пэд + «вжик» зачёркивания + «тук» на роль + тики фишек + щелчки телефона.
Голос (voice/nomi1..4.mp3, асосий голос) подмешивает mix.sh: фразы с V=[0.3, 8.7, 13.9, 18.8] c, итог −14 LUFS.
usage: make_audio.py bed.wav"""
import sys, wave, numpy as np
sr = 48000; d = 30.0; n = int(sr * d); t = np.arange(n) / sr; out = np.zeros(n)
for f, a in [(196, .10), (246.9, .07), (293.7, .06), (98, .08)]: out += a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
out *= np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 1.5, 0, 1) * 0.45   # пэд тише — под голосом
rng = np.random.default_rng(7)
def add(t0, s):
    i = int(t0 * sr); m = min(len(s), n - i); out[i:i + m] += s[:m]
def tick(t0, f=1320, a=.45, dec=18):
    tt = np.arange(int(.25 * sr)) / sr; add(t0, a * np.exp(-tt * dec) * (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.5 * tt)))
def swish(t0, dur=.4, a=.35):
    m = int(dur * sr); tt = np.arange(m) / sr; env = np.sin(np.pi * tt / dur) ** 2; nz = rng.standard_normal(m); nz = np.convolve(nz, np.ones(6) / 6, 'same'); add(t0, a * env * nz)
SC = [(2.7, 3.74, [5.42, 6.58, 7.26]), (10.38, 11.45, [12.1, 12.45, 12.8]), (15.58, 16.72, [17.2, 17.55, 17.9])]   # = tStrike, tReal, tChips в demo.js
for ts, tr, tc in SC:
    swish(ts); tick(tr, 520, .55, 9); tick(tr + .02, 780, .3, 9)
    for k, c in enumerate(tc): tick(c, 1100 + k * 150, .22)
tick(18.3, 660, .5, 8); tick(18.8 + 4.3, 520, .45, 7)   # шторка, логотип
for k in range(17): tick(25.0 + k * 0.06, 1800, .06, 60)
out = out / np.max(np.abs(out)) * 0.5
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
