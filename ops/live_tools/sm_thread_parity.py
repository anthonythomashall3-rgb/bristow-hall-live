#!/usr/bin/env python3
"""PROBE ONLY (1167o, not for main): THE STRESS MAP WITH 4 BLAS THREADS AGAINST 2, BYTE FOR BYTE. No AI.

Adapted from sm_cache_parity.py (live-tools.yml mode=cache-parity).

The stress map is built twice on the same restored inputs: A with the county layer computed (as code/stress_map_v2_1052.py --all always
does; the result is stored), B with the county layer taken from the store (ops/live_tools/stress_map_cached.py). Every file the build
writes (out/stress_map_*, out/STRESS-MAP-*, out/county_shapes_*, web/stress-map/*) is compared byte for byte; a .gz file by its
decompressed content (gzip stamps the time it was written). A line that differs only by the build's own clock (the 'Built <time>' and
'HH:MM:SS' stamps) is listed apart. Writes $LT_OUT/sm_cache_parity.json; exit 1 on any other difference."""
import os, re, sys, glob, gzip, json, time, shutil, hashlib, subprocess
C = '/Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12'
HERE = os.path.dirname(os.path.abspath(__file__)); LT = os.environ.get('LT_OUT', '/tmp/lt_out'); os.makedirs(LT, exist_ok=True)
PAT = [os.path.join(C, 'out', p) for p in ('stress_map_*', 'STRESS-MAP-*', 'county_shapes_*')] + [os.path.join(C, 'web', 'stress-map', '*')]
# the build's own clock: its time stamps and the headless browser's page-load timings (milliseconds; they differ between any two builds)
CLOCK = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ|\b\d\d:\d\d:\d\d\b|"(?:seconds?|ms|load_s|dom|load)": [0-9.]+')


def snap(dst):
    os.makedirs(dst, exist_ok=True); got = {}
    for p in PAT:
        for f in glob.glob(p):
            if os.path.isfile(f):
                b = open(f, 'rb').read()
                if f.endswith('.gz'): b = gzip.decompress(b)
                k = os.path.relpath(f, C); got[k] = b
                if len(b) < 20_000_000:   # the small files kept for the record (the county tables are compared, not kept)
                    q = os.path.join(dst, k); os.makedirs(os.path.dirname(q), exist_ok=True); open(q, 'wb').write(b)
    return got


def build(cache, label, threads=None):
    env = dict(os.environ, SM_CACHE=cache, SM_CACHE_DIR=os.path.join(LT, 'sm_thread_parity_store_%s' % (threads or 'default')))
    env.pop('OPENBLAS_NUM_THREADS', None)
    if threads: env['OPENBLAS_NUM_THREADS'] = threads
    t = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, 'stress_map_cached.py'), '--all', '--procs', str(os.cpu_count() or 4)], env=env, cwd=C)
    print('%s: rc %d in %.0f s' % (label, r.returncode, time.time() - t), flush=True)
    rec = json.load(open(os.path.join(LT, 'sm_county_cache.json'))) if os.path.exists(os.path.join(LT, 'sm_county_cache.json')) else {}
    return r.returncode, round(time.time() - t, 1), rec


def main():
    # the same starting point for both builds: the build compares its v1 tests with those of the run before it, so the out/ and web/
    # folders are put back as they were before A
    pre = os.path.join(LT, 'pre'); shutil.rmtree(pre, ignore_errors=True)
    for d in ('out', os.path.join('web', 'stress-map')): shutil.copytree(os.path.join(C, d), os.path.join(pre, d))
    rcA, tA, recA = build('0', 'A: 4 BLAS threads (the default), county layer computed'); A = snap(os.path.join(LT, 'A'))
    for d in ('out', os.path.join('web', 'stress-map')): shutil.rmtree(os.path.join(C, d)); shutil.copytree(os.path.join(pre, d), os.path.join(C, d))
    rcB, tB, recB = build('0', 'B: 2 BLAS threads, county layer computed', '2'); B = snap(os.path.join(LT, 'B'))
    for d in ('out', os.path.join('web', 'stress-map')): shutil.rmtree(os.path.join(C, d)); shutil.copytree(os.path.join(pre, d), os.path.join(C, d))
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
    out['ok'] = rcA == 0 and rcB == 0 and recA.get('hit') is False and recB.get('hit') is False and not diff
    json.dump(out, open(os.path.join(LT, 'sm_thread_parity.json'), 'w'), indent=1)
    print(json.dumps({k: (v if k not in ('identical',) else len(v)) for k, v in out.items()}, indent=1)[:4000])
    print('SM THREAD PARITY', 'PASS' if out['ok'] else 'FAIL')
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
