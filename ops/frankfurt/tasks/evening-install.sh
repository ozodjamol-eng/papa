#!/usr/bin/env bash
# 🌆 Вечерний пул (30.10, владелец «да»): канал «PAPA ВЕЧЕР ПУЛ» (создаётся сам, попадает в KATTA BANK),
# видео Pixabay без людей/лого → 1080×1920 → /var/lib/papa-evening → GENPLAN кладёт фон дня в данные ролика.
# Ничего не публикует в каналы. Откат: systemctl disable --now papa-evening.timer (дайджест вернётся к осеннему фону).
set -Eeuo pipefail
PY=/opt/papa-venv/razvedka/bin/python
command -v ffmpeg >/dev/null || { apt-get install -y -q ffmpeg >/dev/null; }
( cd /opt/papa/modules/razvedka && $PY -m unittest -q tests.test_evening 2>&1 | tail -1 )
getent group papa-genplan >/dev/null || { echo "нет группы papa-genplan"; exit 1; }
install -d -m 2750 -o papa-razvedka -g papa-genplan /var/lib/papa-evening
install -d /etc/systemd/system/papa-razvedka@evening.service.d
printf '[Service]\nReadWritePaths=/var/lib/papa-evening\nEnvironment=PAPA_EVENING_DIR=/var/lib/papa-evening\nMemoryMax=600M\nMemoryHigh=500M\n' \
  > /etc/systemd/system/papa-razvedka@evening.service.d/evening.conf
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-evening.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable -q --now papa-evening.timer
for u in collect run curate hunt pain sources insta archive; do
  if systemctl is-active -q "papa-razvedka@$u.service"; then echo "Разведка занята ($u) — первый прогон по таймеру в 15:30"; echo "== EVENING_INSTALL_DONE"; exit 0; fi
done
systemctl start papa-razvedka@evening.service || true
journalctl -u papa-razvedka@evening.service -n 30 -o cat --no-pager | tail -n 25
echo "фонов на диске: $(ls /var/lib/papa-evening/*.mp4 2>/dev/null | wc -l)"
echo "== EVENING_INSTALL_DONE"
