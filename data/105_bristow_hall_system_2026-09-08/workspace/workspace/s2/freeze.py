# -*- coding: utf-8 -*-
"""THE FREEZE (18 September 2026; collection 202; open-register item 24, work order 0.1).

The rule of record is a chain of files that exec one another, so an edit to any ancestor changes the rule in silence.
This writes down exactly what the rule was: the sha256 of every file it runs and every file it reads, under the
version it claims to be. Nothing here changes the rule; it only records it.

What is hashed:
  code      the exec chain followed from the walk named in cache/bhs_version.json, plus the drivers the runner calls
  lines     the walk's chosen parameters (cache/<var>_prog.pkl) and the version file
  tables    the carried-leg table, the leg release calendar, the closer caches
  data      every series file the build reads, by the same patterns the build's own fingerprint uses

Run from the workspace:
    python3 s2/freeze.py                 write the freeze for the live version
    python3 s2/freeze.py --check         compare today's files with the freeze on file; exit 1 on any difference

The freeze lands in ../freeze/FREEZE-<version>-<date>.json and a copy in Recession Papers. A difference is not an
error by itself - the rule may have been changed on purpose - but it must never be a surprise.
"""
import os, sys, json, re, glob, hashlib, datetime

W = os.getcwd()
COL = os.path.dirname(W)
OUT = os.path.join(COL, 'freeze')
PAPERS = os.path.expanduser('~/Projects/Recession Papers')
ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/Projects/Onset Detector Data')

DRIVERS = ['bhs_run.sh', 'bhs_build.py', 'bhs_site.py', 'bhs_update.py', 'bhs_schedule.py', 'bhs_dol_press.py',
           'bhs_calendar_fetch.py', 'deploy.sh', 's2/q41_data_check.py', 's2/deploy_gate.py', 's2/alert.sh',
           's2/home_tiles.py', 's2/live_sources.py', 's2/state539_live.py', 's2/state_press_live.py',
           's2/search_week.py', 's2/asof_trough.py', 's2/asof_objects.py', 's2/asof_permits.py', 's2/fast_buildv.py',
           's2/freeze.py', 's2/ledger.py', 's2/cmpstate.py', 's2/score_record.py', 's2/watchdog.sh',
           's2/audit_everything.py', 's2/audit_everything.sh', 's2/backup_small.sh']

DATA_PATTERNS = [
    os.path.join(ROOT, '24_bristow_rule_lab', 'workspace', 'lab', 'data', 'fred_weekly', '*.csv'),
    os.path.join(ROOT, '24_bristow_rule_lab', 'workspace', 'lab', 'vac', '*.csv'),
    os.path.join(ROOT, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages', '*_all_vintages.csv'),
    os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'vintages', '*.csv'),
    os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data', '*.csv'),
    os.path.join(ROOT, '45_dol_first_prints_2026-09', '*.csv'),
    os.path.join(ROOT, '189_walk_from_1948_2026-09-16', 'out', 'v355', '*.csv'),
    'cache/objects.pkl', 'cache/alfred_first_*.csv', 'cache/relcal_*.csv', 'cache/surveys/*.csv',
    'cache/SAHMREALTIME.csv', 'cache/leg_release_dates.json', 'cache/bhs_version.json', 'cache/*_prog.pkl',
]


def _bridged(path):
    """Several of the rule's vintage inputs are symbolic links whose targets are written as absolute paths under
    /Users/<name>/Projects/Onset Detector Data. Read from anywhere but that Mac - the Linux side of the bridge,
    a second machine, a restored backup under a different home - those links dangle and the freeze reports five
    of the rule's own inputs as ABSENT, which is the one thing an integrity check must never say falsely. If a
    path is missing, follow its link text and re-root it on this machine's collection before giving up."""
    if os.path.exists(path): return path
    try: tgt = os.readlink(path)
    except OSError: return path
    marker = 'Onset Detector Data' + os.sep
    i = tgt.find(marker)
    if i < 0: return path
    alt = os.path.join(ROOT, tgt[i + len(marker):])
    return alt if os.path.exists(alt) else path


def sha(path):
    h = hashlib.sha256()
    with open(_bridged(path), 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def chain():
    """every file the rule runs: the walk named in the version file, and whatever it and its ancestors exec by name"""
    vers = json.load(open('cache/bhs_version.json'))
    seen, stack = [], [vers['walk']] + DRIVERS
    while stack:
        f = stack.pop(0)
        if f in seen or not os.path.exists(f): continue
        seen.append(f)
        if not f.endswith('.py'): continue
        for m in re.finditer(r"""exec\(open\(['"]([^'"]+)['"]\)""", open(f, encoding='utf-8', errors='replace').read()):
            if m.group(1) not in seen: stack.append(m.group(1))
    return vers, sorted(seen)


def collect():
    vers, files = chain()
    code = {f: sha(f) for f in files if os.path.exists(f)}
    data = {}
    for pat in DATA_PATTERNS:
        for f in sorted(glob.glob(pat)):
            if os.path.isfile(_bridged(f)): data[os.path.relpath(f, ROOT) if f.startswith(ROOT) else f] = sha(f)
    return vers, code, data


def _freezes():
    """every freeze on file, oldest first by its OWN recorded UTC stamp rather than by filename. Two freezes made
    the same day - one from the Mac in local time, one from the Linux side of the bridge in UTC - sorted by name in
    the wrong order, so --check compared against a freeze that was not the latest one."""
    out = []
    for p in glob.glob(os.path.join(OUT, 'FREEZE-*.json')):
        try: out.append((json.load(open(p)).get('frozen_at') or '', p))
        except Exception: continue
    return [p for _t, p in sorted(out)]


def main():
    vers, code, data = collect()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rec = {'version': vers['version'], 'walk': vers['walk'], 'var': vers['var'], 'frozen_at': stamp,
           'n_code': len(code), 'n_data': len(data), 'code': code, 'data': data,
           'note': 'sha256 of every file the live rule runs and reads; written by s2/freeze.py (collection 202)'}
    rec['freeze_id'] = hashlib.sha256(json.dumps({'code': code, 'data': data}, sort_keys=True).encode()).hexdigest()

    if '--check' in sys.argv:
        olds = _freezes()
        if not olds: print('freeze: none on file; run without --check first'); return 1
        old = json.load(open(olds[-1]))
        bad = 0
        for kind in ('code', 'data'):
            o, n = old.get(kind, {}), rec[kind]
            for k in sorted(set(o) | set(n)):
                if o.get(k) != n.get(k):
                    bad += 1
                    print('%-6s %-58s %s -> %s' % (kind, k[-58:], (o.get(k) or 'absent')[:12], (n.get(k) or 'absent')[:12]))
        print('freeze %s (%s): %d file(s) differ from %s' % (old['version'], os.path.basename(olds[-1]), bad, old['frozen_at']))
        return 1 if bad else 0

    os.makedirs(OUT, exist_ok=True)
    # Every freeze carries its own diff from the one before it, so the history says what moved between them
    # without anyone having to line two files up by hand. A freeze whose changed list is empty of walk and build
    # files is a harness change, not a rule change, and the record should be able to show that on its face.
    olds = _freezes()
    if olds:
        prev = json.load(open(olds[-1]))
        ch = {}
        for kind in ('code', 'data'):
            o, n = prev.get(kind, {}), rec[kind]
            d = [k for k in sorted(set(o) | set(n)) if o.get(k) != n.get(k)]
            if d: ch[kind] = d
        rec['previous'] = os.path.basename(olds[-1])
        rec['previous_freeze_id'] = prev.get('freeze_id')
        rec['changed_since_previous'] = ch
    # One freeze per day used to overwrite the last, so a second freeze on the same date destroyed the
    # version it was recording a diff against - the chain pointed at a file that no longer held that
    # content. A same-day refreeze now gets the hour and minute and the history stays whole.
    p = os.path.join(OUT, 'FREEZE-%s-%s.json' % (vers['version'], datetime.date.today().isoformat()))
    if os.path.exists(p):
        p = os.path.join(OUT, 'FREEZE-%s-%sT%s.json' % (vers['version'], datetime.date.today().isoformat(),
                                                        datetime.datetime.now(datetime.timezone.utc).strftime('%H%MZ')))
    json.dump(rec, open(p, 'w'), indent=1, sort_keys=True)
    short = {k: rec[k] for k in ('version', 'walk', 'var', 'frozen_at', 'freeze_id', 'n_code', 'n_data')}
    if os.path.isdir(PAPERS):
        json.dump(short, open(os.path.join(PAPERS, 'BRISTOW-HALL-RULE-FREEZE-%s.json' % vers['version']), 'w'), indent=1)
    print('freeze %s: %d code files, %d data files, id %s' % (vers['version'], len(code), len(data), rec['freeze_id'][:16]))
    print('written', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
