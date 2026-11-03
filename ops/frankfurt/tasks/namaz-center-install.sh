#!/usr/bin/env bash
# «🕌 Намоз маркази» (03.11): таймер выгрузки времени намаза из PAPA (каждые 10 мин) → /var/lib/papa-namaz/namaz.json.
# Шлюз отдаёт её Лондону (/api/runner/namaz). Откат: systemctl disable --now papa-namaz-export.timer
set -euo pipefail
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-namaz-export.service /opt/papa/ops/frankfurt/systemd/papa-namaz-export.timer /etc/systemd/system/
systemctl daemon-reload
systemctl start papa-namaz-export.service && journalctl -u papa-namaz-export -n 2 -o cat --no-pager
systemctl enable -q --now papa-namaz-export.timer
echo "таймер: $(systemctl is-active papa-namaz-export.timer)"
python3 -c "import json;d=json.load(open('/var/lib/papa-namaz/namaz.json'));print('в выгрузке:', d['schedule'][-1])"
echo "== NAMAZ_CENTER_INSTALLED"
