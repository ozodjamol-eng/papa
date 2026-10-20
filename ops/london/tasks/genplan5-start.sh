#!/usr/bin/env bash
# ОТКАТ перехода: снова запустить GENPLAN 5 (Хўжаобод). ВАЖНО: перед этим на Франкфурте убрать бот Хўжаобода из PAPA
# (иначе два «хозяина» у одного бота). Запускать только по решению владельца.
set -Eeuo pipefail
systemctl enable --now xojaobod-genplan-v3.service
for t in xojaobod-evening-digest.timer papa-genplan5-guard.timer; do systemctl enable --now "$t" 2>/dev/null || true; done
sleep 3; echo "GENPLAN 5: $(systemctl is-active xojaobod-genplan-v3.service)"
echo "== GENPLAN5_START_DONE"
