#!/usr/bin/env python3
"""Звук демо «Номи — аслида» (15 с): тёплый пэд + «вжик» зачёркивания + «тук» на роль + тики фишек + щелчки телефона.
usage: make_audio.py out.wav  → ffmpeg … -af loudnorm=I=-16:TP=-1.5"""
import sys, wave, numpy as np
sr = 48000; d = 15.0; n = int(sr * d); t = np.arange(n) / sr; out = np.zeros(n)
for f, a in [(196, .10), (246.9, .07), (293.7, .06), (98, .08)]: out += a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.2 * t))
out *= np.clip(t / 1.2, 0, 1) * np.clip((d - t) / 1.5, 0, 1)
rng = np.random.default_rng(7)
def add(t0, s):
    i = int(t0 * sr); m = min(len(s), n - i); out[i:i + m] += s[:m]
def tick(t0, f=1320, a=.45, dec=18):
    tt = np.arange(int(.25 * sr)) / sr; add(t0, a * np.exp(-tt * dec) * (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.5 * tt)))
def swish(t0, dur=.4, a=.35):
    m = int(dur * sr); tt = np.arange(m) / sr; env = np.sin(np.pi * tt / dur) ** 2; nz = rng.standard_normal(m); nz = np.convolve(nz, np.ones(6) / 6, 'same'); add(t0, a * env * nz)
for t0 in (0.9, 4.5, 8.1):
    swish(t0 + 0.9); tick(t0 + 1.6, 520, .7, 9); tick(t0 + 1.62, 780, .4, 9)
    for k in range(3): tick(t0 + 2.2 + k * .35, 1100 + k * 150, .3)
tick(11.9, 660, .6, 8)
for k in range(17): tick(13.4 + k * 0.05, 1800, .08, 60)
out = out / np.max(np.abs(out)) * 0.8
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * 32767).astype(np.int16).tobytes()); w.close()
