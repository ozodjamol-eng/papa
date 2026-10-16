#!/usr/bin/env bash
# 🌅 Охота за готовыми утренними видео: профиль Разведки находит в каналах-источниках посты-поздравления
# («Хайрли тонг», «Жума тонги муборак»…) и ПЕРЕСЫЛАЕТ лучшие в NEXUS MORNING POOL (внутри Telegram, без скачивания).
# Бот берёт видео из пула, Gemini проверяет кадры (даты, чужие логотипы, не поздравление) → утро на завтра пересобирается.
set -Eeuo pipefail
trap 'systemctl start papa-fabrika' EXIT
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
OUT=/var/lib/papa-razvedka-pub/morning
POOL=/var/lib/papa-genplan/pool
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN: Разведка не авторизована"; exit 1; }
free=$(df --output=avail -BM /var/lib | tail -1 | tr -dc 0-9)
(( free > 2000 )) || { echo "МАЛО МЕСТА: свободно ${free} МБ, нужно 2000"; exit 1; }
if systemctl is-active -q papa-razvedka@collect.service || systemctl is-active -q papa-razvedka@run.service || systemctl is-active -q papa-razvedka@curate.service; then
  echo "Сейчас идёт сбор Разведки — повторите через 10 минут"; exit 1
fi
cp -a "$DB" "$DB.bak-hunt-$(date +%F-%H%M)"
echo "1/4 код и тесты:"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan; systemctl stop papa-fabrika
echo "2/4 охота (10–25 минут, ход ниже):"
systemctl start --no-block papa-razvedka@hunt.service
sleep 2
journalctl -u papa-razvedka@hunt.service -f -n 0 -o cat &
J=$!
while systemctl is-active -q papa-razvedka@hunt.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@hunt.service)" == activating ]]; do sleep 5; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value papa-razvedka@hunt.service)"
echo "3/4 в запас GENPLAN:"
install -d -o papa-genplan -g papa-genplan -m 0700 "$POOL"
[[ -f "$OUT/index.jsonl" ]] && cp "$OUT/index.jsonl" "$POOL/index.jsonl"
[[ -f "$OUT/examples.json" ]] && cp "$OUT/examples.json" "$POOL/examples.json"
chown -R papa-genplan:papa-genplan "$POOL"; chmod -R u+rwX,go-rwx "$POOL"
echo "  видео в пуле для проверки: $(wc -l < "$POOL/index.jsonl" 2>/dev/null || echo 0)"
echo "4/4 утро на завтра пересобирается (новые видео + новый текст):"
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
sys.path.insert(0, "/opt/papa/modules/genplan")
from genplan import store
store.connect(sys.argv[1]).close()          # миграции (новые колонки) до сброса
db = sqlite3.connect(sys.argv[1])
n = db.execute("UPDATE fixed_posts SET prepared=0, redo=1, tries=0, next_try=NULL, hub_msg=NULL, preview_sent=0, approved=0 "
               "WHERE status='pending' AND substr(at,1,16)>strftime('%Y-%m-%dT%H:%M','now','+5 hours')").rowcount
db.commit(); print(f"  постов на пересборку: {n}")
PY
systemctl start papa-fabrika; sleep 240
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
print("  проверка кадров (Gemini):", dict(db.execute("SELECT status, count(*) FROM morning_pool GROUP BY status").fetchall()))
print("  годные по дням:", dict(db.execute("SELECT coalesce(weekday,'общие'), count(*) FROM morning_pool WHERE status='ok' GROUP BY 1").fetchall()))
for r in db.execute("SELECT reason, count(*) FROM morning_pool WHERE status='rejected' GROUP BY 1 ORDER BY 2 DESC LIMIT 5"):
    print("  отбраковано:", *r)
for r in db.execute("SELECT channel, key, substr(at,12,5), prepared, coalesce(source,'') FROM fixed_posts "
                    "WHERE substr(at,1,16)>strftime('%Y-%m-%dT%H:%M','now','+5 hours','-1 hour') ORDER BY at, channel"):
    print("  ", *r)
PY
journalctl -u papa-fabrika -n 4 --no-pager -o cat
echo "== MORNING_HUNT_DONE (проверка кадров продолжается сама; предпросмотры — в боте)"
