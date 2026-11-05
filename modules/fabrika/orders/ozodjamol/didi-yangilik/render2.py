"""Версия на нашем дикторе: время сцен из render.py пересчитывается по фразам (map.json: old→new)."""
import os, sys, json, bisect
import render as R
M = json.load(open("/home/claude/vo/map.json")); OLD, NEW = M["old"], M["new"]
R.DUR = NEW[-1]
def warp(t):
    i = max(0, min(len(NEW) - 2, bisect.bisect_right(NEW, t) - 1))
    a, b = NEW[i], NEW[i + 1]; oa, ob = OLD[i], OLD[i + 1]
    return oa + (ob - oa) * min(1, max(0, (t - a) / (b - a)))
_hdr = R.header
def frame2(n):
    t = n / R.FPS; to = warp(t)
    R.header = lambda cv, _t: _hdr(cv, t)          # полоса прогресса — реальное время
    return R.frame(int(round(to * R.FPS)) if False else to * R.FPS)
# frame() принимает номер кадра → t = n/FPS; отдаём дробный «номер» старого времени
if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2]); os.makedirs("/home/claude/didi/fr2", exist_ok=True)
    for n in range(a, b):
        frame2(n).save(f"/home/claude/didi/fr2/{n:05d}.jpg", quality=92)
