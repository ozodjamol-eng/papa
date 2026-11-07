#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: токен Instagram VOLIDAM (основной аккаунт Нодирбека) для Воронки.
# Токен вводится скрыто, пишется только в /etc/papa-voronka/volidam.env (0600). Другие воронки не трогаются.
set -Eeuo pipefail
PAPA_VORONKA_IG_ENV=/etc/papa-voronka/volidam.env python3 /opt/papa/ops/frankfurt/voronka_token.py
if id papa-voronka >/dev/null 2>&1; then chown papa-voronka:papa-voronka /etc/papa-voronka/volidam.env; fi
echo "Аккаунт токена: $(grep '^IG_USERNAME=' /etc/papa-voronka/volidam.env | cut -d= -f2) — должен быть Instagram Нодирбека"
echo "== VOLIDAM_TOKEN_SAVED (дальше: papa-update volidam-voronka-install)"
