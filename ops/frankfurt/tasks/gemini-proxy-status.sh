#!/usr/bin/env bash
# 🔀 Прокси Gemini: работает ли, сколько запросов ушло в бесплатный Google и сколько в OpenRouter, остаток $5. Только чтение.
set -euo pipefail
echo "служба: $(systemctl is-active papa-gemini-proxy) · включён для агентов: $([[ -e /etc/papa-gemini-proxy/on ]] && echo да || echo нет)"
cat /var/lib/papa-gemini-proxy/stats.json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(" ",k,v) for k,v in sorted(d.items())[-3:]]' || echo "  статистики пока нет"
set -a; . /etc/papa-gemini-proxy/env; set +a
python3 - <<'PY'
import json, os, urllib.request
req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
d = json.loads(urllib.request.urlopen(req, timeout=20).read()).get("data", {})
print(f"OpenRouter: потрачено ${d.get('usage') or 0:.4f} из ${d.get('limit')} · осталось ${d.get('limit_remaining')}")
PY
echo "== GEMINI_PROXY_STATUS_DONE"
