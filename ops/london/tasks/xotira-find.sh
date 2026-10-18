#!/usr/bin/env bash
# Только чтение: где живёт бот «ХОТИРА МАРКАЗИ» (@XotiraMarkaziBot) и почему молчит. Токены не печатаются.
set -uo pipefail
echo "== службы/таймеры со словом xotira/hotira/memory/khotira:"
systemctl list-unit-files --no-legend 2>/dev/null | grep -iE 'xotira|hotira|xotira|memor|khotira' || echo "  нет"
echo "== в списке остановленного старого NEXUS (15.10):"
cat /var/backups/papa-archive/old-nexus-units-*.state 2>/dev/null | grep -iE 'xotira|hotira|memor|khotira|bot' || echo "  нет совпадений"
echo "== папки и файлы с упоминанием XotiraMarkazi:"
grep -rIl --exclude-dir={node_modules,.git,venv,.venv,__pycache__} -iE 'XotiraMarkazi|ХОТИРА МАРКАЗИ|xotira' /opt /root /srv /home 2>/dev/null | head -30 || true
echo "== какой токен из .env = @XotiraMarkaziBot:"
find /opt /root /srv /home -maxdepth 4 -name '*.env' -o -maxdepth 4 -name '.env' 2>/dev/null | while read -r f; do
  [[ -r $f ]] || continue
  grep -E '^[A-Z_][A-Z0-9_]*TOKEN[A-Z0-9_]*=' "$f" 2>/dev/null | while IFS='=' read -r k v; do
    v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
    u=$(python3 - "$v" <<'PY'
import json, sys, urllib.request
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{sys.argv[1]}/getMe", timeout=15) as r:
        print(json.loads(r.read())["result"]["username"])
except Exception:
    print("-")
PY
)
    [[ "${u,,}" == *xotira* ]] && echo "  НАЙДЕН: $f  $k → @$u"
  done
done
echo "== GENPLAN 5 / боты сейчас:"
for s in xojaobod-genplan-v3 xojaobodcity24bot goldwater-bot; do echo "  $s: $(systemctl is-active $s)"; done
echo "== XOTIRA_FIND_DONE"
