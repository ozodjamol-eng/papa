#!/usr/bin/env bash
# 🌙 Свой Кечки дайжест: служба + таймер 19:50 (Ташкент), режим ПРОВЕРКИ — предпросмотр владельцу и в PAPA TEST.
# В настоящую группу Хўжаобод — отдельным шагом (передача пакета на Лондон), только по решению владельца.
# Откат: systemctl disable --now papa-digest.timer
set -Eeuo pipefail
echo "1/3 тесты дайджеста:"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) /opt/papa-venv/razvedka/bin/python -m unittest -q tests.test_digest 2>&1 | tail -1 ) | tee /tmp/digest-tests.txt
grep -q '^OK' /tmp/digest-tests.txt || { echo "ТЕСТЫ НЕ ПРОШЛИ — ничего не меняю"; exit 1; }
echo "2/3 служба и таймер:"
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-digest.service /etc/systemd/system/
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-digest.timer /etc/systemd/system/
systemctl daemon-reload; systemctl enable -q --now papa-digest.timer
echo "  таймер: $(systemctl is-active papa-digest.timer), следующий: $(systemctl show papa-digest.timer -p NextElapseUSecRealtime --value)"
echo "3/3 пробная сборка сейчас (предпросмотр придёт в Пульт КАТТА ДАВРА):"
systemctl start papa-digest.service || true
journalctl -u papa-digest -n 6 --no-pager -o cat | cut -c1-300
echo "== DIGEST_INSTALL_DONE (откат: systemctl disable --now papa-digest.timer)"
