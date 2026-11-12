#!/usr/bin/env bash
# 📋 Только чтение (12.11): какие Telegram-источники выбраны по каналам и рубрикам (choice.json) — для сверки «что есть в Telegram / чего нет».
set -uo pipefail
F=/var/lib/papa-sources-choice/choice.json
[[ -r $F ]] || { echo "нет $F"; exit 0; }
python3 - "$F" <<'P'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
def show(x, pad=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("auto_seen", "seen", "checked", "vision", "cache"): 
                print(f"{pad}{k}: ({len(v) if hasattr(v,'__len__') else v})"); continue
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}:"); show(v, pad + "  ")
            else:
                print(f"{pad}{k}: {str(v)[:80]}")
    elif isinstance(x, list):
        for v in x[:60]:
            if isinstance(v, (dict, list)): show(v, pad + "- ")
            else: print(f"{pad}- {str(v)[:80]}")
        if len(x) > 60: print(f"{pad}… ещё {len(x)-60}")
show(d)
P
echo "== SOURCES_LIST_DONE"
