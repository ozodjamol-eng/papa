#!/usr/bin/env bash
# AI-MOTION: Node.js 22 + Playwright Chromium для скилла awesome-ai-motion (637 эффектов GSAP → mp4).
# Ставит в /opt/papa-motion, делает пробный рендер титра. Повтор безопасен.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
SK=/opt/papa/.claude/skills/awesome-ai-motion
M=/opt/papa-motion
command -v ffmpeg >/dev/null || { apt-get update -qq && apt-get install -y -qq ffmpeg >/dev/null; }
NODE_MAJOR=$(node -v 2>/dev/null | sed 's/v\([0-9]*\).*/\1/' || echo 0)
if [[ "${NODE_MAJOR:-0}" -lt 20 ]]; then
  apt-get update -qq && apt-get install -y -qq ca-certificates curl gnupg >/dev/null
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
  apt-get update -qq && apt-get install -y -qq nodejs >/dev/null
fi
echo "node: $(node -v)"
install -d -m 0755 $M
cd $M
[[ -f package.json ]] || echo '{"name":"papa-motion","private":true,"type":"module"}' > package.json
npm i -s --no-audit --no-fund playwright@1 >/dev/null
export PLAYWRIGHT_BROWSERS_PATH=$M/browsers
npx -y playwright install --with-deps chromium >/dev/null 2>&1 || npx -y playwright install --with-deps chromium | tail -3
ln -sfn $M/node_modules "$SK/node_modules"   # render.mjs берёт playwright отсюда
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp "$SK/recipes/title-opener/index.html" "$T/index.html"
timeout 300 node "$SK/scripts/render.mjs" "$T/index.html" --embed --text "OZOD JAMOL" --out "$T/out" --jobs 1 2>&1 | tail -2
ls -la "$T/out" | grep -E "clip|poster" || { echo "== AI_MOTION_FAIL"; exit 1; }
free -m | awk 'NR==2{print "память: занято " $3 " из " $2 " МБ"}'
df -h / | awk 'NR==2{print "диск: свободно " $4}'
echo "== AI_MOTION_DONE"
