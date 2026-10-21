#!/usr/bin/env bash
# Writes comp/clips.js = the list of clips whose frames exist (clips/<ID>.json written by fetch_clip.sh).
P="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"; shopt -s nullglob; L=""; for f in "$P"/clips/*.json; do b=$(basename "$f" .json); L="$L\"$b\","; done
echo "window.CLIPS_AVAILABLE=[${L%,}];" > "$P/comp/clips.js"; cat "$P/comp/clips.js"
