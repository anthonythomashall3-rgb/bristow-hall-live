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


# v3.69 (22 September 2026, collection 302; the live-ops audit). Since 21 September 2026 the cloud repository is the live system's home and the
# source of truth for its data: it appends production vintages, policy days, breadth months, claims weeks, S&P closes and
# the forward ledger every day. Rebuilding the bundle from the Mac would put the Mac's older copies over them. It now runs
# only when asked (--rebuild-from-mac), and even then never replaces a cloud file that already holds everything the Mac's
# copy holds and more.
def _safe_copy(src, dst):
    """copy src over dst unless dst already begins with src's bytes and is longer (the cloud is ahead); returns True if copied"""
    try:
        if os.path.exists(dst) and os.path.getsize(dst) > os.path.getsize(src):
            with open(src, 'rb') as a, open(dst, 'rb') as b:
                if b.read(os.path.getsize(src)) == a.read(): return False
    except Exception: pass
    shutil.copyfile(src, dst); return True


def main():
    if '--rebuild-from-mac' not in sys.argv:
        print('cloud_bundle: the cloud repository is the live system\'s home since 21 September 2026; rebuilding it from the '
              'Mac would overwrite the data it appends every day. Run with --rebuild-from-mac only to rebuild on purpose '
              '(files the cloud has extended are kept).'); return 2
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the workspace
    os.chdir(here)
    # the freeze stores data paths relative to the DATA ROOT (Onset Detector Data), which is two levels above the
    # workspace, not one. The first run of this resolved them against the collection and found 94 of 4,434.
    root = os.path.dirname(os.path.dirname(here))
    out = os.path.join(os.path.dirname(here), 'cloud')   # beside the workspace, not inside its repo
    if '--out' in sys.argv: out = sys.argv[sys.argv.index('--out') + 1]

    # the code lives where the chain expects it: inside the data root, so one symlink makes every hardcoded path
    # in the rule resolve on a runner without editing a single file.
    CODEDIR = os.path.join('data', os.path.basename(os.path.dirname(here)), 'workspace')
    fz = sorted(glob.glob('../freeze/FREEZE-*.json'))
    if not fz: print('no freeze on file; run s2/freeze.py first'); return 1
    F = json.load(open(fz[-1]))

    # the traced read set, folded in the same way the freeze does, so the bundle carries what the rule actually
    # reads and not only what the freeze's hand-written patterns happened to name
    extra = []
    try:
        rs = json.load(open(os.path.join('out', 'read_set.json')))
        for p in rs.get('paths') or []:
            f2 = p if os.path.isabs(p) else os.path.join(root, p)
            if os.path.isfile(f2) and f2.startswith(root):
                extra.append(os.path.relpath(f2, root))
    except Exception:
        pass

    # the traced IMPORT set, and every python file that sits beside one. Reading a file and importing a module
    # are different acts and only the first went through `open`: the runner died on `late_screen`, three imports
    # deep in collection 187, after the read set was already complete. A module's own directory comes with it
    # because the chain also shells out, and a subprocess's imports are invisible to both tracers.
    mod_dirs = set()
    try:
        for p_ in (rs.get('modules') or []):
            f2 = p_ if os.path.isabs(p_) else os.path.join(root, p_)
            if os.path.isfile(f2) and f2.startswith(root):
                mod_dirs.add(os.path.dirname(f2))
    except Exception:
        pass

    n_data = n_code = skipped = 0
    bytes_ = 0
    for rel in sorted(set(F['data']) | set(extra)):
        src = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.exists(src): src = os.path.join(here, rel)
        if not os.path.exists(src): skipped += 1; continue
        dst = os.path.join(out, 'data', rel.lstrip('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not _safe_copy(os.path.realpath(src), dst): skipped += 1; continue   # v3.69: the cloud is ahead
        n_data += 1; bytes_ += os.path.getsize(dst)

    # the code: every python and shell file in the workspace, minus backups, caches and outputs
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = [d for d in dirnames
                       if d not in ('__pycache__', '.git', 'cloud', 'out', 'cache', 'site', 'venv', '.venv')
                       and not d.startswith('_v3')]
        for fn in filenames:
            if not fn.endswith(('.py', '.sh')) or '.bak' in fn: continue
            src = os.path.join(dirpath, fn)
            dst = os.path.join(out, CODEDIR, os.path.relpath(src, '.'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst); n_code += 1; bytes_ += os.path.getsize(dst)

    # the caches the build needs that are not in the freeze's data list
    # fred_meta.json matters more than it looks: without it the runner does not know what it already has and
    # asks FRED for everything, which the first cloud run answered with 429 Too Many Requests. With it, the runner
    # starts warm and pulls only what changed, exactly as the Mac does.
    # THE WHOLE CACHE, minus the other walks' summaries. Naming cache files one at a time cost five cloud runs -
    # weekly_iur_prewar.csv was the last - and the directory is 117 MB of which the other walks' pickles are most.
    # Everything the build might reach for is cheaper to carry than to guess at.
    cache_pats = ['cache/**/*']
    for pat in cache_pats:
        for src in glob.glob(pat, recursive=True):
            if not os.path.isfile(src): continue
            base = os.path.basename(src)
            # the other walks' summaries are large and only walk 94 is live
            if base.endswith(('_sum.pkl', '_prog.pkl')) and not base.startswith('w94'): continue
            if base.endswith(('.log', '.out')) or 'run.lock' in src: continue
            dst = os.path.join(out, CODEDIR, src)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not _safe_copy(src, dst): continue   # v3.69: a cache file the cloud has extended is kept
            n_code += 1; bytes_ += os.path.getsize(dst)

    # Code in OTHER collections that the chain shells out to. The tracer watches `open`, so it cannot see a
    # subprocess: the cloud runner reported three of these missing one run at a time. Listed explicitly.
    for pat in ('191_standing_collector_*/code/*.py', '191_standing_collector_*/code/*.json',
                '190_month_standard_and_hf_legs_*/code/*.py', '190_month_standard_and_hf_legs_*/code/*.json',
                '177_new_legs_priced_*/code/*.py', '176_financial_leg_conjunction_*/code/*.py',
                '186_realtime_channels_*/code/*.py', '121_warn_causal_breadth_*/code/*.py',
                '108_high_frequency_speed_*/code/*.py', '_shared/*.py',
                # every python file in the collections the chain touches, wherever it sits. Selecting
                # directories one at a time cost four cloud runs - lab/slack/objects.py was the last of them -
                # and the whole set is 663 files and 4 MB. Code is cheap; guessing which code is not.
                '24_bristow_rule_lab/**/*.py', '189_walk_from_1948_*/**/*.py', '183_transmission_channels_*/**/*.py',
                # the standing collector's derived series: the high-frequency channels read them, 230 files
                # and nine megabytes, and the runner found them missing one directory at a time
                '191_standing_collector_*/warehouse/*/derived/*.csv',
                '191_standing_collector_*/warehouse/*/*/derived/*.csv'):
        for src in glob.glob(os.path.join(root, pat), recursive=True):
            if any(x in src for x in ('/venv/', '/.venv/', '/__pycache__/', '/node_modules/')): continue
            dst = os.path.join(out, 'data', os.path.relpath(src, root))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.realpath(src), dst); n_code += 1; bytes_ += os.path.getsize(dst)

    # Every python file in every collection the chain touched at all. Eleven cloud runs died on a missing
    # module or a missing file, each one named by the run before it, because the bundle was assembled from
    # guesses about which directories mattered. Python files are small; the whole set is a few megabytes.
    # Carrying all of them in the touched collections ends the class of failure rather than its latest member.
    touched = set()
    for rel in list(F['data']) + list(extra):
        r = rel.lstrip('/')
        if os.path.isabs(rel):
            continue
        top = r.split(os.sep)[0]
        if top and top != os.path.basename(os.path.dirname(here)):
            touched.add(top)
    for d_ in sorted(mod_dirs):
        r = os.path.relpath(d_, root)
        if not r.startswith('..'):
            touched.add(r.split(os.sep)[0])
    for top in sorted(touched):
        base = os.path.join(root, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in ('__pycache__', '.git', 'venv', '.venv', 'node_modules')]
            for fn in filenames:
                if not fn.endswith('.py'):
                    continue
                src = os.path.join(dirpath, fn)
                dst = os.path.join(out, 'data', os.path.relpath(src, root))
                if os.path.exists(dst):
                    continue
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(os.path.realpath(src), dst)
                    n_code += 1; bytes_ += os.path.getsize(dst)
                except OSError:
                    pass

    # every python file beside a module the chain imported
    for d in sorted(mod_dirs):
        if any(x in d for x in ('/venv/', '/.venv/', '/__pycache__/', '/node_modules/')): continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(('.py', '.json')): continue
            src = os.path.join(d, fn)
            if not os.path.isfile(src): continue
            dst = os.path.join(out, 'data', os.path.relpath(src, root))
            if os.path.exists(dst): continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.realpath(src), dst); n_code += 1; bytes_ += os.path.getsize(dst)

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
