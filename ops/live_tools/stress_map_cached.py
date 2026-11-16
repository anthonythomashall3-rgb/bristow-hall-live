#!/usr/bin/env python3
"""THE STRESS MAP WITH ITS COUNTY LAYER CACHED (speed program 1052, step 3; 16 November 2026). No AI.

code/stress_map_v2_1052.py --all spends 23 of its 26 minutes on the county layer (C0: the State chronology v4 code on 3,143 counties).
That layer depends only on the county inputs - the county outlines, the county unemployment rates (LAUS, held file or the run's fetch),
QCEW county jobs - and on the code that colours them. A BLS State release, the ETA 539 file or the jobs report changes none of them.

This runs the same script unchanged (its own main(), same arguments, same working folder) with one function wrapped: step_counties.
Its result (the county-month table, the county periods, the info dict and the Amendment 5 note) is stored under the SHA-256 of
everything it reads: the bytes of the stress-map, v1 and v3.1 scripts and the disturbance modules they import, the county outlines it
was given, the county unemployment table it was given (row for row), every QCEW county file, the v3/v3.1 switches and the start month.
Same key = same inputs = the stored result, and the two county files the function writes are written again from it exactly as the
function writes them. Any change of any input or of the code = a new key = the full computation. The tool's outputs are byte-identical
either way (ops/live_tools/sm_cache_parity.py, run by live-tools.yml mode=cache-parity).
    python3 ops/live_tools/stress_map_cached.py --all --procs N      (cache folder: $SM_CACHE_DIR, default ~/.cache/bhr_sm_county)"""
import os, sys, glob, gzip, json, time, pickle, hashlib, importlib.util

C = '/Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12'
CACHE = os.environ.get('SM_CACHE_DIR') or os.path.expanduser('~/.cache/bhr_sm_county')
REC = {}


def _sha_files(paths):
    h = hashlib.sha256()
    for p in paths:
        h.update(p.encode()); h.update(b'\0')
        if os.path.exists(p):
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
        h.update(b'\1')
    return h.hexdigest()


def main():
    sys.argv = [os.path.join(C, 'code', 'stress_map_v2_1052.py')] + sys.argv[1:]
    sys.path.insert(0, os.path.join(C, 'code'))
    spec = importlib.util.spec_from_file_location('stress_map_v2_1052', sys.argv[0])
    sm = importlib.util.module_from_spec(spec); sys.modules['stress_map_v2_1052'] = sm; spec.loader.exec_module(sm)
    import pandas as pd
    real = sm.step_counties

    def key_of(CSH, L):
        code = [sys.argv[0], sm.V1PY, sm.V3PY] + sorted(glob.glob(os.path.join(sm.DI, '10_chronology_site', 'code', '*.py')))
        h = hashlib.sha256()
        h.update(_sha_files(code).encode())
        h.update(json.dumps(CSH, sort_keys=True, default=str).encode())
        if L is None:
            L, _, _ = sm.load_county_inputs()
        h.update(pd.util.hash_pandas_object(L, index=True).values.tobytes()); h.update(json.dumps(list(L.columns)).encode())
        qf = []; y = 1990
        while os.path.exists(sm.INPUTS['county_qcew'].replace('<YEAR>', str(y))): qf.append(sm.INPUTS['county_qcew'].replace('<YEAR>', str(y))); y += 1
        h.update(_sha_files(qf).encode())
        h.update(json.dumps([sm.V3, sm.V31, sm.TAG, str(sm.CSTART), sm.INPUTS.get('county_laus_held')], default=str).encode())
        return h.hexdigest()

    def cached(CSH, procs, L_override=None):
        t0 = time.time(); k = key_of(CSH, L_override); f = os.path.join(CACHE, 'county_%s.pkl.gz' % k)
        REC.update(key=k, cache_dir=CACHE)
        if os.path.exists(f) and os.environ.get('SM_CACHE', '1') != '0':
            with gzip.open(f, 'rb') as fh: CM, PER, info, amend5 = pickle.load(fh)
            sm.AMEND5.clear(); sm.AMEND5.update(amend5)
            CM.to_csv(os.path.join(sm.OUT, 'stress_map_' + sm.TAG + '_county_month.csv.gz'), index=False, compression='gzip')
            PER.to_csv(os.path.join(sm.OUT, 'stress_map_' + sm.TAG + '_county_periods.csv'), index=False)
            sm.log('county layer: the inputs and the code are those of a stored computation (key %s): taken from it in %.0f s' % (k[:12], time.time() - t0))
            REC.update(hit=True, seconds=round(time.time() - t0, 1)); return CM, PER, info
        CM, PER, info = real(CSH, procs, L_override)
        os.makedirs(CACHE, exist_ok=True); tmp = f + '.tmp'
        with gzip.open(tmp, 'wb', compresslevel=3) as fh: pickle.dump((CM, PER, info, dict(sm.AMEND5)), fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, f)
        for old in sorted(glob.glob(os.path.join(CACHE, 'county_*.pkl.gz')), key=os.path.getmtime)[:-2]: os.remove(old)   # the last two only
        sm.log('county layer: computed (key %s), stored for the next run' % k[:12])
        REC.update(hit=False, seconds=round(time.time() - t0, 1)); return CM, PER, info

    sm.step_counties = cached
    os.chdir(C)
    try:
        sm.main()
    finally:
        out = os.environ.get('LT_OUT')
        if out:
            os.makedirs(out, exist_ok=True); json.dump(REC, open(os.path.join(out, 'sm_county_cache.json'), 'w'))


if __name__ == '__main__':
    main()
