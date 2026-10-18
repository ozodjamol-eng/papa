#!/usr/bin/env bash
# Только чтение: ищем токен @XotiraMarkaziBot во всех env-файлах (/etc, /opt, /root, /srv, /home) и код с «ФИО».
set -uo pipefail
check(){ python3 - "$1" <<'PY'
import json, sys, urllib.request
try:
    with urllib.request.urlopen(f"https://api.telegram.org/bot{sys.argv[1]}/getMe", timeout=15) as r:
        print(json.loads(r.read())["result"]["username"])
except Exception:
    print("-")
PY
}
seen=0
while read -r f; do
  grep -aoE '[0-9]{8,12}:[A-Za-z0-9_-]{30,}' "$f" 2>/dev/null | sort -u | while read -r t; do
    u=$(check "$t"); [[ "${u,,}" == *xotira* ]] && echo "НАЙДЕН ТОКЕН: $f → @$u"
  done
done < <(find /etc /opt /root /srv /home -xdev -type f \( -name '*.env' -o -name '.env' -o -name '*.env.*' -o -name 'config*.py' -o -name '*.json' -o -name '*.toml' \) -size -200k 2>/dev/null | grep -vE 'node_modules|site-packages|/\.git/|dist-packages')
echo "== код бота (ФИО + ёш автоматик):"
grep -rIl --exclude-dir={node_modules,.git,venv,.venv,__pycache__,site-packages} -E 'Ёш автоматик|намунадагидек ёзинг|XotiraMarkaziBot' /opt /root /srv /home 2>/dev/null | sed -E 's#^(/[^/]+/[^/]+/[^/]+).*#\1#' | sort | uniq -c | head
echo "== Python-процессы ботов сейчас:"; ps -eo pid,etime,cmd | grep -E 'python|node' | grep -v grep | cut -c1-140 | head -20
echo "== XOTIRA_FIND2_DONE"
