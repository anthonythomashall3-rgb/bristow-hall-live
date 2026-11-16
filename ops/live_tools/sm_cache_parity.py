#!/usr/bin/env python3
"""PARITY OF THE CACHED COUNTY LAYER (speed program 1052, step 3). No AI. Runs on the live-tools runner (live-tools.yml mode=cache-parity).

The stress map is built twice on the same restored inputs: A with the county layer computed (as code/stress_map_v2_1052.py --all always
does; the result is stored), B with the county layer taken from the store (ops/live_tools/stress_map_cached.py). Every file the build
writes (out/stress_map_*, out/STRESS-MAP-*, out/county_shapes_*, web/stress-map/*) is compared byte for byte; a .gz file by its
decompressed content (gzip stamps the time it was written). A line that differs only by the build's own clock (the 'Built <time>' and
'HH:MM:SS' stamps) is listed apart. Writes $LT_OUT/sm_cache_parity.json; exit 1 on any other difference."""
import os, re, sys, glob, gzip, json, time, shutil, hashlib, subprocess
C = '/Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12'
HERE = os.path.dirname(os.path.abspath(__file__)); LT = os.environ.get('LT_OUT', '/tmp/lt_out'); os.makedirs(LT, exist_ok=True)
PAT = [os.path.join(C, 'out', p) for p in ('stress_map_*', 'STRESS-MAP-*', 'county_shapes_*')] + [os.path.join(C, 'web', 'stress-map', '*')]
CLOCK = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ|\b\d\d:\d\d:\d\d\b|"seconds?": [0-9.]+|"ms": [0-9.]+')


def snap(dst):
    os.makedirs(dst, exist_ok=True); got = {}
    for p in PAT:
        for f in glob.glob(p):
            if os.path.isfile(f):
                b = open(f, 'rb').read()
                if f.endswith('.gz'): b = gzip.decompress(b)
                k = os.path.relpath(f, C); got[k] = b
                q = os.path.join(dst, k); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(b)
    return got


def build(cache, label):
    env = dict(os.environ, SM_CACHE=cache, SM_CACHE_DIR=os.path.join(LT, 'sm_cache_parity_store'))
    t = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'stress_map_cached.py'), '--all', '--procs', str(os.cpu_count() or 4)], env=env, cwd=C)
    print('%s: rc %d in %.0f s' % (label, r.returncode, time.time() - t), flush=True)
    rec = json.load(open(os.path.join(LT, 'sm_county_cache.json'))) if os.path.exists(os.path.join(LT, 'sm_county_cache.json')) else {}
    return r.returncode, round(time.time() - t, 1), rec


def main():
    shutil.rmtree(os.path.join(LT, 'sm_cache_parity_store'), ignore_errors=True)
    # the same starting point for both builds: the build compares its v1 tests with those of the run before it, so the out/ and web/
    # folders are put back as they were before A
    pre = os.path.join(LT, 'pre'); shutil.rmtree(pre, ignore_errors=True)
    for d in ('out', os.path.join('web', 'stress-map')): shutil.copytree(os.path.join(C, d), os.path.join(pre, d))
    rcA, tA, recA = build('0', 'A full (county layer computed)'); A = snap(os.path.join(LT, 'A'))
    for d in ('out', os.path.join('web', 'stress-map')): shutil.rmtree(os.path.join(C, d)); shutil.copytree(os.path.join(pre, d), os.path.join(C, d))
    rcB, tB, recB = build('1', 'B incremental (county layer from the store)'); B = snap(os.path.join(LT, 'B'))
    same, clock_only, diff = [], [], []
    for k in sorted(set(A) | set(B)):
        a, b = A.get(k), B.get(k)
        if a == b: same.append(k); continue
        if a is not None and b is not None:
            la, lb = a.decode('utf-8', 'replace').splitlines(), b.decode('utf-8', 'replace').splitlines()
            if len(la) == len(lb) and all(x == y or CLOCK.sub('#', x) == CLOCK.sub('#', y) for x, y in zip(la, lb)):
                clock_only.append(dict(file=k, lines=[i for i, (x, y) in enumerate(zip(la, lb)) if x != y][:20])); continue
        diff.append(dict(file=k, A=None if a is None else hashlib.sha256(a).hexdigest(), B=None if b is None else hashlib.sha256(b).hexdigest()))
    out = dict(full_seconds=tA, incremental_seconds=tB, rc=[rcA, rcB], cache_A=recA, cache_B=recB, files=len(set(A) | set(B)),
               identical=same, clock_stamps_only=clock_only, different=diff)
    out['ok'] = rcA == 0 and rcB == 0 and recB.get('hit') is True and not diff
    json.dump(out, open(os.path.join(LT, 'sm_cache_parity.json'), 'w'), indent=1)
    print(json.dumps({k: (v if k not in ('identical',) else len(v)) for k, v in out.items()}, indent=1)[:4000])
    print('SM CACHE PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
