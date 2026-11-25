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
    # 1167b (25 Nov 2026; Anthony: "under 3 minutes of data releases"): THE COUNTY WORK BESIDE THE STATE LAYER. main() runs the State layer
    # (its own process, about 20 s) and only then the county outlines, the county unemployment file, the county layer (from the store,
    # about 22 s) and the industry series; none of the four reads the State layer or is read by it. Here they start in a thread when the
    # State layer starts, and main() gets their results (the same objects) when it asks for them; a failure is raised where main() would
    # have met it. LT_SM_PARALLEL=0 runs them in main()'s order.
    if os.environ.get('LT_SM_PARALLEL', '1') != '0' and '--procs' in sys.argv[1:]:
        import threading
        PRE = {}
        r_v1, r_shapes, r_laus, r_cnt, r_ind = sm.step_v1, sm.step_county_shapes, sm.step_fetch_laus, sm.step_counties, sm.step_industry
        procs = int(sys.argv[sys.argv.index('--procs') + 1])

        def county_work():
            try:
                PRE['CSH'] = r_shapes(); PRE['L'] = r_laus(); PRE['C'] = r_cnt(PRE['CSH'], procs, PRE['L']); PRE['I'] = r_ind()
            except BaseException as e:
                PRE['err'] = e

        def step_v1(rerun=True):
            if rerun and 'th' not in PRE:
                PRE['th'] = threading.Thread(target=county_work, name='county-work', daemon=True); PRE['th'].start()
            return r_v1(rerun)

        def take(k):
            PRE['th'].join()
            if k not in PRE: raise PRE.get('err') or RuntimeError('county work: %s missing' % k)
            return PRE[k]

        def step_counties(CSH, procs_, L_override=None):
            if 'th' in PRE:
                c_ = take('C')
                if CSH is PRE['CSH'] and L_override is PRE['L'] and procs_ == procs: return c_
            return r_cnt(CSH, procs_, L_override)
        sm.step_v1 = step_v1
        sm.step_county_shapes = lambda: take('CSH') if 'th' in PRE else r_shapes()
        sm.step_fetch_laus = lambda: take('L') if 'th' in PRE else r_laus()
        sm.step_counties = step_counties
        sm.step_industry = lambda: take('I') if 'th' in PRE else r_ind()
    # 1167b: THE PAGE WRITTEN ONCE. main() writes the page, runs the browser checks on it, then calls step_page again with the same objects
    # (TESTS2, the one argument that changes, is not read by step_page); the second call writes the first call's bytes again (about 17 s).
    # Here it returns the first call's result when every other argument is the same object, the page on disk is the one the first call
    # wrote, the day (the page's 'built') and the template are unchanged, and step_page is the code read on 25 Nov 2026 (SHA-256).
    # LT_SM_PAGE_ONCE=0 writes it twice.
    import inspect
    if (os.environ.get('LT_SM_PAGE_ONCE', '1') != '0'
            and hashlib.sha256(inspect.getsource(sm.step_page).encode()).hexdigest() == '83b1529369cff6afd53bc1f0b198654322907e648e0d949568d329366eea3896'):
        r_page = sm.step_page; PG = {}

        def _fp():
            t = sm.INPUTS['v2_template']
            return (_sha_files([os.path.join(sm.WEB, 'index.html')]), os.path.getmtime(t), os.path.getsize(t), pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'))

        def step_page(J1, CSH, CM, PER, N, S, B, info, TESTS2, DESC2, gapm):
            key = tuple(map(id, (J1, CSH, CM, PER, N, S, B, info, DESC2, gapm)))
            if PG.get('key') == key and PG.get('fp') == _fp():
                sm.log('wrote', os.path.join(sm.WEB, 'index.html'), PG['ret'][0], 'bytes'); REC.update(page_once=True); return PG['ret']
            ret = r_page(J1, CSH, CM, PER, N, S, B, info, TESTS2, DESC2, gapm)
            PG.update(key=key, ret=ret, fp=_fp()); return ret
        sm.step_page = step_page
    os.chdir(C)
    try:
        sm.main()
    finally:
        out = os.environ.get('LT_OUT')
        if out:
            os.makedirs(out, exist_ok=True); json.dump(REC, open(os.path.join(out, 'sm_county_cache.json'), 'w'))


if __name__ == '__main__':
    main()
