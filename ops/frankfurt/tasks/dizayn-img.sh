#!/usr/bin/env bash
# 🏠 Дизайн квартир: ветка dizayn (job.json + 3D-заготовки, кладёт ассистент) → Gemini рисует картинки → ветка dizayn-out.
# Только запрос к Gemini (бесплатный ключ) и push картинок в отдельную ветку. Ничего не публикует в каналы.
set -Eeuo pipefail
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin dizayn 2>/dev/null || { echo "NO_DIZAYN_BRANCH"; exit 1; }
mkdir -p "$T/in" "$T/out"; git -C /opt/papa archive FETCH_HEAD dizayn | tar -x -C "$T/in"
set -a; . /etc/papa-genplan/ai.env; [ -f /etc/papa-dizayn/img.env ] && . /etc/papa-dizayn/img.env; set +a   # платный ключ картинок — свой
python3 -I /opt/papa/ops/frankfurt/dizayn_img.py "$T/in/dizayn" "$T/out/dizayn-out"
ls "$T/out/dizayn-out"/*.png >/dev/null 2>&1 || { echo "== DIZAYN_IMG_DONE (картинок нет)"; exit 0; }
KEY=/etc/papa-motion/deploy_key
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
cd "$T/out" && git init -q && git checkout -q --orphan dizayn-out && git add -A \
  && git -c user.name=papa-dizayn -c user.email=papa@localhost commit -qm "dizayn-out $(date +%F-%H%M)" \
  && git push -q -f git@github.com:ozodjamol-eng/papa.git dizayn-out && echo "pushed dizayn-out"
echo "== DIZAYN_IMG_DONE"
