# Один раз: ключ только для чтения репозитория papa (через порт 443, работает даже если 22 закрыт)
set -Eeuo pipefail
install -d -m 700 /root/.ssh
[[ -f /root/.ssh/papa_deploy ]] || ssh-keygen -q -t ed25519 -N '' -C "papa-deploy-$(hostname)" -f /root/.ssh/papa_deploy
grep -q '^Host github-papa$' /root/.ssh/config 2>/dev/null || printf '\nHost github-papa\n  HostName ssh.github.com\n  Port 443\n  User git\n  IdentityFile /root/.ssh/papa_deploy\n  IdentitiesOnly yes\n' >> /root/.ssh/config
chmod 600 /root/.ssh/config
grep -q 'ssh.github.com' /root/.ssh/known_hosts 2>/dev/null || ssh-keyscan -p 443 -t ed25519 ssh.github.com >> /root/.ssh/known_hosts 2>/dev/null
cat /root/.ssh/papa_deploy.pub
