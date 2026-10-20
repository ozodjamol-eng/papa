#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: правило «окно защиты рекламы» GENPLAN 5 — сколько минут должно быть между рекламами. Ничего не меняет.
set -uo pipefail
G=/opt/xojaobod-genplan-v5
grep -rn --include=*.py -iE "ad_protection|protection_window|AD_.*MIN|ad_gap|ads?_spacing" "$G/genplan_v3" | grep -v venv | cut -c1-220 | head -30
echo "== GENPLAN5_AD_WINDOW_FIND_DONE"
