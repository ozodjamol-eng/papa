#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: включены ли в GENPLAN 5 хук по смыслу и фирменная подпись. Ключ не показывается.
set -uo pipefail
SVC=xojaobod-genplan-v3.service
echo "правка в коде: $(grep -q 'def _papa_hook' /opt/xojaobod-genplan-v5/genplan_v3/hook_policy.py && echo да || echo нет)"
echo "файл ключа: $([[ -s /etc/papa-genplan5/ai.env ]] && echo есть || echo нет)"
echo "флаг PAPA_AI_HOOKS=1: $(grep -q '^PAPA_AI_HOOKS=1' /etc/papa-genplan5/ai.env 2>/dev/null && echo да || echo нет)"
echo "подключено к службе: $([[ -f /etc/systemd/system/$SVC.d/papa-ai.conf ]] && echo да || echo нет)"
pid=$(systemctl show -p MainPID --value $SVC)
echo "служба видит флаг: $(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -q '^PAPA_AI_HOOKS=1' && echo да || echo нет)"
echo "служба: $(systemctl is-active $SVC)"
echo "== AI_CHECK_DONE"
