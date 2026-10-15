#!/usr/bin/env bash
# 🌅 Материалы владельца из PAPA СКЛАД (последние 3 с медиа) → ближайшее утро, второй пост (вместо «Бугун — … куни»)
# по одному на канал: Давра, Paparazzi, Хўжаобод; текст один (первая подпись) + дата; без ✅ не выйдет.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-sklad-$(date +%F-%H%M)"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan papa-fabrika
echo "1/2 последние 3 материала в PAPA СКЛАД:"
systemctl start papa-razvedka@sklad-latest.service
journalctl -u papa-razvedka@sklad-latest.service -n 3 --no-pager -o cat | grep -E "SKLAD_LATEST|Error|не найден" || true
L=/var/lib/papa-razvedka-pub/morning/sklad.json
[[ -s "$L" ]] || { echo "НЕ НАЙДЕНЫ материалы в складе"; exit 1; }
install -o papa-genplan -g papa-genplan -m 0600 "$L" /var/lib/papa-genplan/sklad.json
echo "2/2 ставлю на утро:"
set -a; . /etc/papa-genplan/genplan.env; set +a
sudo -u papa-genplan --preserve-env=GENPLAN_BOT_TOKEN,HUB_CHAT_ID,OWNER_IDS $PY - "$DB" <<'PY'
import json, os, sys
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import morning, store
from genplan.__main__ import cfg, make_bot
db = store.connect(sys.argv[1])
# будущие утренние посты, которые выпали из очереди (пропуск/отмена), — вернуть; время — по новым правилам
latest = json.load(open("/var/lib/papa-genplan/sklad.json", encoding="utf-8"))
done = morning.use_sklad(make_bot(os.environ["GENPLAN_BOT_TOKEN"]), db, cfg(), dict(os.environ), latest)
print("  готово:", *done, sep="\n   ")
morning.ensure_all(db, cfg(), __import__("datetime").datetime.now(morning.plan.TZ))
print("  утро (канал · пост · время · статус · готов · ✅):")
for r in db.execute("SELECT channel, key, day, substr(at,12,5) t, status, prepared, approved FROM fixed_posts "
                    "WHERE day>=date('now','+5 hours') ORDER BY day, at"):
    print("   ", r["day"][5:], r["channel"], r["key"], r["t"], r["status"], r["prepared"], r["approved"])
PY
echo "Предпросмотры с ✅ придут в бот через минуту. Без ✅ не выйдет."
echo "== MORNING_SKLAD_DONE"
