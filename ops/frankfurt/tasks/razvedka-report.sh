# Показать отчёт и отправить его в «Избранное» аккаунта Разведки.
set -Eeuo pipefail
systemctl start papa-razvedka@send.service
journalctl -u papa-razvedka@send.service -n 120 -o cat --no-pager | tail -n 80
