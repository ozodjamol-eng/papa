#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен Instagram @shodiyona.mebel.uz для Воронки Shodiyona Mebel.
# Токен вводится скрыто, пишется только в /etc/papa-voronka/shodiyona.env (0600). Токен Paparazzi не трогается.
set -Eeuo pipefail
PAPA_VORONKA_IG_ENV=/etc/papa-voronka/shodiyona.env python3 /opt/papa/ops/frankfurt/voronka_token.py
if id papa-voronka >/dev/null 2>&1; then chown papa-voronka:papa-voronka /etc/papa-voronka/shodiyona.env; fi
grep -q '^IG_USERNAME=shodiyona\.mebel\.uz$' /etc/papa-voronka/shodiyona.env || echo "⚠️ это НЕ @shodiyona.mebel.uz — проверьте, для какого аккаунта создан токен"
systemctl try-restart papa-voronka-shodiyona 2>/dev/null || true
echo "== SHODIYONA_TOKEN_SAVED (дальше: shodiyona-voronka-install)"
