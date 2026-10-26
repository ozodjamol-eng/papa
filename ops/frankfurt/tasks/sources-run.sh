#!/usr/bin/env bash
# 📡 Отбор каналов-источников — «белый список» (решение владельца 26.10). Только чтение: профиль Разведки читает все
# папки владельца за 7 дней, Gemini проверяет кадры на чужой логотип, таблица — владельцу в главный пульт.
# Ничего не публикует и не пересылает. 30–90 минут (бесплатный лимит Gemini). Откат не нужен.
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_sources 2>&1 | tail -1 )
for u in collect run curate hunt pain sources; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Сейчас работает Разведка ($u) — повторите позже"; exit 1; fi
done
systemctl start --no-block papa-razvedka@sources.service
echo "Отбор запущен в фоне — таблица придёт в главный пульт (30–90 мин)."
echo "Ход: journalctl -u papa-razvedka@sources.service -f"
echo "== SOURCES_STARTED"
