#!/usr/bin/env bash
# 💰 31.10 «Реклама под ключ», этап 2: ✅ под заказом ИИ-ассистента → реклама сама в пульте Хўжаобода (экран времени).
# Папка /var/lib/papa-ads-inbox: пишет papa-assistant, читает и чистит papa-genplan. В каналы ничего не публикует.
# Откат: rm /etc/systemd/system/papa-{assistant,genplan}.service.d/ads-inbox.conf; daemon-reload; restart обоих; git revert.
set -Eeuo pipefail
D=/var/lib/papa-ads-inbox
( cd /opt/papa/modules/reklama && python3 -I -m unittest discover -q -s tests 2>&1 | tail -1 )
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) /opt/papa-venv/razvedka/bin/python -m unittest -q tests.test_adsin 2>&1 | tail -1 )
install -d -m 2770 -o papa-assistant -g papa-genplan "$D"
for s in papa-assistant papa-genplan; do
  mkdir -p /etc/systemd/system/$s.service.d
  printf '[Service]\nReadWritePaths=%s\n' "$D" > /etc/systemd/system/$s.service.d/ads-inbox.conf
done
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-assistant.service /etc/systemd/system/papa-assistant.service
systemctl daemon-reload
systemctl restart papa-assistant papa-genplan; sleep 6
echo "assistant: $(systemctl is-active papa-assistant) · genplan: $(systemctl is-active papa-genplan) · папка: $(stat -c '%U:%G %a' $D)"
journalctl -u papa-genplan -n 3 --no-pager -o cat
echo "== ADS_INBOX_DONE"
