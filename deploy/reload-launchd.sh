#!/bin/bash
# reload-launchd.sh — plutil-validated reload of the inception daemon agent.
set -euo pipefail
PLIST_PATH="${1:-}"
LABEL="${2:-}"
LOG_FILE="${3:-/tmp/inception-launchd-reload.log}"
[[ -z "$PLIST_PATH" || -z "$LABEL" ]] && exit 1
[[ ! -f "$PLIST_PATH" ]] && exit 1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] detected change in $PLIST_PATH" >> "$LOG_FILE"
if ! plutil -lint "$PLIST_PATH" > /dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: invalid plist — skipping reload" >> "$LOG_FILE"
    exit 1
fi
launchctl unload "$PLIST_PATH" 2>/dev/null || true
sleep 0.5
launchctl load "$PLIST_PATH"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] reloaded $LABEL" >> "$LOG_FILE"
