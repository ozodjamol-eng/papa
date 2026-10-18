#!/usr/bin/env bash
# 🔑 Замена ключа шифрования копий (18.10, владелец: «да» — старый ключ частично попал на скрин).
# Новый ключ → свежие копии с ним (сервер + «PAPA РЕЗЕРВ») → проверка расшифровкой → старые копии и старый ключ удаляются.
# Ключ в вывод НЕ печатается: владелец смотрит его сам в консоли (cat /etc/nexus-v2-backup.key).
set -Eeuo pipefail; umask 077
K=/etc/nexus-v2-backup.key; OUT=/var/backups/nexus-v2
cp -p "$K" "$K.old"
openssl rand -base64 48 | tr -d '\n' > "$K.new" && chmod 600 "$K.new" && mv -f "$K.new" "$K"
mkdir -p "$OUT/old-key" && find "$OUT" -maxdepth 1 -name '*.enc*' -exec mv {} "$OUT/old-key/" \;
if systemctl start nexus-v2-backup.service && /usr/local/lib/nexus-v2/restore-test.sh | grep -q "RESTORE OK"; then
  journalctl -u nexus-v2-backup.service -n 20 -o cat --no-pager | grep -E "BACKUP_OK|TELEGRAM_" | tail -6
  rm -rf "$OUT/old-key" "$K.old"
  echo "✅ Новый ключ работает: копии сделаны и проверены расшифровкой. Старый ключ и старые копии на сервере удалены."
else
  mv -f "$K.old" "$K"; mv "$OUT"/old-key/* "$OUT/" 2>/dev/null || true; rmdir "$OUT/old-key" 2>/dev/null || true
  echo "ROTATE_FAIL: вернул старый ключ, ничего не потеряно"; exit 1
fi
echo "== BACKUP_ROTATE_DONE"
