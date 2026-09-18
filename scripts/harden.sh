#!/usr/bin/env bash
# harden.sh — file-permission anchors (run on the server after any redeploy
# that might create files). ROUND-6: .env and the DB were world-readable
# (644) while carrying 6 live credentials.
set -euo pipefail
cd /home/kresna/ark-watch
chmod 600 .env data/arkwatch.db data/arkwatch.db-wal data/arkwatch.db-shm 2>/dev/null || true
chmod 640 logs/*.log 2>/dev/null || chmod 600 logs/*.log 2>/dev/null || true
echo "✓ hardened:"
stat -c '%a %n' .env data/arkwatch.db
