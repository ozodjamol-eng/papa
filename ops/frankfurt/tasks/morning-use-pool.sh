#!/usr/bin/env bash
# 🌅 Готовый пост владельца: последний пост с медиа в NEXUS MORNING POOL → ближайшее утро «Хайрли тонг/Жума муборак»
# во всех каналах (наша подпись, чужие @/ссылки убираются). Предпросмотр с ✅ придёт в бот; без ✅ не выйдет.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-usepool-$(date +%F-%H%M)"
echo "1/2 последний пост в NEXUS MORNING POOL:"
systemctl start papa-razvedka@pool-latest.service
journalctl -u papa-razvedka@pool-latest.service -n 3 --no-pager -o cat | grep -E "POOL_LATEST|Error|не найден" || true
L=/var/lib/papa-razvedka-pub/morning/latest.json
[[ -s "$L" ]] || { echo "НЕ НАЙДЕН пост в пуле"; exit 1; }
install -o papa-genplan -g papa-genplan -m 0600 "$L" /var/lib/papa-genplan/pool-latest.json
echo "2/2 ставлю на утро:"
set -a; . /etc/papa-genplan/genplan.env; set +a
sudo -u papa-genplan --preserve-env=GENPLAN_BOT_TOKEN,HUB_CHAT_ID,OWNER_IDS $PY - "$DB" <<'PY'
import json, os, sys
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import morning, store
from genplan.__main__ import cfg, make_bot
db = store.connect(sys.argv[1])
latest = json.load(open("/var/lib/papa-genplan/pool-latest.json", encoding="utf-8"))
done = morning.use_manual(make_bot(os.environ["GENPLAN_BOT_TOKEN"]), db, cfg(), dict(os.environ), latest)
print("  готово:", *done, sep="\n   ")
PY
echo "Предпросмотры с ✅ придут в бот через минуту. Без ✅ не выйдет."
echo "== MORNING_USE_POOL_DONE"
