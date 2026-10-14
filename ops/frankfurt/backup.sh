#!/usr/bin/env bash
# Consistent SQLite backup (online backup API) -> integrity check -> AES-256 encrypt -> keep 14 -> optional offsite.
set -Eeuo pipefail; umask 077
PY=/opt/nexus-private-control-v2/.venv/bin/python
DB=/var/lib/nexus-private-control/control.sqlite3
OUT=/var/backups/nexus-v2; KEY=/etc/nexus-v2-backup.key
install -d -m 700 "$OUT"
ts=$(date -u +%Y%m%dT%H%M%SZ); tmp="$OUT/.tmp-$ts.sqlite3"
trap 'rm -f "$tmp"' EXIT
"$PY" - "$DB" "$tmp" <<'PY'
import sqlite3,sys
s=sqlite3.connect(f'file:{sys.argv[1]}?mode=ro',uri=True);d=sqlite3.connect(sys.argv[2])
s.backup(d);ok=d.execute('PRAGMA integrity_check').fetchone()[0];d.close();s.close()
if ok!='ok':raise SystemExit('integrity_check_failed')
PY
gzip -c "$tmp" | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$KEY" -out "$OUT/control-$ts.sqlite3.gz.enc"
sha256sum "$OUT/control-$ts.sqlite3.gz.enc" | awk '{print $1}' > "$OUT/control-$ts.sqlite3.gz.enc.sha256"
ls -1t "$OUT"/control-*.enc 2>/dev/null | tail -n +15 | while read -r f; do rm -f "$f" "$f.sha256"; done
echo "BACKUP_OK control-$ts.sqlite3.gz.enc"
if [[ -r /etc/nexus-v2-offsite.env ]]; then . /etc/nexus-v2-offsite.env
  [[ -n "${OFFSITE_SSH:-}" ]] && scp -q -i /root/.ssh/nexus_v2_offsite -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes \
     "$OUT/control-$ts.sqlite3.gz.enc" "$OUT/control-$ts.sqlite3.gz.enc.sha256" "$OFFSITE_SSH:" && echo "OFFSITE_OK $OFFSITE_SSH"
fi
