#!/bin/bash
# THE DEAD-MAN WATCHDOG (18 September 2026; collection 205; open register items 61 and 1.4).
#
# The live pipeline needs no AI and no Claude: launchd runs caffeinate -> bash -> bhs_run.sh, which is Python and
# shell only. But nothing watched the watcher. If launchd never fired, if the Mac slept through every slot, if the
# job died before its first line, or if the site quietly stopped being updated, the system said nothing at all - the
# search-week feed was dead for three days in September before anyone noticed.
#
# This is a second launchd job, independent of the first, that asks four questions and raises one alert if any of
# them is wrong. It is plain bash and curl: no AI, no Claude, no Python beyond the standard library, and it keeps
# working with the desktop app closed and nobody logged into anything.
#
#   1  did a run finish recently?          cache/last_done, against the hour of day
#   2  is the published site current?      built_at in the live bhs_state.json
#   3  does the local build match it?      out/bhs_state.json against what is published
#   4  is a publish owed?                  cache/deploy_pending left behind by a held or failed deploy
#
# Quiet when all four are well: it writes one line to live/WATCHDOG.log and exits 0. On a fault it calls s2/alert.sh,
# which appends to live/ALERTS.log, raises a macOS notification and, if local.env names ALERT_NTFY_TOPIC, pushes the
# same line to a phone through ntfy.sh. It repeats an alert at most once every six hours so a long outage does not
# become a stream.
#
#   bash s2/watchdog.sh            check, and alert if anything is wrong
#   bash s2/watchdog.sh --test     force the alert path once, to prove it reaches the phone
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# Where the collection is. Resolved from this script's own location, so the system keeps working if the
# ~/mnt symlink that used to be hardcoded here is ever moved or removed. The old path is the fallback.
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/../.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
WS="$COL/workspace"
LOG="$COL/live/WATCHDOG.log"
SEEN="$WS/cache/watchdog_last_alert"

# mtime in epoch seconds. BSD stat (macOS) and GNU stat (the Linux side of the bridge) take different flags, and
# the BSD form on Linux prints a filesystem report instead of a number, which used to make the arithmetic below
# die with "File: unbound variable". Try both, and fall back to now so a missing file never crashes the check.
# Epoch seconds from a timestamp string. The BSD-only form of the date command is macOS only, so off the Mac
# every one of these checks silently returned 0 and the script reported "cannot be read" - and, worse, alerted
# on it. python3 is already a hard dependency here, and it reads the offset in cache/last_done instead of
# throwing it away, so the age stays right even if the Mac's time zone stops matching the offset written.
#   _epoch_iso "2026-09-17T18:21:20.051954-07:00"   an offset-aware stamp; a naive one is read as local time
#   _epoch_ny  "2026-09-17 21:20"                   built_at, which the site writes in New York time
_epoch_iso() { python3 -c '
import sys, datetime
try:
    d = datetime.datetime.fromisoformat(sys.argv[1].strip())
    if d.tzinfo is None: d = d.astimezone()
    print(int(d.timestamp()))
except Exception: print(0)' "$1" 2>/dev/null || echo 0; }
_epoch_ny() { python3 -c '
import sys, datetime, zoneinfo
try:
    d = datetime.datetime.strptime(sys.argv[1].strip(), "%Y-%m-%d %H:%M")
    print(int(d.replace(tzinfo=zoneinfo.ZoneInfo("America/New_York")).timestamp()))
except Exception: print(0)' "$1" 2>/dev/null || echo 0; }
_mtime() {
  local m
  m=$(stat -f %m "$1" 2>/dev/null); case "$m" in (*[!0-9]*|"") m="";; esac
  [ -n "$m" ] || { m=$(stat -c %Y "$1" 2>/dev/null); case "$m" in (*[!0-9]*|"") m="";; esac; }
  echo "${m:-$NOW}"
}
SITE="https://bhrrealtime.pages.dev/bhs_state.json"
cd "$WS" 2>/dev/null || { echo "$(date -u +%FT%TZ) FAULT no workspace at $WS" >> "$HOME/watchdog-fallback.log"; exit 1; }
mkdir -p "$COL/live" cache 2>/dev/null
date -u +%s > "$WS/cache/watchdog_last"   # heartbeat: proves the job fired even if a later check dies

if [ "${1:-}" = "--test" ]; then
  bash s2/alert.sh "WATCHDOG TEST" "the watchdog can reach you: $(date -u +%FT%TZ)"
  echo "$(date -u +%FT%TZ) TEST alert sent" >> "$LOG"; exit 0
fi

OWNER="$COL/workspace/cache/watchdog_owner"
[ -f "$OWNER" ] || { [ "$(uname -s)" = "Darwin" ] && hostname > "$OWNER"; }
ONHOST=1
[ "$(uname -s)" = "Darwin" ] || ONHOST=0
[ ! -f "$OWNER" ] || [ "$(cat "$OWNER" 2>/dev/null)" = "$(hostname)" ] || ONHOST=0

NOW=$(date -u +%s)
HOUR_LOCAL=$(date +%H); HOUR_LOCAL=${HOUR_LOCAL#0}; DOW=$(date +%u)
FAULTS=""

# --- 1. a run finished recently. The schedule runs hourly 08:03-18:03 ET every day, so between those hours a gap of
# more than three hours is a fault; overnight the bar is twenty hours, which still catches a Mac that never woke.
LD="cache/last_done"
if [ ! -f "$LD" ]; then FAULTS="$FAULTS; no run has ever completed (cache/last_done is missing)"
else
  LDS=$(_epoch_iso "$(tr -d "\n" < "$LD")")
  if [ "$LDS" -eq 0 ]; then FAULTS="$FAULTS; cache/last_done cannot be read"
  else
    AGE=$(( (NOW - LDS) / 60 ))
    LIMIT=1200
    if [ "$HOUR_LOCAL" -ge 5 ] && [ "$HOUR_LOCAL" -le 16 ]; then LIMIT=180; fi
    if [ "$AGE" -gt "$LIMIT" ]; then
      FAULTS="$FAULTS; the last run finished ${AGE} minutes ago (more than ${LIMIT})"
      # Do not only complain: start it. Anthony does not disable sleep, so the Mac misses slots whenever it is
      # asleep - launchd folds the missed slots into one firing on wake, but if that firing never came (the job
      # unloaded, a wake too brief to run, a failure before the first line) nothing else would start it until the
      # next slot. Every ten minutes the Mac is awake and a run is overdue, this kicks one off. bhs_run.sh takes
      # its own lock, so a kickstart during a run is a no-op, and --why still refuses when nothing is due.
      if [ "$ONHOST" -eq 1 ]; then
        launchctl kickstart "gui/$(id -u)/com.bristowhall.system" >/dev/null 2>&1 \
          && echo "$(date -u +%FT%TZ) kickstarted the system job (last run ${AGE} min ago)" >> "$LOG"
      fi
    fi
  fi
fi

# --- 2. the published site is current, and 3. it is this machine's build
PUB="$(curl -sS -m 30 "$SITE?w=$NOW" 2>/dev/null)"
if [ -z "$PUB" ]; then FAULTS="$FAULTS; the published state file did not answer"
else
  PBUILT=$(printf '%s' "$PUB" | python3 -c "import sys,json;print((json.load(sys.stdin).get('built_at') or '')[:16])" 2>/dev/null)
  if [ -z "$PBUILT" ]; then FAULTS="$FAULTS; the published state file has no built_at"
  else
    PS=$(_epoch_ny "$PBUILT")                                               # built_at is New York time
    if [ "$PS" -gt 0 ]; then
      PAGE=$(( (NOW - PS) / 3600 ))
      MAXH=30; [ "$DOW" -ge 6 ] && MAXH=54                                  # a quiet weekend may have nothing to publish
      [ "$PAGE" -gt "$MAXH" ] && FAULTS="$FAULTS; the site was last built ${PAGE} hours ago (more than ${MAXH})"
    fi
    if [ -f out/bhs_state.json ]; then
      LBUILT=$(python3 -c "import json;print((json.load(open('out/bhs_state.json')).get('built_at') or '')[:16])" 2>/dev/null)
      if [ -n "$LBUILT" ] && [ "$LBUILT" != "$PBUILT" ]; then
        LS=$(_epoch_ny "$LBUILT")
        if [ "$LS" -gt "$PS" ] && [ $(( (LS - PS) / 3600 )) -ge 6 ]; then
          FAULTS="$FAULTS; this machine built at $LBUILT but the site still shows $PBUILT"
        fi
      fi
    fi
  fi
fi

# --- 4. a publish is owed
[ -f cache/deploy_pending ] && FAULTS="$FAULTS; a publish is owed (cache/deploy_pending); the site is not current"

# --- 5. the collectors are running, and are restarted here if they are not. This replaces the Claude-side scheduled
# task of 18 September, which did the same every four hours but needed the desktop app open and a model to read the
# output; this runs every ten minutes with neither. (What the Claude task could also do and this cannot: fetch the
# overwrite-in-place releases from the cloud while the Mac is ASLEEP. Nothing running on the Mac can do that. The
# answer to that is the Mac not sleeping, or a cloud runner - not a scheduled task that needs an app open.)
UID_=$(id -u)
for J in com.bristowhall.collector com.bristowhall.queuecollector com.bristowhall.system; do
  [ -f "$HOME/Library/LaunchAgents/$J.plist" ] || continue
  if ! launchctl print "gui/$UID_/$J" >/dev/null 2>&1; then
    launchctl bootstrap "gui/$UID_" "$HOME/Library/LaunchAgents/$J.plist" >/dev/null 2>&1 \
      && echo "$(date -u +%FT%TZ) loaded $J (it was not in launchd)" >> "$LOG"
    FAULTS="$FAULTS; $J was not loaded in launchd and has been loaded"
  fi
done
# the standing collector should have written a cycle line within six hours
ST="$HOME/mnt/Onset Detector Data/191_standing_collector_2026-09-16/logs/STATUS.txt"
if [ -f "$ST" ]; then
  SA=$(( (NOW - $(_mtime "$ST")) / 3600 ))
  if [ "$SA" -ge 6 ]; then
    FAULTS="$FAULTS; the standing collector has not written STATUS.txt for ${SA} hours"
    launchctl kickstart "gui/$UID_/com.bristowhall.collector" >/dev/null 2>&1 \
      && echo "$(date -u +%FT%TZ) kickstarted the collector (STATUS.txt ${SA}h old)" >> "$LOG"
  fi
fi
# --- 5b. the small backup, once a day. There is no Time Machine destination on this Mac and no git remote, so a
# disk failure would take the code, the pre-registrations, the records and the commit history with it. The
# harvested data could be fetched again; those cannot. The script measures its own list first and refuses over a
# cap, so it cannot quietly fill Dropbox the way its first version did. Run here because the watchdog is already
# a loaded job firing every ten minutes and a new launchd job is Anthony's to install.
BK="$WS/cache/backup_last"
if [ "$ONHOST" -eq 1 ]; then
  BA=999999; [ -f "$BK" ] && BA=$(( (NOW - $(_mtime "$BK")) / 3600 ))
  if [ "$BA" -ge 20 ]; then
    ( bash "$WS/s2/backup_small.sh" >> "$LOG" 2>&1; date -u +%s > "$BK" ) &
  fi
fi

# --- 5c. the full site audit, once a day: every page, every served file, every one of the 57 external source
# links, and the tool behind them. The fast form already runs after every publish; this is the slow half.
AU="$WS/cache/audit_last"
if [ "$ONHOST" -eq 1 ]; then
  AA=999999; [ -f "$AU" ] && AA=$(( (NOW - $(_mtime "$AU")) / 3600 ))
  if [ "$AA" -ge 20 ]; then
    ( OUT2="$(cd "$WS" && python3 s2/audit_everything.py --quiet 2>&1 | tail -20)"; RC2=$?
      echo "$(date -u +%FT%TZ) full audit: $(printf '%s' "$OUT2" | tail -1)" >> "$LOG"
      [ $RC2 -ne 0 ] && bash "$WS/s2/alert.sh" "THE DAILY SITE AUDIT FAILED" "$(printf '%s' "$OUT2" | tail -6 | tr '\n' ' ')"
      date -u +%s > "$AU" ) &
  fi
fi

# --- 6. the disk, which the harvest can fill
FREE=$(df -g /System/Volumes/Data 2>/dev/null | awk 'NR==2{print $4}'); : "${FREE:=}"
[ -n "$FREE" ] || FREE=$(df -BG / 2>/dev/null | awk 'NR==2{gsub(/G/,"",$4); print $4}')
# 80 GiB, not 40. The harvests write in bursts - collection 198 added 31 GB of press-release PDFs in one day -
# so a 40 GiB floor gives about two days' notice and an 80 GiB floor gives a fortnight. And the warning now names
# the collection that grew most in the last day, because "the disk is filling" without "this is what is filling
# it" leaves nothing to act on.
if [ -n "${FREE:-}" ] && [ "$FREE" -lt 80 ]; then
  BIG=$(cd "$COL/.." 2>/dev/null && for d in */; do
          [ -d "$d" ] || continue
          n=$(find "$d" -type f -mtime -1 -print0 2>/dev/null | xargs -0 stat -f %z 2>/dev/null \
              | awk '{s+=$1} END {printf "%.0f", s/1073741824}')
          [ "${n:-0}" -gt 0 ] && echo "$n $d"
        done | sort -rn | head -1)
  FAULTS="$FAULTS; only ${FREE} GiB of disk left${BIG:+ (grown most in the last day: ${BIG} GB)}"
fi

if [ -z "$FAULTS" ]; then
  echo "$(date -u +%FT%TZ) well | last run $(cut -c1-19 < "$LD" 2>/dev/null) | site built ${PBUILT:-?}" >> "$LOG"
  rm -f "$SEEN"; exit 0
fi

FAULTS="${FAULTS#; }"
if [ "$ONHOST" -ne 1 ]; then
  echo "$(date -u +%FT%TZ) off-host, not alerting | $FAULTS" >> "$LOG"
  exit 0
fi
echo "$(date -u +%FT%TZ) FAULT $FAULTS" >> "$LOG"
LAST=0; [ -f "$SEEN" ] && LAST=$(cat "$SEEN" 2>/dev/null || echo 0)
if [ $(( NOW - LAST )) -ge 21600 ]; then          # at most one alert every six hours
  bash s2/alert.sh "SYSTEM NOT RUNNING" "$FAULTS"
  echo "$NOW" > "$SEEN"
fi
exit 1
