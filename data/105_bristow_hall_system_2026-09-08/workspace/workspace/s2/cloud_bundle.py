# -*- coding: utf-8 -*-
"""ASSEMBLE THE CLOUD BUNDLE (18 September 2026).

Anthony does not disable sleep, so the Mac misses slots. The site itself never goes down - it is static files on
Cloudflare - but the UPDATING stops with the laptop. The fix is to run the update somewhere that never sleeps.

That is possible because the live rule is small. The whole collection is 164 GB, but the rule READS only 351 MB
across 4,434 files, none bigger than 19 MB, and the freeze already lists every one of them by name. This copies
exactly those, plus the code, into a folder that can be pushed to a repository and run by a scheduled job.

    python3 s2/cloud_bundle.py [--out DIR]     default: <collection>/cloud

Symlinks are dereferenced: five of the rule's vintage inputs are links to absolute paths under one Mac's home and
would arrive dangling anywhere else.
"""
import os, sys, json, glob, shutil, hashlib, datetime


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the workspace
    os.chdir(here)
    # the freeze stores data paths relative to the DATA ROOT (Onset Detector Data), which is two levels above the
    # workspace, not one. The first run of this resolved them against the collection and found 94 of 4,434.
    root = os.path.dirname(os.path.dirname(here))
    out = os.path.join(os.path.dirname(here), 'cloud')   # beside the workspace, not inside its repo
    if '--out' in sys.argv: out = sys.argv[sys.argv.index('--out') + 1]

    fz = sorted(glob.glob('../freeze/FREEZE-*.json'))
    if not fz: print('no freeze on file; run s2/freeze.py first'); return 1
    F = json.load(open(fz[-1]))

    n_data = n_code = skipped = 0
    bytes_ = 0
    for rel in F['data']:
        src = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.exists(src): src = os.path.join(here, rel)
        if not os.path.exists(src): skipped += 1; continue
        dst = os.path.join(out, 'data', rel.lstrip('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.realpath(src), dst)     # realpath: FAT32 and git alike dislike dangling links
        n_data += 1; bytes_ += os.path.getsize(dst)

    # the code: every python and shell file in the workspace, minus backups, caches and outputs
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = [d for d in dirnames
                       if d not in ('__pycache__', '.git', 'cloud', 'out', 'cache', 'site', 'venv', '.venv')
                       and not d.startswith('_v3')]
        for fn in filenames:
            if not fn.endswith(('.py', '.sh')) or '.bak' in fn: continue
            src = os.path.join(dirpath, fn)
            dst = os.path.join(out, 'workspace', os.path.relpath(src, '.'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst); n_code += 1; bytes_ += os.path.getsize(dst)

    # the caches the build needs that are not in the freeze's data list
    # fred_meta.json matters more than it looks: without it the runner does not know what it already has and
    # asks FRED for everything, which the first cloud run answered with 429 Too Many Requests. With it, the runner
    # starts warm and pulls only what changed, exactly as the Mac does.
    for pat in ('cache/bhs_version.json', 'cache/w94_sum.pkl', 'cache/w94_prog.pkl', 'cache/objects.pkl',
                'cache/release_schedule.csv', 'cache/claims_release_dates.csv', 'cache/leg_mechanisms.json',
                'cache/fred_meta.json', 'cache/leg_release_dates.json', 'cache/SAHMREALTIME.csv',
                'cache/alfred_first_*.csv', 'cache/relcal_*.csv', 'cache/surveys/*.csv',
                'cache/daily_readings.pkl', 'cache/opening_scores_*.pkl', 'cache/closers/*.pkl'):
        for src in glob.glob(pat):
            dst = os.path.join(out, 'workspace', src)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst); n_code += 1; bytes_ += os.path.getsize(dst)

    man = dict(built=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               freeze=os.path.basename(fz[-1]), freeze_id=F.get('freeze_id'),
               version=F.get('version'), walk=F.get('walk'),
               data_files=n_data, code_files=n_code, missing=skipped,
               megabytes=round(bytes_ / 1048576, 1))
    os.makedirs(out, exist_ok=True)
    json.dump(man, open(os.path.join(out, 'BUNDLE.json'), 'w'), indent=1)
    print(json.dumps(man, indent=1))
    if skipped: print('WARNING: %d files in the freeze could not be found and are NOT in the bundle' % skipped)
    return 0


if __name__ == '__main__':
    sys.exit(main())
