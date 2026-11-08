"""Удары песни для «Слово-удар»: python3 beats.py song.(wav|mp3|mp4) [--start 0 --dur 15] → JSON {tempo, beats, onsets}."""
import json, sys, argparse, subprocess, tempfile, os
import librosa, numpy as np
a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--start', type=float, default=0); a.add_argument('--dur', type=float, default=None)
p = a.parse_args()
with tempfile.TemporaryDirectory() as d:
    w = os.path.join(d, 'a.wav')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', str(p.start), '-i', p.src, '-vn', '-ac', '1', '-ar', '22050'] + (['-t', str(p.dur)] if p.dur else []) + [w]
    subprocess.run(cmd, check=True)
    y, sr = librosa.load(w, sr=22050)
tempo, b = librosa.beat.beat_track(y=y, sr=sr)
on = librosa.onset.onset_detect(y=y, sr=sr, units='time')
print(json.dumps({'tempo': round(float(np.atleast_1d(tempo)[0]), 1),
                  'beats': [round(float(t), 2) for t in librosa.frames_to_time(b, sr=sr)],
                  'onsets': [round(float(t), 2) for t in on]}, ensure_ascii=False))
