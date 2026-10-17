#!/usr/bin/env bash
# Проверка (ничего не меняет, ~1 цент): какие хуки ИИ пишет для Хўжаобода на 3 примерах; при ошибке — её причина. Ключ не показывается.
set -uo pipefail
D=/opt/xojaobod-genplan-v5; PY=$D/venv/bin/python; [[ -x $PY ]] || PY=python3
[[ -s /etc/papa-genplan5/ai.env ]] || { echo "нет ключа"; exit 1; }
set -a; . /etc/papa-genplan5/ai.env; set +a
cd $D && "$PY" - <<'P'
import json, os, urllib.request, urllib.error
from genplan_v3 import hook_policy as h
samples = {
 "стихотворение": "❗️ Жуда чиройли шеър\n\nОнажоним, сиз борсиз — дунё мунаввар,\nСиз борсиз — қалбимда баҳор ҳар саҳар.",
 "здоровье": "Ошқозон оғриғи: ҳеч қачон ошқозонингизни кестиришга шошилманг! Соғлиғингиз — энг катта бойлигингиз. Озишнинг соғлом йўлини танланг.",
 "погода": "Дам олиш кунлари айрим ҳудудларда ҳаво ҳарорати +30 даражагача кўтарилиши кутилмоқда. Куртакларни четга суриб, табиат қўйнига чиқиш вақти келди!",
}
for name, body in samples.items():
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps({
        "model": os.environ.get("AI_MODEL", "claude-haiku-5-5"), "max_tokens": 120, "system": h._PAPA_HOOK_SYSTEM,
        "messages": [{"role": "user", "content": "Пост матни:\n\n" + body}]}).encode(),
        headers={"content-type": "application/json", "anthropic-version": "2023-06-01", "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        raw = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text").strip()
        print(f"{name}: ответ ИИ → {raw!r}")
        print(f"   итог хука → {h._papa_hook(body) or '(без хука)'}")
    except urllib.error.HTTPError as e:
        print(f"{name}: ОШИБКА {e.code} {e.read()[:200]!r}")
    except Exception as e:
        print(f"{name}: ОШИБКА {type(e).__name__}: {e}")
P
echo "== AI_TEST_DONE"
