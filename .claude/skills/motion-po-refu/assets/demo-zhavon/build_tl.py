#!/usr/bin/env python3
"""Собрать timeline.js + дорожку голоса из озвучки (voice-out: W01..W11.mp3 + .align.json).
usage: build_tl.py <папка_озвучки> <comp_dir> [префикс файлов, по умолчанию W]   →  comp/timeline.js, comp/voice.wav
Паузы — медленный темп (владелец 04.11: «чуть медленнее и понятнее»); глава ≥ 3,4 с."""
import json, subprocess, sys, os
src, comp = sys.argv[1], sys.argv[2]; PFX = sys.argv[3] if len(sys.argv) > 3 else "W"
SCREEN = ["БУ — SHODIYONA ЖАВОНИ.",
          "ТАШҚАРИДАН ЧИРОЙЛИ. ИЧИГА НИМА СИҒАДИ?",
          "КИТОБЛАР, ГУЛЛАР, ҚУТИЛАР, ЎЙИНЧОҚЛАР — ҲАММАСИ ЖОЙИДА!",
          "ЭНДИ — ОЛТИТА ИСБОТ.",
          "БИРИНЧИ — ЎЛЧАМИ. ОДАМ ЁНИДА КЎРИНГ.",
          "ИККИНЧИ — МАТЕРИАЛИ. МЕТАЛЛ КАРКАС, ЯҚИНДАН ҚАРАНГ.",
          "УЧИНЧИ — ХОНАДА ҚАНДАЙ ТУРИШИ.",
          "ТЎРТИНЧИ — АНИҚ ЎЛЧАМЛАР: БЎЙИ ВА ЭНИ.",
          "БЕШИНЧИ — НАРХИ. ИШЛАБ ЧИҚАРУВЧИДАН, ЎРТАКАШСИЗ.",
          "ОЛТИНЧИ — ЎЛЧАМНИ БУЮРТМАНГИЗГА ҚАРАБ ЯСАЙМИЗ.",
          "SHODIYONA MEBEL. ИШЛАБ ЧИҚАРУВЧИДАН — ТЎҒРИДАН-ТЎҒРИ!"]
GAP_AFTER = [0.7, 0.8, 1.4, 0.6, 0.9, 0.9, 0.9, 0.9, 0.9, 1.0, 1.9]  # пауза после строки
MIN_CH = 3.4
LEAD = 1.15
t = LEAD; lines = []; parts = []
for i in range(11):
    n = f"{PFX}{i+1:02d}"; al = json.load(open(f"{src}/{n}.align.json"))
    ch, cs, ce = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    nz = [k for k, c in enumerate(ch) if c.strip()]; a0, a1 = cs[nz[0]], ce[nz[-1]]
    # слова латиницы по пробелам
    words, cur, w0 = [], "", None
    for k, c in enumerate(ch):
        if c == " ":
            if cur: words.append((cur, w0, ce[k - 1])); cur = ""
        else:
            if not cur: w0 = cs[k]
            cur += c
    if cur: words.append((cur, w0, ce[len(ch) - 1]))
    words = [w for w in words if w[0].strip(".…") not in ("—", "-", "")]
    scr = [s for s in SCREEN[i].split() if s not in ("—", "-")]
    if len(scr) != len(words): sys.exit(f"{n}: слов {len(words)} ≠ экран {len(scr)}: {[w[0] for w in words]}")
    off = t - a0
    lines.append({"t0": round(t, 3), "t1": round(off + a1, 3), "words": [[s, round(off + w[1], 3), round(off + w[2], 3)] for s, w in zip(scr, words)]})
    parts.append((f"{src}/{n}.mp3", off))
    dur = a1 - a0; gap = GAP_AFTER[i]
    if 4 <= i <= 9: gap = max(gap, MIN_CH - dur)
    t = off + a1 + gap
D = round(t, 3)
open(f"{comp}/timeline.js", "w").write("window.TL = " + json.dumps({"dur": D, "lines": lines}, ensure_ascii=False) + ";\n")
# дорожка голоса: каждая строка на своё место
inp = []; flt = []
for k, (f, off) in enumerate(parts):
    inp += ["-i", f]; flt.append(f"[{k}:a]aresample=48000,adelay={int(max(0, off) * 1000)}:all=1[a{k}]")
flt.append("".join(f"[a{k}]" for k in range(len(parts))) + f"amix=inputs={len(parts)}:normalize=0,apad,atrim=0:{D}[v]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(flt), "-map", "[v]", "-ac", "1", f"{comp}/voice.wav"], check=True)
print("dur", D, "lines", [(l["t0"], l["t1"]) for l in lines])
