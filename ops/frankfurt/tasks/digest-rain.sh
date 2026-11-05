#!/usr/bin/env bash
# 🌧 05.11 владелец: «дайджест надо делать с дождиком». Отметка «сегодня дождь» → GENPLAN в 19:50 берёт для
# «Кечки дайжест» (оба канала) дождливый фон из «PAPA ВЕЧЕР ПУЛ». Цифры погоды не трогает (они — из прогноза).
# Ничего не публикует. Откат: rm /var/lib/papa-evening/rain-<дата>. Без отметки дождь ловится и сам — по прогнозу 16–21 ч.
set -Eeuo pipefail
D=/var/lib/papa-evening
[[ -d "$D" ]] || { echo "❌ нет $D — вечерний пул не установлен (задача evening-install)"; exit 1; }
DAY=$(TZ=Asia/Tashkent date +%F)
find "$D" -maxdepth 1 -name 'rain-*' ! -name "rain-$DAY" -delete
echo "owner $(date -u +%FT%TZ)" > "$D/rain-$DAY"
chown papa-razvedka:papa-genplan "$D/rain-$DAY"; chmod 640 "$D/rain-$DAY"
echo "🌧 отметка: $D/rain-$DAY"
if [[ -f "$D/tags.json" ]]; then
  /opt/papa-venv/razvedka/bin/python - "$D" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); t = json.loads((d / "tags.json").read_text(encoding="utf-8"))
wet = [k for k, v in t.items() if any(w in v.lower() for w in ("rain", "ёмғир", "yomg'ir", "дожд")) and (d / k).exists()]
print(f"дождливых фонов в пуле: {len(wet)}" + ("" if wet else " — доберёт вечерний агент в 15:30"))
PY
else
  echo "метки фонов появятся после прогона вечернего агента (15:30) — он же доберёт дождливые видео"
fi
echo "== DIGEST_RAIN_DONE"
