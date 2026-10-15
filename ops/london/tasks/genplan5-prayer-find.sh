#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: где GENPLAN 5 разбирает время намаза (для исправления «19 10» / «19.10»). Ничего не меняет.
set -uo pipefail
D=/opt/xojaobod-genplan-v5
cd "$D" || { echo "NO_DIR $D"; exit 1; }
echo "== файлы с разбором намаза:"
grep -rln --include=*.py -e "Хуфтон" -e "Xufton" -e "huftan" genplan_v3 | head
echo "== регулярные выражения времени:"
grep -rn --include=*.py -E "re\.(compile|search|findall|match|fullmatch)\(.*(\\\\d|\[0-9\])" genplan_v3 | grep -iv test | grep -E ":|\\\\d\{1,2\}|\\\\d\\\\d" | cut -c1-200 | head -25
echo "== функции разбора:"
grep -rn --include=*.py -E "def .*(parse|bulk|prayer).*\(" genplan_v3 | grep -iv test | cut -c1-160 | head -25
echo "== DONE_FIND"
