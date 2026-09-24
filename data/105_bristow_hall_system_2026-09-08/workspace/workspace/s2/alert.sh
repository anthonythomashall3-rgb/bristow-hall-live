#!/bin/bash
# THE BRISTOW HALL SYSTEM - one alert (17 September 2026; collection 201; register item 61).
#     bash s2/alert.sh "<level>" "<message>"
# Appends to live/ALERTS.log, posts a macOS notification, and - only if local.env names ALERT_NTFY_TOPIC - sends the
# same line to https://ntfy.sh/<topic> so it reaches a phone. Never fails its caller; prints nothing.
LEVEL="${1:-ALERT}"; MSG="${2:-}"; MSG="${MSG//\"/\'}"
# Where the collection is. Resolved from this script's own location, so the system keeps working if the
# ~/mnt symlink that used to be hardcoded here is ever moved or removed. The old path is the fallback.
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/../.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
ENV="$HOME/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env"
mkdir -p "$COL/live" 2>/dev/null
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$LEVEL] $MSG" >> "$COL/live/ALERTS.log" 2>/dev/null
/usr/bin/osascript -e "display notification \"${MSG:0:220}\" with title \"Bristow-Hall System: $LEVEL\" sound name \"Basso\"" >/dev/null 2>&1 || true
if [ -f "$ENV" ]; then
  TOPIC="$(grep -m1 '^ALERT_NTFY_TOPIC=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")"
  if [ -n "$TOPIC" ]; then curl -sS -m 15 -H "Title: Bristow-Hall System: $LEVEL" -d "$MSG" "https://ntfy.sh/$TOPIC" >/dev/null 2>&1 || true; fi
fi
exit 0
