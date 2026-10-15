#!/usr/bin/env bash
# 📁 Сортировка каналов владельца по трём НОВЫМ папкам-назначениям: «P→Давра», «P→Paparazzi», «P→Хўжаобод».
# Профиль Разведки (= профиль владельца) читает свои каналы, Gemini определяет тему каждого, агент создаёт папки.
# Старые папки не трогаются. Отчёт — в «Избранное» профиля. Разрешение владельца — 16.10 01:26.
# Откат: удалить три папки в Telegram (Настройки → Папки) — каналы остаются на месте.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
if systemctl is-active -q papa-razvedka@collect.service || systemctl is-active -q papa-razvedka@run.service \
   || systemctl is-active -q papa-razvedka@hunt.service; then
  echo "Сейчас работает Разведка — повторите через 10 минут"; exit 1
fi
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
set -a; . /etc/papa-razvedka/telegram.env; . /etc/papa-genplan/ai.env; set +a
export PAPA_RAZVEDKA_PUB=/var/lib/papa-razvedka-pub PYTHONUNBUFFERED=1
echo "Сортирую (10–20 минут: читаю каналы, ИИ определяет темы)…"
( cd /opt/papa/modules/razvedka && $PY -m razvedka sort-folders )
chown -R papa-razvedka /var/lib/papa-razvedka-pub/morning 2>/dev/null || true
echo "Полный список — в «Избранном» вашего Telegram."
echo "== FOLDERS_SORT_DONE"
