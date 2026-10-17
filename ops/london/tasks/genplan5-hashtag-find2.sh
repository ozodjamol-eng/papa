#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ (шаг 2): точка, где GENPLAN 5 собирает итоговую подпись перед отправкой в группу. Ничего не меняет.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; G=$D/genplan_v3
cd "$D" || { echo "NO_DIR $D"; exit 1; }
show() { local f=$1 pat=$2 n=${3:-30}; local l; l=$(grep -n -m1 -E "$pat" "$f" | cut -d: -f1); [[ -n "$l" ]] && { echo "== $f:$l"; sed -n "${l},$((l+n))p" "$f" | cut -c1-200; }; }
show $G/telegram_ui.py "def _compose_hashtag_caption" 8
show $G/telegram_ui.py "def _effective_caption" 25
show $G/subtypes.py "def render_caption" 25
show $G/hook_policy.py "def compose\(" 40
echo "== где вызывается отправка (send_*) с подписью:"
grep -rn --include=*.py -E "send_(message|video|photo|animation|document|media_group|copy)|copy_message\(" $G | grep -iv test | cut -c1-200 | head -30
echo "== кто вызывает hook_policy.compose / footer_engine:"
grep -rn --include=*.py -E "hook_policy\.compose|footer_engine\.[a-z_]+\(" $G | grep -iv test | cut -c1-200 | head -20
echo "== тесты есть?"; ls tests 2>/dev/null | head -50 | tr '\n' ' '; echo
echo "== DONE_FIND2"
