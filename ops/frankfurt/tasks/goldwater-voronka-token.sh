#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен Instagram @goldwaterandijon для Воронки GOLD WATER (вместо ChatPlace).
# Токен вводится скрыто, пишется только в /etc/papa-voronka/goldwater.env (0600). Токен Paparazzi не трогается.
set -Eeuo pipefail
PAPA_VORONKA_IG_ENV=/etc/papa-voronka/goldwater.env python3 /opt/papa/ops/frankfurt/voronka_token.py
if id papa-voronka >/dev/null 2>&1; then chown papa-voronka:papa-voronka /etc/papa-voronka/goldwater.env; fi
grep -q '^IG_USERNAME=goldwaterandijon$' /etc/papa-voronka/goldwater.env || echo "⚠️ это НЕ @goldwaterandijon — проверьте, для какого аккаунта создан токен"
systemctl try-restart papa-voronka-goldwater 2>/dev/null || true
echo "== GOLDWATER_TOKEN_SAVED (дальше: goldwater-voronka-install)"
