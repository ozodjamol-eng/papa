#!/usr/bin/env python3
"""Звук демо «Гуруҳ кундалиги» (13 с): без музыки (тема святынь) — тихий воздух + мягкий колокольчик на каждой остановке маршрута + щелчок на финале.
usage: make_audio.py out.wav  → ffmpeg … -af loudnorm=I=-16:TP=-1.5"""
import sys, wave, numpy as np
sr = 48000; d = 13.0; n = int(sr * d); t = np.arange(n) / sr; rng = np.random.default_rng(7)
air = np.convolve(rng.standard_normal(n), np.ones(400) / 400, 'same') * 0.6; out = air * np.clip(t / 1.0, 0, 1) * np.clip((d - t) / 1.2, 0, 1)
def bell(t0, f, a=.5, dec=3.5):
    i = int(t0 * sr); m = int(1.6 * sr); tt = np.arange(m) / sr; s = a * np.exp(-tt * dec) * (np.sin(2*np.pi*f*tt) + .4*np.sin(2*np.pi*f*2.01*tt) + .2*np.sin(2*np.pi*f*3.0*tt))
    out[i:i + m] += s[:max(0, min(m, n - i))]
for k, t0 in enumerate([1.9, 3.5, 5.1, 6.7, 8.3]): bell(t0, 523.25 * 2 ** (k * 2 / 12))   # = DAYS в demo.js
bell(10.1, 392, .6, 2.5)
out = out / np.max(np.abs(out)) * 0.8
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
