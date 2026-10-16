#!/usr/bin/env bash
# 🤖 Автопилот PAPA: ИИ сам запускает задачи papa-update на Франкфурте через шлюз NEXUS.
#   безопасные (allow.json → auto) — сразу; остальные — после кнопки «✅ Разрешить» в «🎉 КАТТА ДАВРА Пульт»;
#   секреты / вход в аккаунты / сам автопилот — никогда. О каждой задаче — сообщение владельцу.
# Шаги: тесты → шлюз и Connect (новые инструменты, тесты + автооткат) → GENPLAN (кнопка разрешения) → служба papa-autopilot.
# Откат: systemctl disable --now papa-autopilot   (всё остальное продолжает работать как раньше)
set -Eeuo pipefail
A=/opt/papa/ops/frankfurt/autopilot
echo "1/5 тесты автопилота:"
( cd "$A" && python3 -I -m unittest -q test_autopilot 2>&1 | tail -1 )
( cd "$A" && python3 -I -m unittest -q test_autopilot >/dev/null 2>&1 ) || { echo "ТЕСТЫ НЕ ПРОШЛИ — ничего не меняю"; exit 1; }
echo "2/5 где база шлюза:"
GWDB=""
for f in $(systemctl show -p EnvironmentFiles --value nexus-private-control-v2 | tr ' ' '\n' | grep '^/' | sed 's/^-//'); do
  [[ -f "$f" ]] && v=$(grep -E '^NEXUS_CONTROL_DB=' "$f" | tail -1 | cut -d= -f2- | tr -d '"'"'") && [[ -n "$v" ]] && GWDB=$v
done
v=$(systemctl show -p Environment --value nexus-private-control-v2 | tr ' ' '\n' | grep '^NEXUS_CONTROL_DB=' | cut -d= -f2- || true)
[[ -n "$v" ]] && GWDB=$v
[[ -n "$GWDB" ]] || GWDB=/var/lib/nexus-private-control/control.sqlite3
[[ -f "$GWDB" ]] || { echo "НЕ НАШЁЛ базу шлюза ($GWDB) — остановка"; exit 1; }
echo "  $GWDB (владелец: $(stat -c %U "$GWDB"))"
install -d -m 700 /etc/papa-autopilot
printf 'PAPA_AUTOPILOT_GW_DB=%s\n' "$GWDB" > /etc/papa-autopilot/autopilot.env; chmod 600 /etc/papa-autopilot/autopilot.env
echo "3/5 шлюз и Connect (инструменты автопилота):"
bash /opt/papa/ops/frankfurt/tasks/pult-deploy.sh || { echo "ШЛЮЗ НЕ ОБНОВИЛСЯ — автопилот не включаю"; exit 1; }
echo "4/5 GENPLAN (кнопка «✅ Разрешить / ❌ Нет»):"
systemctl restart papa-genplan; sleep 4; echo "  papa-genplan: $(systemctl is-active papa-genplan)"
echo "5/5 служба papa-autopilot:"
install -m 644 "$A/papa-autopilot.service" /etc/systemd/system/papa-autopilot.service
systemctl daemon-reload; systemctl enable -q papa-autopilot; systemctl restart papa-autopilot; sleep 4
echo "  papa-autopilot: $(systemctl is-active papa-autopilot)"
journalctl -u papa-autopilot -n 3 --no-pager -o cat
echo "== AUTOPILOT_INSTALL_DONE  (выключить: systemctl disable --now papa-autopilot)"
