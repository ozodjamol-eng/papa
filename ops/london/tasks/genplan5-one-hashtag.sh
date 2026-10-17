#!/usr/bin/env bash
# GENPLAN 5 (Хўжаобод): правило владельца — в посте ОДИН хэштег (первый, т.е. выбранный рубрикой) или ни одного.
# Повод 17.10: пост «Саломатлик» вышел с #САЛОМАТЛИК #ТИББИЁТ (второй тег был в тексте автора, GENPLAN 5 его не трогал).
# Меняется только hook_policy.py: функция _one_hashtag + вызов перед сборкой итоговой подписи. Реклама не трогается.
# Резервная копия; проверка на примерах; тесты; перезапуск. Любая ошибка → автооткат.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; F=$D/genplan_v3/hook_policy.py; SVC=xojaobod-genplan-v3.service
PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
cd "$D" || { echo NO_DIR; exit 1; }
grep -q "def _one_hashtag" "$F" && { echo "уже установлено"; echo "== ONE_HASHTAG_DONE"; exit 0; }
B="$F.bak-$(date +%F-%H%M%S)"; cp -a "$F" "$B"; echo "копия: $B"
rollback() { cp -a "$B" "$F"; systemctl restart "$SVC"; echo "!! ОТКАТ: $1 — всё возвращено как было"; exit 1; }

"$PY" - "$F" <<'P' || rollback "место вставки не найдено"
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_bytes().decode("utf-8")
nl = "\r\n" if "\r\n" in s else "\n"
old = '    return "\\n\\n".join(x for x in (top, body, handle, bottom) if x)'
if s.count(old) != 1:
    sys.exit("return line not found exactly once")
new = ('    out = "\\n\\n".join(x for x in (top, body, handle, bottom) if x)' + nl +
       '    return out if kind == "ad" else _one_hashtag(out)  # PAPA 2026-10-17: один хэштег' )
s = s.replace(old, new, 1)
func = r'''

# PAPA 2026-10-17: правило владельца — один хэштег по смыслу (первый) или ни одного.
_ONE_TAG = re.compile(r"#([\wЀ-ӿ]+)")
def _one_hashtag(text):
    tags = _ONE_TAG.findall(text or "")
    if len(tags) <= 1:
        return text
    seen = [False]
    def sub_line(line):
        if not _ONE_TAG.search(line):
            return line
        only_tags = not _ONE_TAG.sub("", line).strip(" \t,.;|")
        def rep(m):
            if not seen[0]:
                seen[0] = True
                return m.group(0)
            return "" if only_tags else m.group(1).replace("_", " ")
        new = _ONE_TAG.sub(rep, line)
        if not only_tags:
            return new
        new = re.sub(r"[ \t]{2,}", " ", new).strip(" \t,;|")
        return new or None
    lines = [sub_line(l) for l in text.split("\n")]
    out = "\n".join(l for l in lines if l is not None)
    return re.sub(r"\n{3,}", "\n\n", out).strip()
'''.replace("\n", nl)
p.write_bytes((s.rstrip() + func).encode("utf-8"))
print("вставлено")
P

"$PY" - <<'P' || rollback "проверка на примерах не прошла"
from genplan_v3.hook_policy import _one_hashtag as f
a = "Матн бошланиши.\n\n#САЛОМАТЛИК #ТИББИЁТ\n\nБуни уй шароитида даволаш"
r = f(a); print(repr(r))
assert r.count("#") == 1 and "#САЛОМАТЛИК" in r and "ТИББИЁТ" not in r and "Буни уй" in r
b = "#ЯНГИЛИК\nМатн #Андижон шаҳрида\n#ДУНЁ #ХАБАР"
r = f(b); print(repr(r))
assert r.count("#") == 1 and r.startswith("#ЯНГИЛИК") and "Андижон шаҳрида" in r and "ДУНЁ" not in r
assert f("Битта #ТЕГ бор") == "Битта #ТЕГ бор" and f("Тегсиз матн") == "Тегсиз матн"
print("ПРОВЕРКА OK")
P

"$PY" -m py_compile "$F" || rollback "ошибка синтаксиса"
if [[ -d tests ]]; then
  out=$(timeout 600 "$PY" -m unittest discover -t . -s tests -k hook -k footer -k hashtag 2>&1 | tail -4); echo "$out"
  echo "$out" | grep -qE "^OK|NO TESTS RAN|Ran 0 tests" || rollback "тесты подписи/хэштегов"
fi
systemctl restart "$SVC"; sleep 6
systemctl is-active --quiet "$SVC" || rollback "служба не поднялась"
echo "служба: $(systemctl is-active $SVC)"
echo "== ONE_HASHTAG_DONE"
