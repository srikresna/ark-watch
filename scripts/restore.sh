#!/usr/bin/env bash
# restore.sh — verified disaster recovery from a nightly backup.
# RUNBOOK (scripts/README.md §restore): a naive `cp` over the live DB
# replays a STALE -wal and the restored file silently stays in
# journal_mode=delete — this script is the only supported restore path.
set -euo pipefail
DB=/home/kresna/ark-watch/data/arkwatch.db
BK=/home/kresna/ark-watch/backups

if [ -z "${1:-}" ]; then
  echo "usage: bash scripts/restore.sh arkwatch-YYYYMMDD.db   (ls $BK for candidates)" >&2
  exit 2
fi
SRC="$BK/$1"
[ -f "$SRC" ] || { echo "✗ backup not found: $SRC" >&2; exit 2; }

echo "=== 1/5 pre-flight ==="
systemctl is-active arkwatch && echo "  (daemon akan dihentikan)"
ls -la "$DB" "$DB-wal" 2>/dev/null || true

echo "=== 2/5 stop daemon ==="
sudo systemctl stop arkwatch
sleep 2

echo "=== 3/5 restore ==="
rm -f "$DB-wal" "$DB-shm"          # stale WAL = silent data replay
cp "$SRC" "$DB"
chmod 600 "$DB"

echo "=== 4/5 re-assert WAL + integrity ==="
python3 - <<'EOF'
import sqlite3
c = sqlite3.connect("/home/kresna/ark-watch/data/arkwatch.db", isolation_level=None)
print("  journal:", c.execute("PRAGMA journal_mode=WAL").fetchone()[0])
print("  integrity:", c.execute("PRAGMA integrity_check").fetchone()[0])
print("  schema:", c.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0])
c.close()
EOF

echo "=== 5/5 start (verified) ==="
bash scripts/restart-verified.sh
echo "✓ RESTORE SELESAI — cek brief berikutnya + fetch_log"
