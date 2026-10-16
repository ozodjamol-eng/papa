#!/usr/bin/env bash
# 📡 Агент-куратор: тесты → обновлённый шаблон Разведки (+ключ Gemini для проверки кадров) → GENPLAN (источник в карточке,
# вечерний отчёт 21:30) → таймер 08:00 / 12:30 / 17:00 → первый запуск сейчас.
# Откат: systemctl disable --now papa-curator.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
run_curate(){
  systemctl start --no-block papa-razvedka@curate.service; sleep 2
  journalctl -u papa-razvedka@curate.service -f -n 0 -o cat & J=$!
  while systemctl is-active -q papa-razvedka@curate.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@curate.service)" == activating ]]; do sleep 3; done
  sleep 1; kill $J 2>/dev/null || true
  echo "результат: $(systemctl show -p Result --value papa-razvedka@curate.service)"
}
echo "1/4 тесты:"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
echo "2/4 службы:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /opt/papa/ops/frankfurt/systemd/papa-curator.timer /etc/systemd/system/
systemctl daemon-reload
systemctl restart papa-genplan; sleep 3; echo "  papa-genplan: $(systemctl is-active papa-genplan)"
systemctl enable -q --now papa-curator.timer
echo "  таймер: $(systemctl list-timers papa-curator.timer --no-pager --no-legend 2>/dev/null | cut -c1-40 || true)"
echo "3/4 первый запуск куратора (2–6 минут):"
run_curate
echo "4/4 готово: карточки «📡 Куратор нашёл» — в пультах КАТТА ДАВРА и PaparazziUZ"
echo "== CURATOR_INSTALL_DONE"
