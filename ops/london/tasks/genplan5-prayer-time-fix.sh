#!/usr/bin/env bash
# GENPLAN 5 (Хўжаобод): время намаза принимается в любом виде — 19:10, 19 10, 19.10, 19-10, 19,10, 1910.
# Меняется ОДНА строка (_TIME_RE в prayer.py). Резервная копия; проверка, что результат разбора совпадает с «19:10»;
# тесты намаза; перезапуск. Любая ошибка → автооткат.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; F=$D/genplan_v3/prayer.py; SVC=xojaobod-genplan-v3.service
PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
cd "$D" || { echo NO_DIR; exit 1; }
B="$F.bak-$(date +%F-%H%M%S)"; cp -a "$F" "$B"; echo "копия: $B"
rollback() { cp -a "$B" "$F"; systemctl restart "$SVC"; echo "!! ОТКАТ: $1 — всё возвращено как было"; exit 1; }

"$PY" - "$F" <<'P' || rollback "строка не найдена"
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
old = '_TIME_RE = re.compile(r"(\\d{1,2})[:.](\\d{2})")'
new = '_TIME_RE = re.compile(r"(?<!\\d)(\\d{1,2})\\s*[:.\\-,;\\s]?\\s*(\\d{2})(?!\\d)")  # PAPA 2026-10-15: 19:10 / 19 10 / 19.10 / 19-10 / 1910'
if old not in s:
    sys.exit("old regex not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("строка заменена")
P

"$PY" - <<'P' || rollback "проверка разбора не прошла"
import re
from genplan_v3 import prayer
base = "Намоз вақтлари: 15.10.2026\nБомдод {0}\nПешин {1}\nАср {2}\nШом {3}\nХуфтон {4}"
times = [("05", "45"), ("12", "45"), ("16", "00"), ("17", "45"), ("19", "10")]
ref = repr(prayer.parse_bulk_schedule_text(base.format(*[f"{h}:{m}" for h, m in times])))
for sep in [" ", ".", "-", ",", "", " : ", " . "]:
    got = repr(prayer.parse_bulk_schedule_text(base.format(*[f"{h}{sep}{m}" for h, m in times])))
    assert got == ref, f"разделитель «{sep}» разобран иначе"
    print(f"  ок: 19{sep}10")
print("ПРОВЕРКА OK")
P

"$PY" -m py_compile "$F" || rollback "ошибка синтаксиса"
if [[ -d tests ]]; then
  out=$("$PY" -m unittest discover -t . -s tests -k prayer -k namaz 2>&1 | tail -3); echo "$out"
  echo "$out" | grep -qE "^OK|NO TESTS RAN|Ran 0 tests" || rollback "тесты намаза"
fi
systemctl restart "$SVC"; sleep 6
systemctl is-active --quiet "$SVC" || rollback "служба не поднялась"
echo "служба: $(systemctl is-active $SVC)"
echo "== PRAYER_FIX_DONE"
