#!/usr/bin/env bash
# GENPLAN 5 (Хўжаобод), решение владельца 17.10: внизу поста — текст → наша фирменная подпись (@XOJAOBODCITY24) → хук ПО СМЫСЛУ (ИИ Anthropic).
# Старый авто-вопрос «…эмодзи реакция билан билдиринг» больше не ставится. Нет мысли / грустная тема / ИИ недоступен — без хука.
# Реклама, намаз и религиозное (protected) не трогаются. Включается только флагом PAPA_AI_HOOKS=1 (его ставит genplan5-ai-key),
# поэтому старые тесты идут по старой логике. Копия; проверка; тесты; перезапуск. Любая ошибка → автооткат.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; F=$D/genplan_v3/hook_policy.py; SVC=xojaobod-genplan-v3.service
PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
cd "$D" || { echo NO_DIR; exit 1; }
grep -q "def _papa_hook" "$F" && { echo "уже установлено"; echo "== AI_HOOK_PATCH_DONE"; exit 0; }
grep -q "def _one_hashtag" "$F" || { echo "сначала нужна правка genplan5-one-hashtag"; exit 1; }
B="$F.bak-$(date +%F-%H%M%S)"; cp -a "$F" "$B"; echo "копия: $B"
rollback() { cp -a "$B" "$F"; systemctl restart "$SVC"; echo "!! ОТКАТ: $1 — всё возвращено как было"; exit 1; }

"$PY" - "$F" <<'P' || rollback "место вставки не найдено"
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_bytes().decode("utf-8")
nl = "\r\n" if "\r\n" in s else "\n"
old = '    out = "\\n\\n".join(x for x in (top, body, handle, bottom) if x)'
if s.count(old) != 1:
    sys.exit("compose join not found exactly once")
ins = ('    if _papa_on() and kind not in ("protected", "ad") and handle.casefold() == "@xojaobodcity24":  # PAPA 17.10' + nl +
       '        body = "\\n".join(l for l in body.split("\\n") if l.strip() not in _PAPA_SIGS).strip()' + nl +
       '        handle, bottom = _papa_sig(body), _papa_hook(body)' + nl)
s = s.replace(old, ins + old, 1)
func = r'''

# PAPA 2026-10-17: фирменная подпись + хук по смыслу текста (Anthropic). Включается PAPA_AI_HOOKS=1.
import os as _os, json as _json, hashlib as _hl, urllib.request as _ur
_PAPA_SIGS = ("📍 Хўжаободдаги энг тезкор хабарлар 👉 @XOJAOBODCITY24",
              "🏘 Хўжаобод ҳаёти — ҳар куни биз билан 👉 @XOJAOBODCITY24",
              "📢 Хўжаобод янгиликлари биринчи бўлиб 👉 @XOJAOBODCITY24")
_PAPA_HOOK_SYSTEM = """Сен — «XO'JAOBOD CITY 24» Telegram-гуруҳи муҳарририсан. Пост матнини ўқиб, унинг остига битта қисқа ЯКУНИЙ ҚАТОР ёз.
Қоидалар:
- Фақат ўзбек тилида, КИРИЛЛ алифбосида. Бир қатор, 70 белгидан ошмасин, бошида 1 та мос эмодзи.
- Қатор айнан шу пост мазмунига мос бўлсин: шеър — шеърга, рецепт — рецептга, янгилик — янгиликка, ҳазил — ҳазилга.
- Мақсад — ўқувчини жонли ҳаракатга ундаш: дўстларига улашиш, сақлаб қўйиш ёки реакция қолдириш. Биттасини танла, мазмунга энг мосини.
- Шаблон сўзлар йўқ: «эмодзи реакция билан билдиринг», «Шундай усулдан фойдаланганмисиз» каби қуруқ, роботга ўхшаш гаплар ТАҚИҚЛАНГАН.
- Мазмунга мос бўлмаган савол берма. Ҳар доим ҳам савол шарт эмас.
- @юзернейм, ҳавола, хэштег ёзма. Изоҳ ёзишни сўрама.
- Хабар қайғули бўлса (вафот, фожиа, авария, касаллик хабари) ёки мос қатор топилмаса — фақат битта сўз қайтар: ЙЎҚ.
Фақат тайёр қаторни қайтар, изоҳсиз."""


def _papa_on():
    return _os.environ.get("PAPA_AI_HOOKS") == "1"


def _papa_sig(body):
    return _PAPA_SIGS[int(_hl.md5((body or "").encode("utf-8")).hexdigest(), 16) % len(_PAPA_SIGS)]


def _papa_hook(body, http=None):
    key = _os.environ.get("ANTHROPIC_API_KEY")
    if not key or not (body or "").strip():
        return ""
    req = _ur.Request("https://api.anthropic.com/v1/messages", data=_json.dumps({
        "model": _os.environ.get("AI_MODEL", "claude-haiku-5-5"), "max_tokens": 120, "system": _PAPA_HOOK_SYSTEM,
        "messages": [{"role": "user", "content": "Пост матни:\n\n" + body[:2500]}]}).encode("utf-8"),
        headers={"content-type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": key})
    try:
        data = http(req) if http else _json.loads(_ur.urlopen(req, timeout=25).read())
        out = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    except Exception:
        return ""
    line = next((l.strip() for l in out.splitlines() if l.strip()), "")
    if not line or line.upper().strip(" .!") in ("ЙЎҚ", "YO'Q", "YOQ", "НЕТ") or len(line) > 110 or "@" in line or "#" in line:
        return ""
    return line
'''.replace("\n", nl)
p.write_bytes((s.rstrip() + func).encode("utf-8"))
print("вставлено")
P

"$PY" - <<'P' || rollback "проверка на примерах не прошла"
import os
from genplan_v3 import hook_policy as h
fake = lambda ans: (lambda req: {"content": [{"type": "text", "text": ans}]})
os.environ["ANTHROPIC_API_KEY"] = "x"
assert h._papa_hook("Жуда чиройли шеър", fake("📖 Шеър ёққан бўлса, яқинларингизга ҳам юборинг!")).startswith("📖")
assert h._papa_hook("Вафот этди", fake("ЙЎҚ")) == ""
assert h._papa_hook("Матн", fake("Обуна бўлинг @kanal")) == ""
assert h._papa_sig("a") in h._PAPA_SIGS
del os.environ["ANTHROPIC_API_KEY"]
assert h._papa_hook("Матн") == ""          # без ключа — без хука
print("ПРОВЕРКА OK")
P

"$PY" -m py_compile "$F" || rollback "ошибка синтаксиса"
if [[ -d tests ]]; then
  out=$(timeout 600 env -u PAPA_AI_HOOKS "$PY" -m unittest discover -t . -s tests -k hook -k footer -k hashtag 2>&1 | tail -4); echo "$out"
  echo "$out" | grep -qE "^OK|NO TESTS RAN|Ran 0 tests" || rollback "тесты подписи/хуков"
fi
systemctl restart "$SVC"; sleep 6
systemctl is-active --quiet "$SVC" || rollback "служба не поднялась"
echo "служба: $(systemctl is-active $SVC) (новая логика включится после genplan5-ai-key)"
echo "== AI_HOOK_PATCH_DONE"
