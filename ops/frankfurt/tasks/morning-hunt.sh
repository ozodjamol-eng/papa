#!/usr/bin/env bash
# 🌅 Охота за готовыми утренними видео («Жума тонги», «Хайрли тонг»…) в каналах Разведки и NEXUS MORNING POOL →
# запас GENPLAN (Fabrika проверяет кадры через Gemini: даты, чужие логотипы) → утро на завтра пересобирается
# (новые видео + длинный тёплый ИИ-текст), предпросмотр придёт в бот. Только чтение каналов.
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
OUT=/var/lib/papa-razvedka-pub/morning
POOL=/var/lib/papa-genplan/pool
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN: Разведка не авторизована"; exit 1; }
free=$(df --output=avail -BM /var/lib | tail -1 | tr -dc 0-9)
(( free > 3000 )) || { echo "МАЛО МЕСТА: свободно ${free} МБ, нужно 3000"; exit 1; }
if systemctl is-active -q papa-razvedka@collect.service || systemctl is-active -q papa-razvedka@run.service; then
  echo "Сейчас идёт сбор Разведки — повторите через 10 минут"; exit 1
fi
cp -a "$DB" "$DB.bak-hunt-$(date +%F-%H%M)"
echo "1/4 код и тесты:"
( cd /opt/papa/modules/genplan && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
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
n=0
for f in "$OUT"/*.mp4; do
  [[ -e "$f" ]] || continue
  mv -n "$f" "$POOL/"; n=$((n+1))
done
rm -f "$OUT"/*.mp4
[[ -f "$OUT/index.jsonl" ]] && cp "$OUT/index.jsonl" "$POOL/index.jsonl"
[[ -f "$OUT/examples.json" ]] && cp "$OUT/examples.json" "$POOL/examples.json"
chown -R papa-genplan:papa-genplan "$POOL"; chmod -R u+rwX,go-rwx "$POOL"
echo "  перенесено видео: $n · в запасе: $(ls "$POOL"/*.mp4 2>/dev/null | wc -l) · занято: $(du -sh "$POOL" | cut -f1)"
echo "4/4 утро на завтра пересобирается (новые видео + новый текст):"
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
n = db.execute("UPDATE fixed_posts SET prepared=0, redo=1, tries=0, next_try=NULL, hub_msg=NULL, preview_sent=0 "
               "WHERE status='pending' AND day=date('now','+5 hours','+1 day')").rowcount
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
                    "WHERE day=date('now','+5 hours','+1 day') ORDER BY at, channel"):
    print("  ", *r)
PY
journalctl -u papa-fabrika -n 4 --no-pager -o cat
echo "== MORNING_HUNT_DONE (проверка кадров продолжается сама; предпросмотры — в боте)"
