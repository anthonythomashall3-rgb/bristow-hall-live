#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): the live tools' files between runs, kept as GitHub release assets (add-only).

The runner has no disk between runs. The files the State page, the stress map, the data page's Mac rows and the shadow tool read live in
the newest release tagged lts-base-<stamp> of this repository:
  base-<stamp>.tar.gz (+ .sha256)    every file, at its Mac path (Users/anthonyhall/Projects/..., Volumes/Sandisk G/...); built once on the
                                     Mac by make_base_on_mac.py, or here by 'rebase'
  delta-<stamp>.tar.gz (+ .sha256)   the files one run added or changed (refreshed inputs, their dated copies, the add-only feeds)
Each archive carries Users/anthonyhall/.lts/MANIFEST-<stamp>.sha256: the sha256 of EVERY state file after it. Nothing is ever deleted:
an asset once uploaded stays; a file a run replaced is still in the earlier archive.
  restore   download the base and every delta of the newest lts-base-* release, check each archive's sha256, unpack in order to /,
            then check every file against the newest manifest. Writes $LT_OUT/restored.json (path -> sha256).
  delta     after a run: hash the state files again; files new or changed since restore go into delta-<stamp>.tar.gz with the new full
            manifest, uploaded to the same release. Per-run outputs (pages, build outputs, logs) are not state and are left out (EXCLUDE).
  rebase    (when the release holds 60 deltas, or by hand) a new release lts-base-<stamp> with one archive of the whole current state.
Usage: state.py restore | delta [--no-upload] | rebase"""
import os, sys, io, re, json, time, hashlib, tarfile, subprocess, argparse
REPO = os.environ.get('GITHUB_REPOSITORY', 'anthonythomashall3-rgb/bristow-hall-live')
ROOTS = ['Users/anthonyhall/Projects', 'Volumes/Sandisk G']
OUT = os.environ.get('LT_OUT', '/tmp/lt_out'); DL = os.path.join(OUT, 'assets')
C52 = 'Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12/'
D32 = 'Users/anthonyhall/Projects/Onset Detector Data/1032_state_recession_indicator_all_states_dc_2026-11-09/'
SNAP = ['out/BH-STATE-CHRONOLOGY-V4-1032.csv', 'out/damage_line_v4_a198_1032.json', 'out/state_chronology_v4_a198_1032.json', 'out/TRIAL-state-class2-windows-a204-1032.csv',
        'out/trial_state_class2_a204_1032.json', 'out/state_class2_a205_1032.csv', 'out/state_class2_a205_1032.json', 'web/state-onset/index.html',
        'out/check_bands_have_damage_a185_1032.json', 'out/check_line_matches_class_a187_1032.json']
EXCLUDE = [re.compile(x) for x in (r'/__pycache__/', r'\.pyc$', r'\.tmp\d*$', r'\.tmp1052$',
           '^' + re.escape(C52) + r'(out|web|logs)/', '^' + re.escape(C52) + r'data/dated_copies/1032_out_asof_', '^' + re.escape(C52) + r'data/live_chronology/',
           '^' + re.escape(D32) + '(' + '|'.join(re.escape(s) for s in SNAP) + ')$',
           r'/_shared/[^/]*\.(sqlite|sqlite-wal|sqlite-shm|db|json|lock)$', r'/824_feeds_refresh_ender_plateau_2026-10-23/data/fetch_', r'/824_feeds_refresh_ender_plateau_2026-10-23/out/',
           r'/105_bristow_hall_system_2026-09-08/cloud(/|$)')]
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def sh(*a, check=True): r = subprocess.run(list(a), capture_output=True, text=True); (r.returncode and check) and sys.exit(f"{' '.join(a)[:200]}: {r.stderr[-600:]}"); return r.stdout
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def excluded(rel): return any(x.search(rel) for x in EXCLUDE)
def scan():
    S = {}
    for r in ROOTS:
        for dp, dn, fn in os.walk('/' + r):
            if os.path.islink(dp): dn[:] = []; continue
            dn[:] = [d for d in dn if not os.path.islink(os.path.join(dp, d))]
            for f in fn:
                p = os.path.join(dp, f); rel = p[1:]
                if os.path.islink(p) or excluded(rel): continue
                S[rel] = sha(p)
    return S
def releases():
    L = json.loads(sh('gh', 'release', 'list', '-R', REPO, '--limit', '200', '--json', 'tagName'))
    return sorted(x['tagName'] for x in L if x['tagName'].startswith('lts-base-'))
def assets(tag): return sorted(a['name'] for a in json.loads(sh('gh', 'release', 'view', tag, '-R', REPO, '--json', 'assets'))['assets'])
def manifest_of(tp):
    with tarfile.open(tp) as T:
        ms = [m for m in T.getmembers() if m.name.startswith('Users/anthonyhall/.lts/MANIFEST-')]
        b = T.extractfile(ms[-1]).read().decode()
    return {l[66:]: l[:64] for l in b.splitlines() if len(l) > 66}

def restore():
    tags = releases()
    if not tags: sys.exit('no lts-base-* release: the state has never been uploaded')
    tag = tags[-1]; A = assets(tag); arch = [a for a in A if a.endswith('.tar.gz')]
    base = [a for a in arch if a.startswith('base-')]; deltas = sorted(a for a in arch if a.startswith('delta-'))
    assert len(base) == 1, f'{tag}: {len(base)} base archives'
    os.makedirs(DL, exist_ok=True)
    sh('gh', 'release', 'download', tag, '-R', REPO, '-D', DL, '--clobber', '-p', '*.tar.gz', '-p', '*.sha256')
    order = base + deltas
    for a in order:
        want = open(os.path.join(DL, a + '.sha256')).read().split()[0]; got = sha(os.path.join(DL, a))
        if want != got: sys.exit(f'{a}: sha256 {got} is not the recorded {want}; nothing restored')
    for a in order:
        r = subprocess.run(['tar', '-xzf', os.path.join(DL, a), '-C', '/'], capture_output=True, text=True)
        if r.returncode: sys.exit(f'unpack {a}: {r.stderr[-400:]}')
    for d in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state_dirs.txt')):   # folders the tools' globs need (some hold no file)
        if d.strip(): os.makedirs('/' + d.strip(), exist_ok=True)
    M = manifest_of(os.path.join(DL, order[-1])); bad = [p for p, h in M.items() if not os.path.isfile('/' + p) or sha('/' + p) != h]
    if bad: sys.exit(f'{len(bad)} files do not match the newest manifest, e.g. {bad[:3]}')
    os.makedirs(OUT, exist_ok=True); json.dump(dict(tag=tag, archives=order, files=M), open(os.path.join(OUT, 'restored.json'), 'w'))
    log(f'restored {tag}: {len(order)} archives ({len(deltas)} deltas), {len(M)} files checked against the newest manifest')

def pack(name, rels, M):
    os.makedirs(DL, exist_ok=True); tp = os.path.join(DL, name)
    with tarfile.open(tp, 'w:gz', compresslevel=6) as T:
        for rel in sorted(rels): T.add('/' + rel, arcname=rel, recursive=False)
        mb = ''.join(f'{M[k]}  {k}\n' for k in sorted(M)).encode(); stamp = name.split('-', 1)[1].split('.')[0]
        ti = tarfile.TarInfo('Users/anthonyhall/.lts/MANIFEST-' + stamp + '.sha256'); ti.size = len(mb); ti.mtime = int(time.time()); T.addfile(ti, io.BytesIO(mb))
    open(tp + '.sha256', 'w').write(f'{sha(tp)}  {name}\n'); return tp

def delta(upload=True):
    R = json.load(open(os.path.join(OUT, 'restored.json'))); old = R['files']; now = scan()
    ch = sorted(p for p, h in now.items() if old.get(p) != h); gone = sorted(p for p in old if p not in now and not excluded(p))
    M = dict(old); M.update(now)          # a file missing now stays in the manifest: it is still in an earlier archive (nothing is deleted)
    rep = dict(tag=R['tag'], changed=len(ch), files=ch[:200], not_on_disk_now=gone[:50])
    if not ch: log('state: nothing new'); rep['uploaded'] = None
    else:
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()); tp = pack(f'delta-{stamp}.tar.gz', ch, M)
        log(f'state delta: {len(ch)} files, {os.path.getsize(tp)} bytes'); rep['uploaded'] = os.path.basename(tp)
        if upload: sh('gh', 'release', 'upload', R['tag'], '-R', REPO, tp, tp + '.sha256')
        if upload and sum(1 for a in assets(R['tag']) if a.startswith('delta-') and a.endswith('.tar.gz')) >= 60: rebase(M)
    json.dump(rep, open(os.path.join(OUT, 'state_delta.json'), 'w'), indent=1)

def rebase(M=None):
    """one archive of every state file: all of the manifest (base files the runs never change included), as on disk now"""
    if M is None:
        M = dict(json.load(open(os.path.join(OUT, 'restored.json')))['files']); M.update(scan())
    M = {p: sha('/' + p) for p in M if os.path.isfile('/' + p)}
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()); tag = 'lts-base-' + stamp
    tp = pack(f'base-{stamp}.tar.gz', list(M), M)
    sh('gh', 'release', 'create', tag, '-R', REPO, '--title', 'live tools state ' + stamp, '--notes',
       'Live tools state (1052): every file the State page, the stress map, the data page Mac rows and the shadow tool read, at their Mac paths. '
       'Add-only: earlier releases are kept. ops/live_tools/state.py.', '--latest=false', tp, tp + '.sha256')
    log('new base release', tag)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['restore', 'delta', 'rebase']); ap.add_argument('--no-upload', action='store_true'); a = ap.parse_args()
    {'restore': restore, 'delta': lambda: delta(not a.no_upload), 'rebase': rebase}[a.cmd]()
