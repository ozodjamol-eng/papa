#!/usr/bin/env bash
# FABRIKA: ffmpeg + yt-dlp + Pillow, служба papa-fabrika, перезапуск бота. Повтор безопасен.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
command -v ffmpeg >/dev/null || { apt-get update -qq && apt-get install -y -qq ffmpeg >/dev/null; }
[[ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ]] || { apt-get update -qq && apt-get install -y -qq fonts-dejavu-core >/dev/null; }
/opt/papa-venv/razvedka/bin/pip install -q --upgrade yt-dlp pillow
echo "ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3) | yt-dlp: $(/opt/papa-venv/razvedka/bin/yt-dlp --version)"
install -d -o papa-genplan -g papa-genplan -m 0700 /var/lib/papa-genplan/work /var/lib/papa-genplan/cache
( cd /opt/papa/modules/genplan && /opt/papa-venv/razvedka/bin/python -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-fabrika.service /etc/systemd/system/papa-fabrika.service
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-genplan.service /etc/systemd/system/papa-genplan.service
systemctl daemon-reload
systemctl enable -q papa-fabrika
systemctl restart papa-genplan papa-fabrika; sleep 5
echo "genplan: $(systemctl is-active papa-genplan) | fabrika: $(systemctl is-active papa-fabrika)"
[[ -s /etc/papa-genplan/ai.env ]] && echo "ИИ: ключ есть" || echo "ИИ: ключа ещё нет — papa-update genplan-ai-key"
free -m | awk 'NR==2{print "память: занято " $3 " из " $2 " МБ"}'
echo "== FABRIKA_DONE"
