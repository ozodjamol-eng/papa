#!/usr/bin/env bash
# GENPLAN 5: хук ИИ был пустым — модель сначала «думает» и тратила весь лимит 120 токенов. Лимит → 1500. Копия + автооткат.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; F=$D/genplan_v3/hook_policy.py; SVC=xojaobod-genplan-v3.service
PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
cd "$D" || exit 1
grep -q '"max_tokens": 1500' "$F" && { echo "уже"; echo "== AI_TOKENS_DONE"; exit 0; }
B="$F.bak-$(date +%F-%H%M%S)"; cp -a "$F" "$B"; echo "копия: $B"
rollback() { cp -a "$B" "$F"; systemctl restart "$SVC"; echo "!! ОТКАТ: $1"; exit 1; }
[[ $(grep -c '"max_tokens": 120, "system": _PAPA_HOOK_SYSTEM' "$F") == 1 ]] || rollback "строка не найдена"
sed -i 's/"max_tokens": 120, "system": _PAPA_HOOK_SYSTEM/"max_tokens": 1500, "system": _PAPA_HOOK_SYSTEM/' "$F"
"$PY" -m py_compile "$F" || rollback "синтаксис"
set -a; . /etc/papa-genplan5/ai.env; set +a
out=$(cd $D && "$PY" -c 'from genplan_v3 import hook_policy as h; print(h._papa_hook("Онажоним, сиз борсиз — дунё мунаввар, сиз борсиз — қалбимда баҳор ҳар саҳар. Жуда чиройли шеър."))')
echo "проверка (стихотворение): ${out:-(без хука)}"
[[ -n "$out" ]] || rollback "ИИ всё ещё пустой"
systemctl restart "$SVC"; sleep 6; systemctl is-active --quiet "$SVC" || rollback "служба не поднялась"
echo "служба: active"; echo "== AI_TOKENS_DONE"
