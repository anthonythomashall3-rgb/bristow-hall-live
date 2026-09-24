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
# 20 September 2026 (collection 257): the topic may also come from the environment (the cloud runner passes the secret
# that way) or from a local.env beside the bundle (the path the workflow writes); a call goes out at high priority.
TOPIC="${ALERT_NTFY_TOPIC:-}"
[ -f "$ENV" ] || ENV="$COL/../onset-detector-new-2026-08-23/live_data/config/local.env"
if [ -z "$TOPIC" ] && [ -f "$ENV" ]; then
  TOPIC="$(grep -m1 '^ALERT_NTFY_TOPIC=' "$ENV" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
PRIO="default"; case "$LEVEL" in *CALLED*|*CLOSED*|*DRILL*|*STANDING*|*PROPOSED*|*LAPSED*) PRIO="high";; esac
if [ -n "$TOPIC" ]; then curl -sS -m 15 -H "Title: Bristow-Hall System: $LEVEL" -H "Priority: $PRIO" -d "$MSG" "https://ntfy.sh/$TOPIC" >/dev/null 2>&1 || true; fi

# A SECOND, INDEPENDENT CHANNEL. ntfy.sh is free, anonymous and promises nothing; until 18 September it was the only
# way an alert reached a phone, so the day ntfy has an outage is the day the system goes quiet without saying so.
# A GitHub issue on the update repository is the second path: gh is already authenticated here, GitHub emails the
# owner on a new issue, and the two services fail for entirely different reasons. One issue per level per day, so a
# long outage is one thread rather than a hundred.
if command -v gh >/dev/null 2>&1; then
  MARK="$COL/workspace/cache/alert_issue_$(date -u +%F)_$(printf '%s' "$LEVEL" | tr -c 'A-Za-z0-9' '_')"
  if [ ! -f "$MARK" ]; then
    ( gh issue create --repo "${GITHUB_REPOSITORY:-anthonythomashall3-rgb/bristow-hall-live}" \
        --title "[$LEVEL] $(date -u +%FT%TZ)" \
        --body "$MSG

Raised by s2/alert.sh on $(hostname). This is the second alert channel; the first is ntfy. If you are reading this
in email and did not also get a phone notification, ntfy is the thing that failed." >/dev/null 2>&1 \
      && touch "$MARK" ) &
  fi
fi
exit 0
