#!/usr/bin/env bash
# 🔎 Дежурный, шаг 1 (05.11, только чтение): почему в сетке пустые часы — куратор/склады, архивариус, лимит Gemini, запас.
set -uo pipefail
for u in curate archive sklad-latest; do
  echo "== papa-razvedka@$u: $(systemctl show -p ActiveState --value papa-razvedka@$u.service) · последний старт $(systemctl show -p ExecMainStartTimestamp --value papa-razvedka@$u.service) · $(systemctl show -p Result --value papa-razvedka@$u.service)"
done
for t in papa-curator papa-archive; do echo "$t.timer: $(systemctl is-active $t.timer) · следующий $(systemctl show -p NextElapseUSecRealtime --value $t.timer)"; done
echo "== куратор/склады за 24 ч: ошибки и лимиты"
journalctl -u papa-razvedka@curate.service --since "-24h" --no-pager -o cat | grep -iE "429|лимит|quota|gemini|error|ошибк|почти пуст|пропуск" | cut -c1-220 | sort | uniq -c | sort -rn | head -25
echo "== куратор: последние строки"
journalctl -u papa-razvedka@curate.service --since "-14h" --no-pager -o cat | grep -vE '^\s*$' | cut -c1-220 | tail -60
echo "== архивариус за 30 ч"
journalctl -u papa-razvedka@archive.service --since "-30h" --no-pager -o cat | grep -vE "^\s*$" | cut -c1-220 | tail -40
echo "== запас и материалы (база read-only)"
/opt/papa-venv/razvedka/bin/python - <<'PY'
import sqlite3, collections
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True); db.row_factory = sqlite3.Row
cols = {r[1] for r in db.execute("PRAGMA table_info(materials)")}
src = "source" if "source" in cols else "''"
print("материалы за 24 ч (канал · источник · статус):")
for r in db.execute(f"SELECT channel, {src} s, status, count(*) n FROM materials WHERE created_at >= datetime('now','-1 day') GROUP BY 1,2,3 ORDER BY 1, n DESC"):
    print("  ", r["channel"], "·", r["s"], "·", r["status"], ":", r["n"])
if "stock" in cols:
    print("запас (канал · рубрика):")
    for r in db.execute("SELECT channel, rubric, status, count(*) n FROM materials WHERE stock=1 GROUP BY 1,2,3 ORDER BY 1"):
        print("  ", r["channel"], "·", r["rubric"], "·", r["status"], ":", r["n"])
print("черновики за 24 ч (не в запасе, ждут выбора?):")
for r in db.execute(f"SELECT channel, rubric, {src} s, stock, auto, substr(coalesce(text,''),1,60) t FROM materials WHERE status='draft' AND created_at >= datetime('now','-1 day') ORDER BY id DESC LIMIT 25"):
    print("  ", dict(r))
PY
echo "== DEZHUR_DIAG_DONE"
