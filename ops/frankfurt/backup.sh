#!/usr/bin/env bash
# Ежедневная копия баз: онлайн-копия SQLite → проверка целостности → AES-256 → хранить 3 на сервере →
# копия в закрытый канал «PAPA РЕЗЕРВ» в Telegram (18.10, владелец: копия вне сервера, без лишней нагрузки на диск).
# Базы: старый NEXUS (control), Разведка, бот GENPLAN PAPA (пульты: очередь, запас, выученные подписи).
set -Eeuo pipefail; umask 077
PY=/opt/nexus-private-control-v2/.venv/bin/python
OUT=/var/backups/nexus-v2; KEY=/etc/nexus-v2-backup.key; KEEP=3
install -d -m 700 "$OUT"
ts=$(date -u +%Y%m%dT%H%M%SZ)
SENT=()

backup_db() {   # $1 — имя копии, $2 — путь к базе
  local name=$1 db=$2 tmp="$OUT/.tmp-$1-$ts.sqlite3" out="$OUT/$1-$ts.sqlite3.gz.enc"
  [[ -r "$db" ]] || { echo "SKIP $name (нет базы)"; return 0; }
  "$PY" - "$db" "$tmp" <<'PY'
import sqlite3,sys
s=sqlite3.connect(f'file:{sys.argv[1]}?mode=ro',uri=True);d=sqlite3.connect(sys.argv[2])
s.backup(d);ok=d.execute('PRAGMA integrity_check').fetchone()[0];d.close();s.close()
if ok!='ok':raise SystemExit('integrity_check_failed')
PY
  gzip -c "$tmp" | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$KEY" -out "$out"
  rm -f "$tmp"
  sha256sum "$out" | awk '{print $1}' > "$out.sha256"
  ls -1t "$OUT"/"$name"-*.enc 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do rm -f "$f" "$f.sha256"; done
  echo "BACKUP_OK $name-$ts.sqlite3.gz.enc ($(du -h "$out" | cut -f1))"
  SENT+=("$out")
}

backup_db control  /var/lib/nexus-private-control/control.sqlite3
backup_db razvedka /var/lib/papa-razvedka/razvedka.sqlite3
backup_db genplan  /var/lib/papa-genplan/genplan.sqlite3

# Копия вне сервера: закрытый канал «PAPA РЕЗЕРВ» (id — /etc/papa-backup.env, задача backup-telegram), шлёт бот отчётов
if [[ -r /etc/papa-backup.env && -r /etc/papa-test/bot.env ]]; then
  set -a; . /etc/papa-backup.env; . /etc/papa-test/bot.env; set +a
  if [[ -n "${PAPA_BACKUP_CHAT_ID:-}" && -n "${PAPA_TEST_BOT_TOKEN:-}" ]]; then
    for f in "${SENT[@]}"; do
      if (( $(stat -c %s "$f") > 49000000 )); then echo "TELEGRAM_SKIP $(basename "$f") (больше 49 МБ — лимит бота)"; continue; fi
      code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 120 \
        -F chat_id="$PAPA_BACKUP_CHAT_ID" -F disable_notification=true \
        -F caption="🗄 $(basename "$f") · sha256 $(cut -c1-12 "$f.sha256")" \
        -F document=@"$f" "https://api.telegram.org/bot${PAPA_TEST_BOT_TOKEN}/sendDocument" || echo 000)
      [[ "$code" == "200" ]] && echo "TELEGRAM_OK $(basename "$f")" || echo "TELEGRAM_FAIL $(basename "$f") http=$code"
    done
  fi
fi

if [[ -r /etc/nexus-v2-offsite.env ]]; then . /etc/nexus-v2-offsite.env
  f=$(ls -1t "$OUT"/control-*.enc | head -1)
  [[ -n "${OFFSITE_SSH:-}" ]] && scp -q -i /root/.ssh/nexus_v2_offsite -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes \
     "$f" "$f.sha256" "$OFFSITE_SSH:" && echo "OFFSITE_OK $OFFSITE_SSH"
fi
