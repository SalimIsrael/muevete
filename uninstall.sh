#!/bin/bash
set -euo pipefail

PLIST_NAME="com.muevete.app.plist"
LABEL="${PLIST_NAME%.plist}"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
rm -f "$PLIST_DST"

echo "Muévete desinstalado."
