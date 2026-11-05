#!/usr/bin/env bash
# ⚡ 05.11 владелец: «срочные, актуальные, не политика — надо делать». Разведка дважды в час ищет срочное полезное
# (свет/газ/вода, дороги, курс/бензин, выходные, погодные предупреждения, мошенники) в папке «XOJAOBOD CITY» и выбранных
# источниках → пересылает в пульт Хўжаобода → карточка «⚡ МУҲИМ»: 🆘 сразу / 🗑. Не больше 3 в день. Сам не публикует.
# Откат: systemctl disable --now papa-muhim.timer
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
echo "1/4 тесты:"
( cd /opt/papa/modules/razvedka && $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
echo "2/4 пульт (papa-genplan) — перезапуск с карточкой ⚡ МУҲИМ:"
systemctl restart papa-genplan; sleep 5; echo "  papa-genplan: $(systemctl is-active papa-genplan)"
echo "3/4 таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-muhim.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-muhim.timer
echo "  $(systemctl list-timers papa-muhim.timer --no-pager --no-legend 2>/dev/null | cut -c1-60 || true)"
echo "4/4 первый поиск сейчас (1–5 минут):"
if systemctl is-active -q papa-razvedka@curate.service; then echo "  куратор сейчас работает — первый поиск по таймеру"; else
  systemctl start --no-block papa-razvedka@muhim.service; sleep 2
  journalctl -u papa-razvedka@muhim.service -f -n 0 -o cat & J=$!
  for i in $(seq 1 100); do
    st=$(systemctl show -p ActiveState --value papa-razvedka@muhim.service)
    [[ "$st" == active || "$st" == activating ]] || break; sleep 3; done
  sleep 1; kill $J 2>/dev/null || true
  echo "  результат: $(systemctl show -p Result --value papa-razvedka@muhim.service)"
fi
echo "== MUHIM_INSTALL_DONE"
