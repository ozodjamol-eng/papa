#!/usr/bin/env bash
# 💡 «Боль аудитории» — внеочередной сбор комментариев (обычно сам по таймеру).
set -Eeuo pipefail
systemctl start --no-block papa-razvedka@pain.service; sleep 2
journalctl -u papa-razvedka@pain.service -f -n 0 -o cat & J=$!
while systemctl is-active -q papa-razvedka@pain.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@pain.service)" == activating ]]; do sleep 3; done
sleep 1; kill $J 2>/dev/null || true
echo "результат: $(systemctl show -p Result --value papa-razvedka@pain.service)"
echo "== PAIN_RUN_DONE"
