#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: где GENPLAN 5 (Хўжаобод) ставит/оставляет хэштеги — для правила «один хэштег по смыслу или ни одного».
# Повод 17.10: пост рубрики «Саломатлик» вышел с двумя тегами (#САЛОМАТЛИК #ТИББИЁТ). Ничего не меняет.
set -uo pipefail
D=/opt/xojaobod-genplan-v5
cd "$D" || { echo "NO_DIR $D"; exit 1; }
echo "== файлы, где есть хэштеги:"
grep -rlin --include=*.py -e "hashtag" -e "хэштег" -e "хештег" -e "САЛОМАТЛИК" -e "ТИББИЁТ" genplan_v3 | grep -iv test | head -20
echo "== строки с хэштегами (код):"
grep -rn --include=*.py -i -e "hashtag" -e "САЛОМАТЛИК" -e "ТИББИЁТ" genplan_v3 | grep -iv test | cut -c1-220 | head -40
echo "== функции вокруг хэштегов:"
grep -rn --include=*.py -E "def .*(hashtag|tag|caption|finalize|signature|build_text|render).*\(" genplan_v3 | grep -iv test | cut -c1-180 | head -30
echo "== настройки/каталоги тегов (не .py):"
grep -rlin -e "САЛОМАТЛИК" -e "ТИББИЁТ" --include=*.json --include=*.toml --include=*.yaml --include=*.yml --include=*.txt . 2>/dev/null | grep -v venv | head -10
echo "== DONE_FIND"
