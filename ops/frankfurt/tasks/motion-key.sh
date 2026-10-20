#!/usr/bin/env bash
# 🔑 Ключ записи в GitHub для роликов-дайджестов (решение владельца 20.10). Создаёт deploy-key (ed25519) один раз
# и показывает ОТКРЫТУЮ часть — владелец добавляет её в GitHub: Settings → Deploy keys → Add (Allow write access).
# Закрытая часть остаётся на сервере (/etc/papa-motion/deploy_key, 0600, только papa-genplan). Повторный запуск — тот же ключ + проверка доступа.
set -Eeuo pipefail
K=/etc/papa-motion/deploy_key
install -d -m 0750 -o root -g papa-genplan /etc/papa-motion
if [[ ! -f "$K" ]]; then
  ssh-keygen -q -t ed25519 -N "" -C "papa-frankfurt-motion" -f "$K"
  echo "ключ создан"
fi
chown papa-genplan:papa-genplan "$K" "$K.pub"; chmod 0600 "$K"; chmod 0644 "$K.pub"
echo "===== ОТКРЫТЫЙ КЛЮЧ (для GitHub) ====="
cat "$K.pub"
echo "====================================="
install -d -m 0700 -o papa-genplan -g papa-genplan /var/lib/papa-genplan/.ssh
if sudo -u papa-genplan env HOME=/var/lib/papa-genplan GIT_SSH_COMMAND="ssh -i $K -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/var/lib/papa-genplan/.ssh/known_hosts" \
     git ls-remote git@github.com:ozodjamol-eng/papa.git HEAD >/dev/null 2>&1; then
  echo "✅ доступ к GitHub по ключу ЕСТЬ"
else
  echo "⏳ доступа пока нет — ключ ещё не добавлен в GitHub"
fi
echo "== MOTION_KEY_DONE"
