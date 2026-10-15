# Voronka: состояние и последние события (ничего не меняет).
set -Eeuo pipefail
echo "papa-voronka: $(systemctl is-active papa-voronka)"
systemd-run --quiet --wait --pipe -p User=papa-voronka -p EnvironmentFile=/etc/papa-test/bot.env \
  -p Environment="PAPA_VORONKA_DB=/var/lib/papa-voronka/voronka.sqlite3" -p WorkingDirectory=/opt/papa/modules/voronka \
  python3 -m voronka status
journalctl -u papa-voronka -n 15 -o cat --no-pager
