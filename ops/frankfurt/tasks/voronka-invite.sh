# Voronka: создать ссылку-приглашение с заявкой в каналы из config.toml (сейчас — только PAPA TEST).
set -Eeuo pipefail
systemd-run --quiet --wait --pipe -p User=papa-voronka -p EnvironmentFile=/etc/papa-test/bot.env \
  -p Environment="PAPA_VORONKA_DB=/var/lib/papa-voronka/voronka.sqlite3" -p WorkingDirectory=/opt/papa/modules/voronka \
  python3 -m voronka invite "${1:-test-$(date +%m%d)}"
