#!/usr/bin/env bash
# 🤖 ИИ-ассистент: диагностика (только чтение). Служба, последние записи журнала, подключение Business и счётчики.
# Токен и тексты переписки не печатаются.
set -uo pipefail
echo "служба: $(systemctl is-active papa-assistant) (с $(systemctl show -p ActiveEnterTimestamp --value papa-assistant))"
echo "== журнал (последние 25):"
journalctl -u papa-assistant -n 25 --no-pager -o short-iso | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g'
DB=/var/lib/papa-assistant/assistant.sqlite3
echo "== база:"
python3 - "$DB" <<'PY'
import sqlite3, sys, datetime as dt
try:
    db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
except Exception as e:
    sys.exit(f"нет базы: {e}")
conns = db.execute("SELECT owner, owner_chat, enabled FROM conn").fetchall()
print(f"подключений Business: {len(conns)}" + "".join(f"\n  владелец {o} · чат уведомлений {'есть' if oc else 'НЕТ'} · {'включено' if en else 'ВЫКЛЮЧЕНО'}" for o, oc, en in conns))
rows = db.execute("SELECT replied_at, owner_at, kind FROM chats").fetchall()
now = dt.datetime.now(dt.timezone.utc)
rep = [r for r in rows if r[0]]
last = max((r[0] for r in rep), default=None)
print(f"чатов в базе: {len(rows)} · ассистент ответил: {len(rep)} (последний ответ: {last or '—'})")
print(f"за 24 ч: ответов {sum(1 for r in rep if now - dt.datetime.fromisoformat(r[0]) < dt.timedelta(hours=24))}, "
      f"чатов, где писали вы сами (бот молчит): {sum(1 for r in rows if r[1] and now - dt.datetime.fromisoformat(r[1]) < dt.timedelta(hours=24))}")
PY
echo "== ASSISTANT_STATUS_DONE"
