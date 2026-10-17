#!/usr/bin/env bash
# Сравнение ИИ-текста: Haiku vs Sonnet на 5 последних постах из пультов. Ничего не публикует и не меняет (~10 центов).
set -uo pipefail
cd /opt/papa/modules/genplan || exit 1
set -a; . /etc/papa-genplan/genplan.env; . /etc/papa-genplan/ai.env; set +a
/opt/papa-venv/razvedka/bin/python - <<'P'
import json, os, sqlite3, tomllib
from genplan import ai, text
cfg = tomllib.load(open("config.toml", "rb"))
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True); db.row_factory = sqlite3.Row
cols = {r[1] for r in db.execute("PRAGMA table_info(materials)")}
rows = db.execute("SELECT * FROM materials WHERE length(text) > 120 AND channel IS NOT NULL "
                  "AND lower(coalesce(rubric,'')) NOT LIKE 'реклама%' ORDER BY id DESC LIMIT 5").fetchall()
for i, m in enumerate(rows, 1):
    ch = cfg["channels"].get(m["channel"], {})
    junk = json.loads(m["junk"] or "[]") if "junk" in cols else []
    src = text.strip_sources(text.drop_lines(m["text"], junk))
    system = ai.SYSTEM.format(title=ch.get("title", ""))
    print(f"\n===== {i}. {ch.get('title', m['channel'])} · рубрика: {m['rubric']} =====")
    print("— ИСХОДНИК:\n" + src[:600])
    for name, model in (("HAIKU", "claude-haiku-5-5"), ("SONNET", "claude-sonnet-5-5")):
        ai.MODEL = model
        try:
            out = ai._claude(system, f"Манба матни:\n\n{src[:4000]}")
        except Exception as e:
            out = f"(ошибка: {type(e).__name__} {e})"
        print(f"— {name}:\n{out or '(пусто)'}")
print("\n== AI_COMPARE_DONE")
P
