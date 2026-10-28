import json, re
from faster_whisper import WhisperModel
S = {}
for l in open("script.txt", encoding="utf-8"):
    k, t = l.rstrip("\n").split(" | ", 1); S[k] = t
m = WhisperModel("small", device="cpu", compute_type="int8")
out = {}
for k, t in S.items():
    my = t.split()
    import subprocess, numpy as np
    a = np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",f"vo/{k}.mp3","-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout, np.float32)
    segs, _ = m.transcribe(a, language="uz", word_timestamps=True, vad_filter=False)
    ws = [w for s in segs for w in s.words]
    st, en = ws[0].start, ws[-1].end
    if len(ws) == len(my):
        tm = [(w.start, w.end) for w in ws]; mode = "match"
    else:
        def cl(w): return len(re.sub(r"\W", "", w)) + 1
        WL = [cl(w.word) for w in ws]; WT = sum(WL); xs=[0.0]; ys=[ws[0].start]
        acc = 0
        for w, x in zip(ws, WL):
            xs.append((acc + 0.0001) / WT); ys.append(w.start); acc += x; xs.append(acc / WT); ys.append(w.end)
        import numpy as np
        L = [cl(w) for w in my]; tot = sum(L); acc = 0; tm = []
        for x in L:
            a = float(np.interp(acc / tot, xs, ys)); acc += x; tm.append((a, float(np.interp(acc / tot, xs, ys))))
        mode = f"prop {len(ws)}/{len(my)}"
    out[k] = {"words": my, "t": tm}
    print(k, mode, round(st, 2), round(en, 2))
json.dump(out, open("words.json", "w"), ensure_ascii=False)
