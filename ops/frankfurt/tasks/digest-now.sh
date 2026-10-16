#!/usr/bin/env bash
# 🌙 Собрать Кечки дайжест сейчас (режим проверки): предпросмотр владельцу и в PAPA TEST. Ничего не публикует в группу.
set -Eeuo pipefail
systemctl start papa-digest.service || true
journalctl -u papa-digest -n 6 --no-pager -o cat | cut -c1-300
echo "== DIGEST_NOW_DONE"
