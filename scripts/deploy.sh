#!/usr/bin/env bash
# deploy.sh — the one-command server deploy (run on the server):
#   git pull → verified restart → status snapshot
# Requires the sudoers rule from scripts/README (NOPASSWD for arkwatch
# systemctl actions) so the restart never depends on a piped password.
set -euo pipefail
cd /home/kresna/ark-watch

echo "=== HEAD sebelum: $(git log --oneline -1) ==="
git pull origin main
echo "=== HEAD sesudah: $(git log --oneline -1) ==="

bash scripts/restart-verified.sh

echo "=== 5 log terakhir ==="
tail -n 5 "$(ls -1t logs/daemon-2026*.log 2>/dev/null | head -1)" || true
