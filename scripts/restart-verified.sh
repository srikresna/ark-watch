#!/usr/bin/env bash
# restart-verified.sh — prove the daemon ACTUALLY restarted.
#
# WHY (2026-09-18 incident): two "restarts" silently failed (the sudo
# password pipe broke on shell quoting) while `systemctl is-active` kept
# answering "active" — the OLD process was still running. is-active is
# NOT proof of a restart; a CHANGED ExecMainStartTimestamp is. This script
# exits non-zero unless the start timestamp moved.
set -euo pipefail

OLD=$(systemctl show arkwatch -p ExecMainStartTimestamp --value)
sudo systemctl restart arkwatch
sleep 3
NEW=$(systemctl show arkwatch -p ExecMainStartTimestamp --value)

if [ -z "$NEW" ] || [ "$OLD" = "$NEW" ]; then
    echo "✗ RESTART TIDAK TERVERIFIKASI — start ts tidak berubah: '$OLD'" >&2
    exit 1
fi
echo "✓ restart terverifikasi: $OLD → $NEW"
echo "  state: $(systemctl is-active arkwatch)"
