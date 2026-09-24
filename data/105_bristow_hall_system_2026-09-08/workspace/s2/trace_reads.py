# -*- coding: utf-8 -*-
"""WHAT DOES THE RULE ACTUALLY READ? (18 September 2026)

The freeze claims to list every file the rule reads, and it does not: it lists seven directory patterns written by
hand, and the cloud runner found files outside them one at a time - sp500_daily_yahoo.csv was the third. A hand
list will always have holes. This finds the true set by watching.

It wraps `open` and pandas' readers, runs the update and the build, and writes every path that was actually read
from outside the workspace. The result is the honest input list: what the freeze should cover, and what the cloud
bundle must carry.

    python3 s2/trace_reads.py            run it and write out/read_set.json
"""
import os, sys, json, builtins, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(HERE); sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
# The same collection is reachable by two names on this Mac - ~/Projects/Onset Detector Data and the ~/mnt
# bridge - and the chain uses both. Recorded as they come, 3,983 of 4,099 traced reads sat outside ROOT and the
# cloud bundle skipped every one of them: it was carrying the freeze's hand-written patterns and almost nothing
# the tracer found. Both names fold to ROOT here, at the source, so nothing downstream has to know.
_ALIAS = [os.path.expanduser('~/mnt/Onset Detector Data'),
          os.path.expanduser('~/Projects/Onset Detector Data'),
          os.path.expanduser('~/Desktop/Onset Detector Data')]


def _norm(p):
    for a in _ALIAS:
        if a != ROOT and p.startswith(a + os.sep):
            return os.path.join(ROOT, p[len(a) + 1:])
    return p


SEEN = set()
_open = builtins.open


def _watch(path, mode='r', *a, **k):
    try:
        if isinstance(path, (str, bytes, os.PathLike)) and 'w' not in str(mode) and 'a' not in str(mode):
            p = _norm(os.path.abspath(os.fspath(path)))
            if os.path.exists(p) and not p.startswith(HERE): SEEN.add(p)
    except Exception:
        pass
    return _open(path, mode, *a, **k)


builtins.open = _watch
import pandas as pd                                                   # noqa: E402
for name in ('read_csv', 'read_excel', 'read_pickle', 'read_json'):
    fn = getattr(pd, name)
    def mk(fn):
        def w(path, *a, **k):
            try:
                if isinstance(path, (str, os.PathLike)):
                    p = _norm(os.path.abspath(os.fspath(path)))
                    if os.path.exists(p) and not p.startswith(HERE): SEEN.add(p)
            except Exception: pass
            return fn(path, *a, **k)
        return w
    setattr(pd, name, mk(fn))


def run(script):
    g = {'__name__': '__main__', '__file__': os.path.abspath(script)}
    sys.argv = [script, '--no-build'] if 'update' in script else [script]
    try:
        exec(compile(_open(script).read(), script, 'exec'), g)
    except SystemExit:
        pass
    except Exception as e:
        print('  %s stopped: %s: %s' % (script, type(e).__name__, str(e)[:100]))


def imported():
    """every module the chain actually imported that lives in the collection

    Reading a file and importing a module are different acts, and only the first went through `open`. The cloud
    runner died on `late_screen`, a module three imports deep in a collection the bundle did not carry, after it
    had already died on files. Watching `sys.modules` after the chain has run gives the import side of the same
    honest list.
    """
    out = set()
    for m in list(sys.modules.values()):
        f = getattr(m, '__file__', None)
        if not f:
            continue
        try:
            q = _norm(os.path.abspath(f))
        except Exception:
            continue
        if q.startswith(HERE) or not q.startswith(ROOT):
            continue
        if os.path.exists(q):
            out.add(q)
    return out


def main():
    for s in ('bhs_update.py', 'bhs_build.py', 'bhs_site.py'):
        print('tracing', s, flush=True); run(s)
    MODS = imported()
    rel = sorted(os.path.relpath(p, ROOT) if p.startswith(ROOT) else p for p in SEEN)
    mrel = sorted(os.path.relpath(p, ROOT) for p in MODS)
    os.makedirs('out', exist_ok=True)
    json.dump(dict(generated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                   root=ROOT, count=len(rel), paths=rel,
                   module_count=len(mrel), modules=mrel), _open('out/read_set.json', 'w'), indent=1)
    print('\nmodules imported from outside the workspace: %d' % len(mrel))
    mtops = {}
    for r in mrel: mtops[r.split(os.sep)[0]] = mtops.get(r.split(os.sep)[0], 0) + 1
    for k, v in sorted(mtops.items(), key=lambda x: -x[1]): print('   %5d  %s' % (v, k))
    print('\nfiles read from outside the workspace: %d' % len(rel))
    tops = {}
    for r in rel: tops[r.split(os.sep)[0]] = tops.get(r.split(os.sep)[0], 0) + 1
    for k, v in sorted(tops.items(), key=lambda x: -x[1]): print('   %5d  %s' % (v, k))
    # what the current freeze misses
    import glob
    fz = sorted(glob.glob('../freeze/FREEZE-*.json'))
    if fz:
        have = set(json.load(_open(fz[-1]))['data'])
        miss = [r for r in rel if r not in have]
        print('\nread but NOT in the freeze: %d' % len(miss))
        for m in miss[:20]: print('   %s' % m)
        json.dump(miss, _open('out/read_set_missing_from_freeze.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
