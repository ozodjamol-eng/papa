# Опись GENPLAN 5 для переезда в PAPA. Только чтение: ничего не меняет, секреты не выводит (только имена настроек).
set -uo pipefail
G=/opt/xojaobod-genplan-v5
DB=$G/data/genplan_v3_production.db
echo "== служба"; systemctl show xojaobod-genplan-v3 -p ExecStart -p WorkingDirectory -p EnvironmentFiles --no-pager | sed 's/;.*//' | cut -c1-160
echo "== файлы кода"; find "$G" -maxdepth 2 -name '*.py' -not -path '*/venv/*' -not -path '*/.venv/*' -printf '%s\t%p\n' 2>/dev/null | sort -k2 | head -40
echo "== настройки (только имена)"; for f in "$G/.env" "$G/config.env"; do [[ -r $f ]] && { echo "$f:"; grep -oE '^[A-Z_][A-Z0-9_]*=' "$f" | tr -d '=' | tr '\n' ' '; echo; }; done
echo "== таблицы и строки"
python3 - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for (name, sql) in db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    cols = [r[1] for r in db.execute(f'PRAGMA table_info("{name}")')]
    print(f"{name} ({n}): {', '.join(cols)}")
PY
echo "== рубрики, слоты, время (из кода)"
grep -rhoE '^(RUBRICS|SLOTS|AD_WINDOWS|AD_SLOTS|ANCHORS|SCHEDULE|DAILY_[A-Z_]*|[A-Z_]*TIME[A-Z_]*|[A-Z_]*SLOT[A-Z_]*)\s*=.{0,160}' --include='*.py' "$G" 2>/dev/null | grep -v -iE 'token|key|secret|pass' | sort -u | head -40
echo "== каналы и чаты в базе"
python3 - "$DB" <<'PY'
import re, sqlite3, sys
SECRET = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}|token|secret|passw|api_?key|hash", re.I)
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for t in ("channels", "chats", "settings"):
    try:
        for r in db.execute(f'SELECT * FROM "{t}" LIMIT 10'):
            row = [str(x)[:60] for x in r]
            print(t, "[скрыто]" if SECRET.search(" ".join(row)) else row)
    except sqlite3.Error:
        pass
PY
echo "== GENPLAN_INVENTORY_DONE"
