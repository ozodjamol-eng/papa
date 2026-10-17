#!/usr/bin/env bash
# GENPLAN 5 (Хўжаобод), схема хуков владельца 17.10:
#   новости / Ўзбекистон / Хўжаобод — без хука; музыка — наша реклама (по очереди);
#   полезное, соғлиқ, оила, маданият — короткий хук ИИ (до 50 знаков); юмор — готовые лёгкие хуки; грустное — без хука.
# Реклама, намаз, религиозное (protected) — без изменений. Копия; проверка; тесты; перезапуск. Любая ошибка → автооткат.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; F=$D/genplan_v3/hook_policy.py; SVC=xojaobod-genplan-v3.service
PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
cd "$D" || exit 1
grep -q "def _papa_bottom" "$F" && { echo "уже установлено"; echo "== HOOK_SCHEME_DONE"; exit 0; }
grep -q "def _papa_hook" "$F" || { echo "сначала нужна правка genplan5-ai-hook"; exit 1; }
B="$F.bak-$(date +%F-%H%M%S)"; cp -a "$F" "$B"; echo "копия: $B"
rollback() { cp -a "$B" "$F"; systemctl restart "$SVC"; echo "!! ОТКАТ: $1 — всё возвращено как было"; exit 1; }

"$PY" - "$F" <<'P' || rollback "место вставки не найдено"
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_bytes().decode("utf-8")
nl = "\r\n" if "\r\n" in s else "\n"
old = "handle, bottom = _papa_sig(body), _papa_hook(body)"
if s.count(old) != 1:
    sys.exit("call not found")
s = s.replace(old, "handle, bottom = _papa_sig(body), _papa_bottom(body, rubric, subtype)", 1)
o2 = "Бир қатор, 70 белгидан ошмасин"
if s.count(o2) != 1:
    sys.exit("prompt line not found")
s = s.replace(o2, "Бир қатор, ҚИСҚА: 50 белгидан ошмасин", 1)
func = r'''

# PAPA 2026-10-17: схема хуков владельца (рубрика → тип нижней строки).
_PAPA_PROMO = ("📣 Реклама учун: @Ozodjamol", "🎉 Бутун Ўзбекистон янгиликлари ва мусиқа — @kattadavrauz")
_PAPA_FUN = ("😂 Кулдингизми? Дўстларингизга ҳам юборинг!", "🤣 Кайфият учун — дўстларингизга улашинг!")
_PAPA_SAD = ("вафот", "фожиа", "марҳум", "ҳалок", "жаноза", "таъзия", "оламдан ўт", "қазо қил", "авария")


def _papa_bottom(body, rubric=None, subtype=None):
    low = (body or "").lower()
    if any(w in low for w in _PAPA_SAD):
        return ""
    rub = str(getattr(rubric, "value", rubric) or "").lower()
    sub = str(subtype or "").lower()
    n = int(_hl.md5((body or "").encode("utf-8")).hexdigest(), 16)
    if rub in ("news", "uzbekistan", "local", "xojaobod", "breaking") or sub.startswith("news"):
        return ""
    if "music" in rub or sub.startswith("music") or "musiqa" in sub or "xonanda" in sub or "tarona" in sub:
        return _PAPA_PROMO[n % len(_PAPA_PROMO)]
    if "entertain" in rub or sub.startswith("ent_") or "kulgili" in sub or "kongilochar" in sub:
        return _PAPA_FUN[n % len(_PAPA_FUN)]
    return _papa_hook(body)
'''.replace("\n", nl)
p.write_bytes((s.rstrip() + func).encode("utf-8"))
print("вставлено")
P

"$PY" - <<'P' || rollback "проверка на примерах не прошла"
import os
from genplan_v3 import hook_policy as h
h._papa_hook = lambda b: "AI"
assert h._papa_bottom("Тошкентда янги кўприк", "news", None) == ""
assert h._papa_bottom("Янги клип", "music_culture", "music_big_premiere") in h._PAPA_PROMO
assert h._papa_bottom("Латифа 😂", "entertainment", "ent_big_humor") in h._PAPA_FUN
assert h._papa_bottom("Бош оғриғи сабаблари", "useful", "video_big_sogliq") == "AI"
assert h._papa_bottom("Шифокор вафот этди", "useful", None) == ""
print("ПРОВЕРКА OK")
P

"$PY" -m py_compile "$F" || rollback "ошибка синтаксиса"
if [[ -d tests ]]; then
  out=$(timeout 600 env -u PAPA_AI_HOOKS "$PY" -m unittest discover -t . -s tests -k hook -k footer -k hashtag 2>&1 | tail -4); echo "$out"
  echo "$out" | grep -qE "^OK|NO TESTS RAN|Ran 0 tests" || rollback "тесты подписи/хуков"
fi
systemctl restart "$SVC"; sleep 6
systemctl is-active --quiet "$SVC" || rollback "служба не поднялась"
echo "служба: $(systemctl is-active $SVC)"
echo "== HOOK_SCHEME_DONE"
