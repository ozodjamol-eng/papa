#!/usr/bin/env bash
# 🕊 История канала ХОТИРА (тексты и фото) → база повторов бота (профиль Разведки читает канал, ничего не публикует). Повторять можно.
set -euo pipefail
set -a; . /etc/papa-razvedka/telegram.env; . /etc/papa-xotira/xotira.env; set +a
export XOTIRA_DB=/var/lib/papa-xotira/xotira.sqlite3
# 21.10: модель узнавания лица SFace int8 (OpenCV Zoo, бесплатно, ~10 МБ) — один раз, с проверкой суммы
M=/var/lib/papa-xotira/models/face_recognition_sface_2021dec_int8.onnx || true
SHA=2b0e941e6f16cc048c20aee0c8e31f569118f65d702914540f7bfdc14048d78a
if [[ ! -f $M ]] || ! echo "$SHA  $M" | sha256sum -c --quiet; then
  mkdir -p "$(dirname $M)"
  curl -fsSL --retry 3 -o "$M.tmp" https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec_int8.onnx || true
  echo "$SHA  $M.tmp" | sha256sum -c --quiet && mv "$M.tmp" "$M" && echo "модель лица: скачана ✅" || { rm -f "$M.tmp"; echo "модель лица: сумма не сошлась ❌"; }
fi
export XOTIRA_FACE_MODEL=$M
nice -n 19 /opt/papa-venv/razvedka/bin/python /opt/papa/ops/frankfurt/xotira_scan.py
# 21.10: отпечатки фото канала (OpenCV из venv бота) + отчёт о повторах, уже попавших в канал
[[ -x /opt/papa-venv/xotira/bin/python ]] && nice -n 19 /opt/papa-venv/xotira/bin/python /opt/papa/ops/frankfurt/xotira_prints.py 2>&1 | grep -v "WARN"
chown -R papa-xotira:papa-xotira /var/lib/papa-xotira
echo "== XOTIRA_SCAN_DONE"
