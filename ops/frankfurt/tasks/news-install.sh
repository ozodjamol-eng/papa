#!/usr/bin/env bash
# 📰 14.11 (шаг 2 решения 09.11, владелец: «без новостей никуда — 3 раза в день, всё через банк»): агент новостей
# трижды в день кладёт ОДНУ лучшую свежую новость (чистый кадр + наш текст, без политики/криминала/грустного)
# в банк «СРОЧНО НОВОСТИ». Если владелец уже бросил свою свежую — агент не кладёт. Сам ничего не публикует:
# дальше прежний порядок (куратор → карточка с 🗑 в пульте → слот 07:40 / 13:00 / 19:00).
# Откат: systemctl disable --now papa-news.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
echo "1/3 тесты:"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
echo "2/3 таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-news.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-news.timer
echo "  $(systemctl list-timers papa-news.timer --no-pager --no-legend 2>/dev/null | cut -c1-60 || true)"
echo "3/3 пробный поиск сейчас (1–5 минут):"
systemctl start --no-block papa-razvedka@news.service; sleep 2
journalctl -u papa-razvedka@news.service -f -n 0 -o cat & J=$!
for i in $(seq 1 100); do
  st=$(systemctl show -p ActiveState --value papa-razvedka@news.service)
  [[ "$st" == active || "$st" == activating ]] || break; sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "  результат: $(systemctl show -p Result --value papa-razvedka@news.service)"
echo "== NEWS_INSTALL_DONE"
