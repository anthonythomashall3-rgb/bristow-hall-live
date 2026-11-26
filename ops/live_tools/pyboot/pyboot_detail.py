# -*- coding: utf-8 -*-
"""THE STRESS MAP'S DETAIL FILES, FASTER (1167f, 26 Nov 2026; Anthony: "under 3 minutes of data releases"). No AI.

code/stress_map_detail_1150.py took 25 s of every live-tools run on GitHub. Two parts of it are made faster here, with the same bytes out:

  ints(a, mul)   the factor files' rounding, [None if not finite else int(round(v * mul))], on the whole array at once: the same product,
                 the same round half to even (numpy's rint, as Python's round), the same ints and Nones.
  industry(...)  the county jobs by industry. They come only from the QCEW county files (1032 data/qcew_industry_county), which change
                 only on a QCEW day, yet every run read all of them again (about 10 of the 25 s). The first run on a set of files does
                 exactly what the script did and keeps what it wrote: the bytes of each county's file and its total line. A later run on
                 the same files (SHA-256 of each), the same month range and county list and this code, writes those same bytes again
                 (only where the file on disk differs, as the script's put() does) and checks the totals against this run's county-month
                 table, as the script does. The store is a file in $SM_CACHE_DIR (kept between runs with the stress map's county layer);
                 SM_CACHE=0 never reads it.

ops/live_tools/pyboot/run_rewritten.py puts these in place of the script's own lines (same line count), only in the file whose SHA-256 it
knows; any other version of the script runs as itself."""
import csv, glob, gzip, hashlib, json, os, pickle
import numpy as np

VERSION = '1167f-1'
STATS = {}


def ints(a, mul):
    a = np.asarray(a, dtype=np.float64)
    ok = np.isfinite(a)
    r = np.rint(np.where(ok, a * mul, 0.0)).astype(np.int64).tolist()
    for i in np.flatnonzero(~ok).tolist():
        r[i] = None
    return r


def _key(files, V, c0, cn, mapc, CODES, NAMES):
    h = hashlib.sha256(VERSION.encode())
    for p in files:
        with open(p, 'rb') as f:
            h.update(os.path.basename(p).encode() + b'\0' + hashlib.sha256(f.read()).digest())
    h.update(json.dumps([V['cstart'], c0, cn, sorted(mapc), CODES, NAMES], sort_keys=True).encode())
    return h.hexdigest()


def _store_dir():
    return os.environ.get('SM_CACHE_DIR') or os.path.expanduser('~/.cache/bhr_sm_county')


def _write(path, b):          # the script's put(): write only when the bytes on disk differ
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, 'rb').read() == b: return 0
    open(path + '.tmp1150', 'wb').write(b); os.replace(path + '.tmp1150', path); return 1


def _check(order, tot10, tot_e, n_i, cn, c0):
    cmp_n = 0; cmp_bad = 0; bad_ex = []
    m = min(n_i, cn)
    for f in order:
        t = tot10.get(f); e = tot_e.get(f)
        if t is None or e is None: continue
        T = t[:m]; E = np.asarray(e, dtype=np.float64)[:m]
        ok = ~np.isnan(T) & np.isfinite(E)
        bad = ok & (np.rint(np.where(ok, E, 0.0)) != np.where(ok, T, 0.0))
        cmp_n += int(ok.sum()); nb = int(bad.sum()); cmp_bad += nb
        if nb and len(bad_ex) < 10:
            for i in np.flatnonzero(bad).tolist():
                if len(bad_ex) >= 10: break
                bad_ex.append([f, '%d-%02d' % ((c0 + i) // 12, (c0 + i) % 12 + 1), int(T[i]), float(E[i])])
    return cmp_n, cmp_bad, bad_ex


def industry(QD, c0, cn, V, mapc, tot_e, R, CODES, NAMES, put, WEB):
    files = sorted(glob.glob(os.path.join(QD, '*.csv.gz')))
    key = _key(files, V, c0, cn, mapc, CODES, NAMES)
    store = os.path.join(_store_dir(), 'detail_%s.pkl.gz' % key)
    if os.environ.get('SM_CACHE', '1') != '0' and os.path.exists(store):
        try:
            with gzip.open(store, 'rb') as f: K = pickle.load(f)
            if K.get('key') == key and K.get('version') == VERSION:
                n_i = K['n_i']; R['industry_months'] = n_i; R['industry_last'] = K['industry_last']
                wrote = sum(_write(os.path.join(WEB, 'ci', f + '.js'), b) for f, b in K['ci'])
                cmp_n, cmp_bad, bad_ex = _check([f for f, _ in K['ci']], K['tot10'], tot_e, n_i, cn, c0)
                STATS.update(path='store', key=key[:16])
                print('pyboot detail: county jobs by industry from the store (%s; QCEW files unchanged)' % key[:16], flush=True)
                return files, set(K['A_keys']), n_i, wrote, K['have'], K['cells'], K['held_cells'], cmp_n, cmp_bad, bad_ex
        except Exception as e:
            print('pyboot detail: the store could not be read (%s): computed' % type(e).__name__, flush=True)
    # ---- computed: the script's own lines (stress_map_detail_1150.py, 19 Nov 2026), and what they wrote kept
    A = {}; last = -1
    for pth in files:
        with gzip.open(pth, 'rt', newline='') as f:
            rd = csv.reader(f); next(rd)
            for fips, own, ind, y, q, m1, m2, m3, disc in rd:
                if ind == '10': key_ = '10' if own == '0' else ('gov' if own in '123' else None)
                else: key_ = ind if own == '5' else None
                if key_ is None: continue
                b = int(y) * 12 + (int(q) - 1) * 3 - c0
                if b < 0 or b + 2 >= cn + 12: continue
                d = A.setdefault(fips, {}).setdefault(key_, {})
                for k, v in enumerate((m1, m2, m3)):
                    if key_ == 'gov':   # federal + State + local; withheld in any one of them = withheld
                        o = d.get(b + k, 0); d[b + k] = None if (o is None or disc == 'N') else o + int(v)
                    else: d[b + k] = None if disc == 'N' else int(v)
                if key_ == '10': last = max(last, b + 2)
    n_i = min(cn, last + 1); R['industry_months'] = n_i; R['industry_last'] = '%d-%02d' % ((c0 + n_i - 1) // 12, (c0 + n_i - 1) % 12 + 1) if n_i > 0 else None
    wrote = 0; have = 0; cells = 0; held_cells = 0; cmp_n = 0; cmp_bad = 0; bad_ex = []
    keep_ci = []; tot10 = {}
    for f in sorted(mapc):
        d = A.get(f)
        if not d: continue
        have += 1; v = {}
        for c in CODES:
            s = d.get(c)
            if not s: v[c] = None; continue
            arr = [s.get(i) for i in range(n_i)]; v[c] = arr if any(x is not None for x in arr) else None
            cells += n_i; held_cells += sum(x is not None for x in arr)
        t = v.get('10'); e = tot_e.get(f)
        if t is not None and e is not None:
            for i in range(min(n_i, cn)):
                if t[i] is not None and np.isfinite(e[i]):
                    cmp_n += 1
                    if int(round(e[i])) != t[i]:
                        cmp_bad += 1
                        if len(bad_ex) < 10: bad_ex.append([f, '%d-%02d' % ((c0 + i) // 12, (c0 + i) % 12 + 1), t[i], float(e[i])])
        path = os.path.join(WEB, 'ci', f + '.js')
        wrote += put(path, 'ci', f, dict(start=V['cstart'], n=n_i, last=R['industry_last'], codes=CODES, names=NAMES, v=v))
        keep_ci.append((f, open(path, 'rb').read()))
        tot10[f] = None if t is None else np.array([np.nan if x is None else float(x) for x in t], dtype=np.float64)
    STATS.update(path='computed', key=key[:16])
    try:
        os.makedirs(_store_dir(), exist_ok=True)
        tmp = store + '.tmp'
        with gzip.open(tmp, 'wb', compresslevel=1) as f:
            pickle.dump(dict(version=VERSION, key=key, n_i=n_i, industry_last=R['industry_last'], A_keys=sorted(A), have=have, cells=cells,
                             held_cells=held_cells, ci=keep_ci, tot10=tot10), f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, store)
        for old in glob.glob(os.path.join(_store_dir(), 'detail_*.pkl.gz')):
            if old != store: os.remove(old)
        print('pyboot detail: county jobs by industry computed and kept (%s)' % key[:16], flush=True)
    except Exception as e:
        print('pyboot detail: not kept (%s)' % type(e).__name__, flush=True)
    return files, A, n_i, wrote, have, cells, held_cells, cmp_n, cmp_bad, bad_ex
