#!/usr/bin/env bash
# 📊 Отчёт Разведки картинками (18.10, владелец: «как в Excel, по пунктам»).
# Ставит Pillow в окружение Разведки, проверяет тесты и сразу шлёт сегодняшний отчёт
# 4 картинками в «PAPA ОТЧЁТЫ». Каналы аудитории не трогает. Расход $0.
# Откат: report_format = "text" в modules/razvedka/config.toml.
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
$PY -m pip install -q -r /opt/papa/modules/razvedka/requirements.txt
echo "Pillow $($PY -c 'import PIL; print(PIL.__version__)')"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl start papa-razvedka@send.service
journalctl -u papa-razvedka@send.service -n 200 -o cat --no-pager | grep -E "CARDS_|REPORT_|FAIL" | tail -5
echo "== RAZVEDKA_CARDS_DONE"
