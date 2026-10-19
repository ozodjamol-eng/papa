#!/usr/bin/env bash
# 🕊 ХОТИРА: обрезка скриншотов и «👤 По лицу» (19.10). Ставит OpenCV в отдельный venv /opt/papa-venv/xotira
# (бесплатно, ~60 МБ на диске), тесты, перезапуск. Откат: rm -rf /opt/papa-venv/xotira && papa-update xotira-restart
set -euo pipefail
V=/opt/papa-venv/xotira
[[ -x $V/bin/python ]] || python3 -m venv $V
$V/bin/pip install -q --upgrade pip
$V/bin/pip install -q -r /opt/papa/modules/xotira/requirements.txt
$V/bin/python -c "import cv2; print('OpenCV', cv2.__version__, '· лицо:', hasattr(cv2, 'FaceDetectorYN'))"
( cd /opt/papa/modules/xotira && $V/bin/python -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-xotira.service /etc/systemd/system/; systemctl daemon-reload
systemctl restart papa-xotira; sleep 5
echo "papa-xotira: $(systemctl is-active papa-xotira) · память свободно $(free -m | awk '/Mem/{print $7}') МБ · диск $(df -h / | awk 'NR==2{print $5}')"
journalctl -u papa-xotira -n 3 --no-pager -o cat
echo "== XOTIRA_PHOTO_DONE"
