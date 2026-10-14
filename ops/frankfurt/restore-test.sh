#!/usr/bin/env bash
# Decrypt latest backup into a temp dir, integrity-check, compare row counts with live DB. Never touches the live DB.
set -Eeuo pipefail; umask 077
OUT=/var/backups/nexus-v2; KEY=/etc/nexus-v2-backup.key; PY=/opt/nexus-private-control-v2/.venv/bin/python
f=$(ls -1t "$OUT"/control-*.enc | head -1)
[[ "$(sha256sum "$f"|awk '{print $1}')" == "$(cat "$f.sha256")" ]] || { echo RESTORE_FAIL_hash; exit 1; }
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$KEY" -in "$f" | gunzip > "$t/r.sqlite3"
"$PY" - "$t/r.sqlite3" /var/lib/nexus-private-control/control.sqlite3 "$f" <<'PY'
import sqlite3,sys
r=sqlite3.connect(sys.argv[1]);l=sqlite3.connect(f'file:{sys.argv[2]}?mode=ro',uri=True)
ok=r.execute('PRAGMA integrity_check').fetchone()[0]
c=lambda db,t:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
print('RESTORE', 'OK' if ok=='ok' else 'FAIL', sys.argv[3].rsplit('/',1)[1],
      {t:(c(r,t),c(l,t)) for t in ('tasks','audit','sessions','devices')}, '(backup,live)')
PY
