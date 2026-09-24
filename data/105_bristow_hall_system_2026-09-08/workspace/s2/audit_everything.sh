#!/bin/bash
# THE WHOLE-SYSTEM AUDIT (18 September 2026).
#
# "Make sure nothing ever fails." Nothing can be guaranteed, but everything can be CHECKED, every time, by a
# script rather than by remembering. This checks the published site end to end - every page, every link, every
# served file - and the tool behind it, and prints one line per check with PASS or FAIL. It exits non-zero if
# anything failed, so it can be wired into the run and the watchdog.
#
#   bash s2/audit_everything.sh            check the live site and this machine
#   bash s2/audit_everything.sh --quiet    only the failures and the total
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/../.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
cd "$COL/workspace" || exit 1
exec python3 s2/audit_everything.py "$@"
