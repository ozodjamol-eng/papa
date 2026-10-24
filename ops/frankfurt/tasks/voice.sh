#!/usr/bin/env bash
# «Голос» (ElevenLabs): поиск голосов, клон по образцу, образцы озвучки. Задание — ветка voice (кладёт ассистент), результат mp3 — ветка voice-out. Ключ — /root/.elevenlabs.env. Ничего не публикует, тратит только кредиты ElevenLabs (Starter, лимит жёсткий).
set -Eeuo pipefail
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -C /opt/papa fetch -q origin voice 2>/dev/null || { echo "NO_VOICE_BRANCH"; exit 1; }
git -C /opt/papa archive FETCH_HEAD | tar -x -C "$T"
[[ -f "$T/voice/job.json" ]] || { echo "NO_JOB"; exit 1; }
python3 -I /opt/papa/ops/frankfurt/voice.py "$T/voice" "$T/out"
if ls "$T"/out/*.mp3 >/dev/null 2>&1; then
  if [[ "${VOICE_TG:-1}" == 1 ]] && grep -q '"telegram": *true' "$T/voice/job.json"; then
    ( set -a; . /etc/papa-genplan/genplan.env; [ -f /etc/papa-genplan/bots.env ] && . /etc/papa-genplan/bots.env; set +a
      python3 -I /opt/papa/ops/frankfurt/voice_send.py "$T/out" ) || echo "TG_SEND_FAIL"
  fi
  if grep -q '"hear": *true' "$T/voice/job.json"; then
    ( set -a; . /etc/papa-genplan/ai.env; set +a; python3 -I /opt/papa/ops/frankfurt/hear.py "$T"/out/*.mp3 ) || echo "HEAR_FAIL"
  fi
  mkdir -p -m 700 /root/.ssh; K=/etc/papa-motion/deploy_key; ssh-keygen -lf $K.pub || true
  export GIT_SSH_COMMAND="ssh -F /dev/null -i $K -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts"
  ( cd "$T/out" && git init -q && git checkout -q -b voice-out && git add . \
    && git -c user.name=papa-frankfurt -c user.email=papa@localhost commit -q -m "voice-out" \
    && git push -q -f git@github.com:ozodjamol-eng/papa.git voice-out 2>&1 | tail -8 && echo "PUSHED voice-out" ) || echo "PUSH_FAIL"
fi
