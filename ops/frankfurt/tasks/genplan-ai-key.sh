#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ: ключ Anthropic (Claude) — основной ИИ для «🤖 ИИ-текст» в пультах (решение 17.10).
# Ключ вводится скрыто — не виден на экране, не попадает в чат и репозиторий. Gemini и другие ключи в ai.env не трогаются.
set -euo pipefail
read -rsp "Вставьте ключ Anthropic (sk-ant-...) и нажмите Enter: " KEY; echo
KEY=$(printf '%s' "$KEY" | tr -d '[:space:]')
[[ "$KEY" == sk-ant-* ]] || { echo "Это не похоже на ключ Anthropic (должен начинаться с sk-ant-)"; exit 1; }
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://api.anthropic.com/v1/models \
       -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01")
[[ "$code" == 200 ]] || { echo "AI_KEY_BAD (ответ $code) — проверьте ключ"; exit 1; }
F=/etc/papa-genplan/ai.env
umask 077; touch $F
grep -v -E '^(ANTHROPIC_API_KEY|AI_PRIMARY|AI_MODEL)=' $F > $F.new || true
printf 'ANTHROPIC_API_KEY=%s\nAI_PRIMARY=claude\nAI_MODEL=claude-haiku-5-5\n' "$KEY" >> $F.new
mv $F.new $F; chown root:papa-genplan $F; chmod 0640 $F
unset KEY
echo "проверка текста (одна короткая подпись, < 1 цента):"
set -a; . $F; set +a
out=$(curl -s --max-time 40 https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" \
      -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
      -d '{"model":"claude-haiku-5-5","max_tokens":60,"messages":[{"role":"user","content":"Ўзбек кирилл алифбосида битта қисқа гап ёз: куз фасли ҳақида."}]}')
echo "$out" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("  ответ ИИ:", "".join(b.get("text","") for b in d.get("content",[])) or d)' \
  || { echo "AI_TEST_FAILED — ключ сохранён, но ответа нет (проверьте баланс в console.anthropic.com)"; exit 1; }
unset ANTHROPIC_API_KEY
systemctl restart papa-genplan papa-fabrika; sleep 4
echo "genplan: $(systemctl is-active papa-genplan) | fabrika: $(systemctl is-active papa-fabrika)"
echo "== AI_KEY_OK (основной ИИ — Claude, запасной — Gemini)"
