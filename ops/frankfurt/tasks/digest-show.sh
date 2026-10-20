#!/usr/bin/env bash
# 🌙 Показать сегодняшний пакет Кечки дайжест (только чтение): полный текст и manifest — для ролика.
set -Eeuo pipefail
D=$(TZ=Asia/Tashkent date +%F); P=/var/lib/papa-genplan/digest/evening-digest-$D
[[ -d "$P" ]] || { echo "❌ нет пакета $P"; ls /var/lib/papa-genplan/digest | tail -3; exit 1; }
ls -la "$P"
for f in "$P"/*.txt "$P"/*.json; do [[ -f "$f" ]] && { echo "===== $(basename "$f")"; cat "$f"; echo; }; done
echo "== DIGEST_SHOW_DONE"
