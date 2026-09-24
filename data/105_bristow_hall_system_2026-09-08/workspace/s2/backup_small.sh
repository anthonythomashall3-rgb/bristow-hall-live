#!/bin/bash
# THE SMALL BACKUP (18 September 2026).
#
# 163 GB sit in ~/Projects/Onset Detector Data with no Time Machine destination and no git remote. Most of that is
# harvested raw data that could be fetched again. What could NOT be fetched again is small: the code, the
# pre-registrations, the records, the manifests, the freezes and the commit history. A disk failure would cost the
# programme its evidence, not its downloads, and the evidence fits in a few megabytes.
#
# The first version of this script used an rsync include list and copied 5.2 GB - 24,547 Claude session
# transcripts and every zip and PDF in Recession Papers - into Dropbox before anyone could stop it. A backup that
# can quietly copy five gigabytes is a fault, not a backup. So this one BUILDS THE LIST FIRST, refuses outright if
# the total is over the cap, and says what the biggest contributors were. It copies nothing until it has measured.
#
#   bash s2/backup_small.sh          measure, then copy if under the cap
#   bash s2/backup_small.sh --dry    measure and report only
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/../.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
ROOT="$(cd "$COL/.." && pwd)"
PAPERS="$(cd "$ROOT/../Recession Papers" 2>/dev/null && pwd || echo '')"
DEST="${BHS_BACKUP_DIR:-$HOME/Dropbox/BristowHall-Backup}"
# A second copy on the USB stick when it is plugged in. It is FAT32 and 124 GB, so it can never hold the 164 GB
# collection - no symlinks, and the collection has 8,186 of them - but ninety megabytes of evidence is exactly
# what it is good for, and a copy that is not in the cloud is worth having. Absent stick, absent copy, no fault.
USB=""
for _u in /Volumes/*/; do
  case "$_u" in (/Volumes/Macintosh*|"/Volumes/$(hostname -s)"*) continue;; esac
  [ -d "$_u" ] && [ -w "$_u" ] && USB="${_u}BristowHall-Backup" && break
done
CAP_MB="${BHS_BACKUP_CAP_MB:-200}"        # refuse above this; the honest figure is about twenty
MAXFILE_KB=2048                            # no single evidence file is bigger than this
STAMP="$(date -u +%FT%TZ)"
DRY=""; [ "${1:-}" = "--dry" ] && DRY=1

[ -d "$(dirname "$DEST")" ] || { echo "no backup destination at $(dirname "$DEST"); set BHS_BACKUP_DIR"; exit 1; }
LIST="$(mktemp)"; trap 'rm -f "$LIST"' EXIT

# Evidence only, by name, with the directories that hold downloads and transcripts cut out by path. Note what is
# NOT here: *.jsonl (session transcripts and ledgers), *.zip, *.pdf, *.csv other than MANIFEST, anything in repo/
# or __pycache__ or .git, and any directory whose name begins with -Users- (Claude's own per-folder log dumps).
collect() {
  local base="$1"; [ -d "$base" ] || return 0
  find "$base" \
    \( -type d \( -name '__pycache__' -o -name '.git' -o -name 'repo' -o -name 'node_modules' -o -name '-Users-*' \
                 -o -name 'venv' -o -name '.venv' -o -name 'site-packages' -o -name 'env' -o -name 'dist' \
                 -o -name 'build' -o -name '.mypy_cache' -o -name '.pytest_cache' \) -prune \) -o \
    -type f \( -name '*.py' -o -name '*.sh' -o -name '*.js' -o -name '*.toml' -o -name '*.md' \
               -o -name 'MANIFEST*.csv' -o -name 'RECORD-*' -o -name 'PREREG-*' -o -name 'FREEZE-*' \) \
    ! -name '*.bak' ! -name '*.bak_*' ! -path '*/.git/*' \
    -size -${MAXFILE_KB}k -print 2>/dev/null
}
collect "$ROOT"   >> "$LIST"
collect "$PAPERS" >> "$LIST"
# A freeze file is 0.6 MB and one is written on every refreeze. Each carries its own diff from the one before, so
# the newest few plus the chain of recorded ids is the evidence; the older bodies are not.
python3 - "$LIST" <<'PYEOF'
import sys, os, re
p = sys.argv[1]
lines = [l.rstrip('\n') for l in open(p, encoding='utf-8', errors='replace')]
fr = [l for l in lines if re.search(r'/FREEZE-[^/]*\.json$', l)]
keep = set(sorted(fr, key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)[-3:])
out = [l for l in lines if l not in fr or l in keep]
open(p, 'w').write('\n'.join(out) + ('\n' if out else ''))
PYEOF

N=$(wc -l < "$LIST" | tr -d ' ')
# Measuring this list defeated two shell attempts. `xargs -d` is GNU-only and returned nothing on macOS; the NUL
# form worked but xargs splits twenty thousand paths across several du runs and `tail -1` then took only the last
# batch, so the total came out under a megabyte. Both failures reported a SMALL number, which a cap treats as
# permission - the worst possible direction for a bug in a guard to fail. python3 is already a hard dependency
# here and counts the list once, and a non-numeric or zero answer is now refused rather than believed.
KB=$(python3 -c '
import sys, os
t = 0
for ln in open(sys.argv[1], encoding="utf-8", errors="replace"):
    p = ln.rstrip("\n")
    try: t += os.path.getsize(p)
    except OSError: pass
print(t // 1024)' "$LIST" 2>/dev/null)
case "${KB:-}" in (''|*[!0-9]*) echo "REFUSED: could not measure the list"; exit 3;; esac
[ "$KB" -gt 0 ] || { echo "REFUSED: measured zero bytes for $N files; the measurement is broken"; exit 3; }
MB=$(( KB / 1024 ))
echo "$STAMP would copy $N files, ${MB} MB (cap ${CAP_MB} MB)"
if [ "$MB" -gt "$CAP_MB" ]; then
  echo "REFUSED: over the cap. The ten biggest:"
  python3 -c '
import sys, os
r = []
for ln in open(sys.argv[1], encoding="utf-8", errors="replace"):
    p = ln.rstrip("\n")
    try: r.append((os.path.getsize(p), p))
    except OSError: pass
for n, p in sorted(r, reverse=True)[:10]: print("  %6.1f MB  %s" % (n / 1048576.0, p))' "$LIST" 
  exit 2
fi
[ -n "$DRY" ] && { echo "dry run; nothing copied"; exit 0; }

mkdir -p "$DEST" 2>/dev/null
rsync -a --delete --files-from="$LIST" / "$DEST/" 2>/dev/null
[ -d "$COL/workspace/.git" ] && git -C "$COL/workspace" bundle create "$DEST/workspace-repo.bundle" --all >/dev/null 2>&1
SZ=$(du -sh "$DEST" 2>/dev/null | awk '{print $1}')
echo "$STAMP backed up: $N files, $SZ, to $DEST" | tee -a "$DEST/BACKUP.log"
if [ -n "$USB" ]; then
  mkdir -p "$USB" 2>/dev/null
  # -L follows symlinks and copies what they point at, because FAT32 cannot store a link
  if rsync -rLt --delete --files-from="$LIST" / "$USB/" 2>/dev/null; then
    [ -f "$DEST/workspace-repo.bundle" ] && cp "$DEST/workspace-repo.bundle" "$USB/" 2>/dev/null
    echo "$STAMP second copy on the stick: $USB" | tee -a "$DEST/BACKUP.log"
  else
    echo "$STAMP the stick refused the copy (FAT32 or unplugged mid-write): $USB" | tee -a "$DEST/BACKUP.log"
  fi
fi
