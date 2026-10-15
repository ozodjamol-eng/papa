# Установить Voronka на Франкфурте. Instagram — в режиме ПРОВЕРКИ (ничего не отправляет),
# Telegram — только тестовый канал PAPA TEST. Существующие службы не трогаются.
set -Eeuo pipefail
[[ -s /etc/papa-voronka/instagram.env ]] || { echo "NO_TOKEN (сначала papa-update voronka-token)"; exit 1; }
[[ -s /etc/papa-test/bot.env ]] || { echo "NO_TEST_BOT (сначала papa-update test-setup)"; exit 1; }
id papa-voronka >/dev/null 2>&1 || useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin papa-voronka
chown -R papa-voronka:papa-voronka /etc/papa-voronka && chmod 700 /etc/papa-voronka && chmod 600 /etc/papa-voronka/instagram.env
( cd /opt/papa/modules/voronka && python3 -m unittest -q tests/test_voronka.py 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-voronka.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q papa-voronka.service
systemctl restart papa-voronka.service
sleep 4
echo "papa-voronka: $(systemctl is-active papa-voronka)"
systemd-run --quiet --wait --pipe -p User=papa-voronka -p EnvironmentFile=/etc/papa-test/bot.env \
  -p Environment="PAPA_VORONKA_DB=/var/lib/papa-voronka/voronka.sqlite3" -p WorkingDirectory=/opt/papa/modules/voronka \
  python3 -m voronka status
echo "gateway=$(systemctl is-active nexus-private-control-v2) connect=$(systemctl is-active nexus-connect) mem_free=$(free -m | awk '/Mem/{print $7}')MB"
echo "== VORONKA_INSTALLED"
