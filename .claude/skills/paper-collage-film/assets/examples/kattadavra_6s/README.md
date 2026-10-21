# КАТТА ДАВРА — интро 6 с (16:9) + 9:16 — первый ролик PAPA на этом скилле (21.10.2026)
Повторить: `bash scripts/new_project.sh <root> kattadavra` → скопировать сюда-файлы в `comp/` (score.html → `audio/`) →
`python3 tools/fonts_local.py . "Unbounded|Rubik|Russo One"` → `python3 tools/static_face.py . "Unbounded:900|Rubik:900"` →
`node tools/code_cutouts.mjs .` → `node tools/render_audio.mjs "$PWD/audio/score.html" audio/score.wav` → `ffmpeg -i audio/score.wav -c:a aac -b:a 256k audio/score.m4a` →
`WORKERS=3 bash tools/render_film.sh final audio/score.m4a out_16x9.mp4` → `bash tools/vertical.sh out_16x9.mp4`.
Все вырезки — кодом (cutouts_code.html), платных генераций 0.
