#!/usr/bin/env bash
# 🔎 31.10 (только чтение): подробности находок аудита — какие автотесты падают на сервере, TypeError «в хаб», failed за сутки.
set -uo pipefail
echo "== автотесты razvedka (как в аудите: без сети и ключей):"
cd /opt/papa/modules/razvedka
env -u GEMINI_API_KEY -u ANTHROPIC_API_KEY -u GITHUB_TOKEN PAPA_GENPLAN_STATE="$(mktemp -d)" \
  HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 \
  timeout 280 /opt/papa-venv/razvedka/bin/python -m unittest discover -s tests 2>&1 \
  | grep -E -A14 "^(FAIL|ERROR):" | grep -vE "^\s*$" | cut -c1-220 | head -90
echo "== «в хаб» TypeError (сутки):"
journalctl -u papa-genplan --since "-24h" --no-pager -o short-iso | grep -B2 -A6 "TypeError" | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | cut -c1-240 | tail -30
echo "== failed за сутки (журналы PAPA):"
journalctl --since "-24h" --no-pager -o short-iso -u 'papa-*' | grep -E "failed|Failed" | grep -v "papa-audit" | cut -c1-200 | tail -15
echo "== AUDIT_DETAILS_DONE"
