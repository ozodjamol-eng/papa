#!/usr/bin/env bash
# Только чтение: @username ботов GENPLAN 5 / Хўжаобода (getMe). Токены не печатаются. Ничего не публикует.
set -uo pipefail
for f in /opt/xojaobod-genplan-v5/.env /opt/xojaobod-genplan-v5/config.env /opt/xojaobod-autopost/.env /opt/xojaobodcity24bot/.env; do
  [[ -r $f ]] || continue
  grep -E '^[A-Z_][A-Z0-9_]*TOKEN[A-Z0-9_]*=' "$f" | while IFS='=' read -r k v; do
    v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
    u=$(python3 - "$v" <<'PY'
import json, sys, urllib.request
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{sys.argv[1]}/getMe", timeout=20) as r:
        me = json.loads(r.read())["result"]
    print(f"@{me['username']} — {me['first_name']}")
except Exception as e:
    print(f"не бот/ошибка ({type(e).__name__})")
PY
)
    echo "$f  $k: $u"
  done
done
echo "== BOTS_WHO_DONE"
