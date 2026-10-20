#!/usr/bin/env bash
# Переход Хўжаобода на PAPA (решение владельца 20.10): остановить GENPLAN 5, когда впереди нет постов владельца
# (намаз, реклама-кампании и Якуний ведёт уже PAPA).
# Копия базы → stop+disable службы и её таймеров. Бот XOJAOBODCITYAVTOPOST24 освобождается для PAPA.
# Откат: papa-update genplan5-start (Лондон) — 1 минута.
set -Eeuo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
NOW=$(TZ=Asia/Tashkent date +%H:%M)
P=$(python3 -c "import sqlite3,sys,datetime as d; db=sqlite3.connect(f'file:{sys.argv[1]}?mode=ro',uri=True); t=(d.datetime.utcnow()+d.timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%S'); print(db.execute(\"SELECT count(*) FROM scheduled_posts WHERE status='pending' AND substr(scheduled_at,1,10)=substr(?,1,10) AND scheduled_at>=? AND coalesce(source,'') NOT IN ('prayer','campaign','fixed')\",(t,t)).fetchone()[0])" "$DB")
[[ "$P" == "0" ]] || { echo "❌ На сегодня в GENPLAN 5 ещё $P поста владельца впереди — не останавливаю (сейчас $NOW)"; exit 1; }
B=/var/backups/genplan5-final-$(date +%Y%m%d-%H%M).db
python3 -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d)" "$DB" "$B"
echo "копия базы: $B ($(du -h "$B" | cut -f1))"
systemctl disable --now xojaobod-genplan-v3.service 2>&1 | tail -1 || true
for t in xojaobod-evening-digest.timer papa-genplan5-guard.timer; do systemctl disable --now "$t" 2>/dev/null && echo "таймер $t: выключен"; done
sleep 2
echo "GENPLAN 5: $(systemctl is-active xojaobod-genplan-v3.service)"
echo "== GENPLAN5_STOP_DONE"
