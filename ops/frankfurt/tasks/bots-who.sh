#!/usr/bin/env bash
# Только чтение: @username каждого бота-пульта (getMe). Токены не печатаются. Ничего не публикует.
set -uo pipefail
set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
/opt/papa-venv/razvedka/bin/python - <<'PY'
import json, os, urllib.request
for name, var in (("КАТТА ДАВРА (главный)", "GENPLAN_BOT_TOKEN"), ("PaparazziUZ", "PAPARAZZI_BOT_TOKEN"), ("Хўжаобод", "XOJAOBOD_BOT_TOKEN")):
    tok = os.environ.get(var)
    if not tok:
        print(f"{name}: нет токена"); continue
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getMe", timeout=20) as r:
            me = json.loads(r.read())["result"]
        print(f"{name}: @{me['username']} — {me['first_name']}")
    except Exception as e:
        print(f"{name}: ошибка {e}")
PY
echo "== BOTS_WHO_DONE"
