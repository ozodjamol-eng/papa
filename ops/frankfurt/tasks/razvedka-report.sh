# Показать отчёт и отправить его в PAPA TEST GROUP (17.10: не в «Избранное»).
set -Eeuo pipefail
systemctl start papa-razvedka@send.service
journalctl -u papa-razvedka@send.service -n 120 -o cat --no-pager | tail -n 80
