#!/bin/bash
# install-launchd.sh — validate and load the INCEPTION daemon launchd agents.
set -euo pipefail
REPO="/Users/void/CodeTonight/inception"
AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$AGENTS_DIR"

for PLIST in com.codetonight.inception com.codetonight.inception-watcher; do
    SRC="$REPO/deploy/$PLIST.plist"
    DST="$AGENTS_DIR/$PLIST.plist"
    plutil -lint "$SRC"
    cp "$SRC" "$DST"
    launchctl unload "$DST" 2>/dev/null || true
    launchctl load "$DST"
    echo "loaded $PLIST"
done

launchctl list | grep -E 'com.codetonight.inception' || true
echo "daemon: curl http://127.0.0.1:8377/api/health"
