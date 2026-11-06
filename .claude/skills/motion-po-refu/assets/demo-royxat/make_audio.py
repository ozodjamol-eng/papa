#!/usr/bin/env python3
"""Звук демо «Янги уй рўйхати» (13 с): тёплый пэд + «тик» на каждую галочку (выше тоном с каждой) + удар на бейдже + щелчки набора телефона.
usage: make_audio.py out.wav  → потом ffmpeg … -af loudnorm=I=-16:TP=-1.5"""
import sys, wave, numpy as np
sr = 48000; d = 13.0; n = int(sr * d); t = np.arange(n) / sr; out = np.zeros(n)
for f, a in [(220, .10), (261.6, .07), (329.6, .06), (110, .08)]: out += a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
out *= np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 1.5, 0, 1)
def tick(t0, f=1320, a=.45, dec=18):
    i = int(t0 * sr); m = int(.25 * sr); tt = np.arange(m) / sr; s = a * np.exp(-tt * dec) * (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.5 * tt))
    out[i:i + m] += s[:max(0, min(m, n - i))]
for k in range(6): tick(0.7 + 0.45 + 0.35 * 0 + k * 0.85, 990 + k * 110)   # = T0 + lag + k*EV (как в demo.js)
tick(6.5, 660, .6, 8); tick(6.52, 990, .4, 8)
for k in range(17): tick(10.5 + k * 0.05, 1800, .08, 60)
out = out / np.max(np.abs(out)) * 0.8
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
