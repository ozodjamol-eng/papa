# Собрать посты (первый раз — до 7 дней назад). Идёт неторопливо, может занять 10–40 минут.
set -Eeuo pipefail
[[ -s /etc/papa-razvedka/telegram.env ]] || { echo "NO_LOGIN: сначала papa-update razvedka-login"; exit 1; }
echo "сбор запущен $(date '+%H:%M'); ход сбора ниже"
systemctl start --no-block papa-razvedka@collect.service
sleep 2
journalctl -u papa-razvedka@collect.service -f -n 0 -o cat &
J=$!
while systemctl is-active -q papa-razvedka@collect.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@collect.service)" == activating ]]; do sleep 5; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value papa-razvedka@collect.service)"
echo "== COLLECT_FINISHED (дальше: papa-update razvedka-report)"
