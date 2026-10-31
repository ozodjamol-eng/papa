#!/usr/bin/env bash
# Франкфурт, ТОЛЬКО ВЛАДЕЛЕЦ В КОНСОЛИ (31.10): ключ OpenRouter (предоплата $5) → прокси Gemini.
# Агенты сначала берут бесплатный Google, при лимите — OpenRouter. Ключ на экране не виден, в чат/репозиторий не попадает.
# Откат: rm /etc/papa-gemini-proxy/on && systemctl disable --now papa-gemini-proxy
set -euo pipefail
install -d -m 750 /etc/papa-gemini-proxy
read -rsp "Вставьте ключ OpenRouter (sk-or-...) и нажмите Enter: " K; echo
[[ "$K" =~ ^sk-or-[A-Za-z0-9_-]{20,}$ ]] || { echo "Это не похоже на ключ OpenRouter — скопируйте целиком (начинается с sk-or-)"; exit 1; }
OPENROUTER_API_KEY="$K" python3 - <<'PY'
import json, os, urllib.request, urllib.error
k = os.environ["OPENROUTER_API_KEY"]
req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {k}"})
try:
    d = json.loads(urllib.request.urlopen(req, timeout=20).read()).get("data", {})
except urllib.error.HTTPError as e:
    raise SystemExit(f"❌ Ключ не принят OpenRouter: HTTP {e.code}")
lim = d.get("limit"); used = d.get("usage") or 0
print(f"✅ ключ принят · лимит ключа: {'нет' if lim is None else f'${lim}'} · потрачено: ${used:.4f}")
if lim is None or lim > 5:
    print("⚠️ У ключа нет лимита $5 — поставьте его на странице ключей OpenRouter (Edit → Credit limit 5)")
body = {"model": "google/gemini-2.5-flash-lite", "messages": [{"role": "user", "content": "Ўзбекча бир сўз: салом"}], "max_tokens": 10}
req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                             headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
r = json.loads(urllib.request.urlopen(req, timeout=60).read())
print("✅ проба Gemini через OpenRouter:", (r["choices"][0]["message"]["content"] or "").strip()[:40])
PY
umask 077; printf 'OPENROUTER_API_KEY=%s\n' "$K" > /etc/papa-gemini-proxy/env; unset K
chmod 600 /etc/papa-gemini-proxy/env
( cd /opt/papa/ops/frankfurt && python3 -m unittest -q test_gemini_proxy 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-gemini-proxy.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-gemini-proxy; sleep 2
systemctl is-active -q papa-gemini-proxy || { journalctl -u papa-gemini-proxy -n 20 --no-pager; exit 1; }
GK=$(grep -E '^GEMINI_API_KEY=' /etc/papa-genplan/ai.env /etc/papa-genplan/genplan.env 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[\"']//g" || true)
code=$(curl -s -o /dev/null -w '%{http_code}' -H 'content-type: application/json' -H "x-goog-api-key: $GK" \
  -d '{"contents":[{"parts":[{"text":"hi"}]}],"generationConfig":{"maxOutputTokens":5}}' \
  http://127.0.0.1:8790/v1beta/models/gemini-flash-lite-latest:generateContent || true)
echo "проба через прокси: HTTP $code"
touch /etc/papa-gemini-proxy/on
echo "✅ Прокси включён: агенты идут через него (Google бесплатно → OpenRouter при лимите). Потолок трат — 5 долларов на счёте."
echo "== OPENROUTER_KEY_DONE"
