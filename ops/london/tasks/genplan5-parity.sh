#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: что GENPLAN 5 реально делает каждый день — чтобы при переходе в PAPA ничего не потерять.
set -uo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
python3 - "$DB" <<'PY' | sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g'
import sqlite3, sys, collections
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
print("== ПУБЛИКАЦИИ за 3 дня (время · тип · рубрика · источник · начало текста)")
for r in db.execute("""SELECT substr(l.actual_time,1,16) t, l.post_type, coalesce(l.rubric,'') rub, coalesce(p.source,'') src,
                       coalesce(p.slot_key,'') sk, substr(replace(coalesce(p.caption,''),char(10),' '),1,55) cap, l.result
                       FROM publication_log l LEFT JOIN scheduled_posts p ON p.id=l.scheduled_post_id
                       WHERE l.actual_time>='2026-10-17' ORDER BY l.actual_time"""):
    print("  ", " · ".join(str(x) for x in r))
print("== ВИДЫ (source/post_type) за 14 дней")
c = collections.Counter()
for r in db.execute("SELECT coalesce(p.source,'?') s, l.post_type pt FROM publication_log l LEFT JOIN scheduled_posts p ON p.id=l.scheduled_post_id WHERE l.actual_time>='2026-10-06'"):
    c[(r["s"], r["pt"])] += 1
for k, v in c.most_common(): print("  ", k, v)
print("== rules_config"); [print("  ", dict(r)) for r in db.execute("SELECT rule_name, value FROM rules_config")]
print("== channel_profiles"); [print("  ", dict(r)) for r in db.execute("SELECT * FROM channel_profiles")]
print("== рубрики с включением"); [print("  ", dict(r)) for r in db.execute("SELECT * FROM channel_rubric_settings")]
print("== footer_pools (имена пулов и сколько)"); [print("  ", dict(r)) for r in db.execute("SELECT pool_name, count(*) n, sum(enabled) on_ FROM footer_pools GROUP BY pool_name")]
print("== content_templates по рубрикам"); [print("  ", dict(r)) for r in db.execute("SELECT rubric, count(*) n FROM content_templates WHERE enabled=1 GROUP BY rubric")]
print("== system_cache ключи"); [print("  ", r[0]) for r in db.execute("SELECT DISTINCT cache_key FROM system_cache")]
PY
echo "== таймеры/службы GENPLAN 5"
systemctl list-timers --all --no-pager 2>/dev/null | grep -iE "xojaobod|genplan|nexus" | cut -c1-160
systemctl list-units --all --no-pager 2>/dev/null | grep -iE "xojaobod|genplan" | cut -c1-140
echo "== модули кода"
ls $G/genplan_v3/*.py | xargs -n1 basename | tr '\n' ' '; echo
echo "== GENPLAN5_PARITY_DONE"
