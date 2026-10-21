#!/usr/bin/env bash
# usage: strip.sh <frames_dir> <out.png> [every_seconds=1]  — contact sheet of one frame per N seconds (24 fps frames f_00000.*)
P="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"; FR="$1"; OUT="$2"; EV="${3:-1}"; TH="$P/review/.strip_th"; rm -rf "$TH"; mkdir -p "$TH"; ARGS=()
export PATH="$P/tools/bin:$PATH"   # node fallback linked by new_project.sh (harmless when node is on PATH)
N=$(ls "$FR" | wc -l | tr -d ' '); STEP=$(python3 -c "print(max(1,int(round($EV*24))))")
for ((n = STEP/2; n < N; n += STEP)); do f=$(ls "$FR" | sed -n "$((n+1))p"); [ -z "$f" ] && break; if command -v sips >/dev/null; then sips -Z 400 "$FR/$f" --out "$TH/$n.jpg" -s format jpeg >/dev/null 2>&1; else ffmpeg -v error -y -i "$FR/$f" -vf "scale=400:-2" "$TH/$n.jpg"; fi; ARGS+=("$TH/$n.jpg|$(python3 -c "print(f'{$n/24:.1f}s')")"); done
node "$P/tools/sheet.mjs" "$OUT" 6 320 "${ARGS[@]}" >/dev/null && echo "$OUT"
