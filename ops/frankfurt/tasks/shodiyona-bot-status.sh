#!/usr/bin/env bash
# Франкфурт: состояние бота Shodiyona — служба, счётчики заявок/заказов/товаров (без личных данных). Ничего не меняет.
set -Eeuo pipefail
echo "papa-shodiyona: $(systemctl is-active papa-shodiyona)"
DB=/var/lib/papa-shodiyona/shodiyona.sqlite3
[[ -f $DB ]] && python3 - "$DB" <<'PY'
import sqlite3, sys
c = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
q = lambda s: c.execute(s).fetchall()
print("покупателей:", q("SELECT COUNT(*) FROM users")[0][0])
print("заявки:", dict(q("SELECT status, COUNT(*) FROM leads GROUP BY status")), "· по видам:", dict(q("SELECT kind, COUNT(*) FROM leads GROUP BY kind")))
print("заказы по этапам:", dict(q("SELECT stage, COUNT(*) FROM orders GROUP BY stage")))
print("ссылка для Instagram (канал, одно нажатие):", (q("SELECT v FROM kv WHERE k='link:instagram'") or [["нет"]])[0][0])
print("пришли через канал:", (q("SELECT v FROM kv WHERE k='joins'") or [["0"]])[0][0])
print("товаров в каталоге:", q("SELECT COUNT(*) FROM products WHERE active=1")[0][0])
PY
journalctl -u papa-shodiyona -n 8 --no-pager -o cat
