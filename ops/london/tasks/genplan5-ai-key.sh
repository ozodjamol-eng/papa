#!/usr/bin/env bash
# Лондон, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: ключ Anthropic для GENPLAN 5 (Хўжаобод) — хук по смыслу + фирменная подпись (решение 17.10).
# Тот же ключ, что на Франкфурте (sk-ant-...). Ввод скрыт: не виден на экране, не попадает в чат и репозиторий.
# Выключить: rm /etc/systemd/system/xojaobod-genplan-v3.service.d/papa-ai.conf && systemctl daemon-reload && systemctl restart xojaobod-genplan-v3
set -euo pipefail
SVC=xojaobod-genplan-v3.service; D=/opt/xojaobod-genplan-v5; PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
grep -q "def _papa_hook" $D/genplan_v3/hook_policy.py || { echo "сначала нужна правка genplan5-ai-hook"; exit 1; }
read -rsp "Вставьте ключ Anthropic (sk-ant-...) и нажмите Enter: " KEY; echo
KEY=$(printf '%s' "$KEY" | tr -d '[:space:]')
[[ "$KEY" == sk-ant-* ]] || { echo "Это не похоже на ключ Anthropic (должен начинаться с sk-ant-)"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://api.anthropic.com/v1/models -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01")
[[ "$code" == 200 ]] || { echo "AI_KEY_BAD (ответ $code) — проверьте ключ"; exit 1; }
install -d -m 700 /etc/papa-genplan5
( umask 077; printf 'ANTHROPIC_API_KEY=%s\nAI_MODEL=claude-haiku-5-5\nPAPA_AI_HOOKS=1\n' "$KEY" > /etc/papa-genplan5/ai.env )
unset KEY
echo "проверка хука (стихотворение, < 1 цента):"
( set -a; . /etc/papa-genplan5/ai.env; set +a; cd $D && "$PY" -c 'from genplan_v3 import hook_policy as h; print("  ", h._papa_sig("Жуда чиройли шеър")); print("  ", h._papa_hook("❗️ Жуда чиройли шеър") or "(ИИ решил: без хука)")' )
install -d /etc/systemd/system/$SVC.d
printf '[Service]\nEnvironmentFile=-/etc/papa-genplan5/ai.env\n' > /etc/systemd/system/$SVC.d/papa-ai.conf
systemctl daemon-reload; systemctl restart $SVC; sleep 6
systemctl is-active --quiet $SVC || { rm -f /etc/systemd/system/$SVC.d/papa-ai.conf; systemctl daemon-reload; systemctl restart $SVC; echo "!! служба не поднялась — включение отменено"; exit 1; }
echo "служба: $(systemctl is-active $SVC)"
echo "== GENPLAN5_AI_KEY_OK (Хўжаобод: текст → фирменная подпись → хук по смыслу)"
