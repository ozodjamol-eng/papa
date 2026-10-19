#!/usr/bin/env bash
# «Уши» (длинные ролики ассистент режет на части по ~4 мин: имя_01.mp3, имя_02.mp3 …): расшифровать речь из аудио в ветке ears (кладёт ассистент). Только чтение + запрос к Gemini. Ничего не публикует.
set -Eeuo pipefail
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin ears 2>/dev/null || { echo "NO_EARS_BRANCH: нет аудио"; exit 1; }
git -C /opt/papa archive FETCH_HEAD | tar -x -C "$T"
mapfile -t F < <(ls "$T"/ears/*.mp3 2>/dev/null)
[[ ${#F[@]} -gt 0 ]] || { echo "NO_AUDIO"; exit 1; }
set -a; . /etc/papa-genplan/ai.env; set +a
python3 -I /opt/papa/ops/frankfurt/hear.py "${F[@]}"
