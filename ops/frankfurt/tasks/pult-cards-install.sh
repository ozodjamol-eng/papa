#!/usr/bin/env bash
# 📡 26.10 владелец: «каждый пульт — свой выбор». Карточки выбора источников и «склад почти пуст» — в пульт своего
# канала, а не в PAPA ШТАБ. Даёт Разведке ключи трёх пультов: /etc/papa-pult-bots.env (берутся из genplan.env и
# bots.env на сервере, в чат не попадают). В каналы ничего не публикует.
# Откат: rm /etc/papa-pult-bots.env (карточки вернутся в PAPA ШТАБ).
set -Eeuo pipefail
G=/etc/papa-genplan/genplan.env
B=/etc/papa-genplan/bots.env
get(){ grep -shE "^$1=" "$2" | tail -1 | cut -d= -f2- | tr -d '"'"'"; }
D=$(get GENPLAN_BOT_TOKEN "$G"); P=$(get PAPARAZZI_BOT_TOKEN "$B"); X=$(get XOJAOBOD_BOT_TOKEN "$B")
[[ -n "$P" ]] || P=$(get PAPARAZZI_BOT_TOKEN "$G"); [[ -n "$X" ]] || X=$(get XOJAOBOD_BOT_TOKEN "$G")
( umask 027
  { [[ -n "$D" ]] && echo "PULT_TOKEN_davra=$D"; [[ -n "$P" ]] && echo "PULT_TOKEN_paparazzi=$P"
    [[ -n "$X" ]] && echo "PULT_TOKEN_xojaobod=$X"; true; } > /etc/papa-pult-bots.env )
chown root:papa-razvedka /etc/papa-pult-bots.env; chmod 640 /etc/papa-pult-bots.env
echo "ключи пультов: давра=$([[ -n $D ]] && echo есть || echo НЕТ) · paparazzi=$([[ -n $P ]] && echo есть || echo НЕТ) · хўжаобод=$([[ -n $X ]] && echo есть || echo НЕТ)"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-razvedka@.service /etc/systemd/system/
systemctl daemon-reload
# пульты понимают кнопки выбора (код GENPLAN) — тесты и перезапуск
( cd /opt/papa/modules/genplan && /opt/papa-venv/razvedka/bin/python -m unittest -q tests.test_sources_choice tests.test_sklad 2>&1 | tail -1 )
systemctl restart papa-genplan; sleep 5; echo "genplan: $(systemctl is-active papa-genplan)"
echo "== PULT_CARDS_DONE"
