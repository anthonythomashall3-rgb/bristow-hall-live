# -*- coding: utf-8 -*-
"""RUN A LIVE-TOOLS SCRIPT WITH ITS parts() ON THE ARRAYS (1167b, 25 Nov 2026), AND THE STRESS MAP'S DETAIL FILES FASTER (1167f). No AI.

    python3 run_rewritten.py <script> [args...]

sitecustomize.py starts this in place of `python3 <script>` when <script> is one of the files below (its SHA-256 exactly; any other version
runs as itself). The script's text is read, its parts() body is replaced by a call to pyboot_fast.parts (same arithmetic, same results;
the replacement keeps the line count, so every later line keeps its number), and the script runs as Python would run it: __main__, its own
__file__, sys.argv and sys.path[0], its exceptions and exit code."""
import os, sys, hashlib

_A198 = ('''def parts(UR, base, Gq, p, m):
    ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
    return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)
''', '''def parts(UR, base, Gq, p, m):
    return __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167b pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
    pass
''')
_NESTED = ('''    def parts(UR, base, Gq, p, m):
        ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
        return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)
''', '''    def parts(UR, base, Gq, p, m):
        return __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167b pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
        pass
''')
# 1167m/n (27 Nov 2026): the same parts() since c2f1d5e3 (#147, 26 Nov: the State grade's production dimension q). The labour score, the output
# dimension and the highest excess come from pyboot_fast.parts as before, q from pyboot_fast.production_q (the script's q line on the arrays).
# The functions are pure (no shared state), so computing q after the output dimension, not before, changes nothing.
_A198_Q = ('''def parts(UR, base, Gq, p, m, Pm=None):
    ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
    q = dd.production_dimension(Pm, p, m) if Pm is not None and len(Pm[(Pm.index >= p - pd.DateOffset(months=12)) & (Pm.index <= m)]) >= 2 else None
    return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0), q
''', '''def parts(UR, base, Gq, p, m, Pm=None):
    L, o, mx = __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167m pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
    q = __import__('pyboot_fast').production_q(Pm, p, m, dd)   # 1167n pyboot: the production dimension on the arrays (the same dict)
    return L, o, mx, q
''')
_NESTED_Q = ('''    def parts(UR, base, Gq, p, m):
        ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
        q = dd.production_dimension(Pm, p, m) if Pm is not None and len(Pm[(Pm.index >= p - pd.DateOffset(months=12)) & (Pm.index <= m)]) >= 2 else None
        return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0), q
''', '''    def parts(UR, base, Gq, p, m):
        L, o, mx = __import__('pyboot_fast').parts(UR, base, Gq, p, m, dd)   # 1167m pyboot: the same arithmetic on the arrays (ops/live_tools/pyboot)
        q = __import__('pyboot_fast').production_q(Pm, p, m, dd)   # 1167n pyboot: the production dimension on the arrays (the same dict)
        return L, o, mx, q
''')
_DET_INTS = ("def ints(a, mul): return [None if not np.isfinite(v) else int(round(v * mul)) for v in a]\n",
             "def ints(a, mul): return __import__('pyboot_detail').ints(a, mul)   # 1167f pyboot: the same rounding on the whole array\n")
_DET_IND = ("    files = sorted(glob.glob(os.path.join(QD, '*.csv.gz'))); A = {}; last = -1\n    for pth in files:\n        with gzip.open(pth, 'rt', newline='') as f:\n            rd = csv.reader(f); next(rd)\n            for fips, own, ind, y, q, m1, m2, m3, disc in rd:\n                if ind == '10': key = '10' if own == '0' else ('gov' if own in '123' else None)\n                else: key = ind if own == '5' else None\n                if key is None: continue\n                b = int(y) * 12 + (int(q) - 1) * 3 - c0\n                if b < 0 or b + 2 >= cn + 12: continue\n                d = A.setdefault(fips, {}).setdefault(key, {})\n                for k, v in enumerate((m1, m2, m3)):\n                    if key == 'gov':   # federal + State + local; withheld in any one of them = withheld\n                        o = d.get(b + k, 0); d[b + k] = None if (o is None or disc == 'N') else o + int(v)\n                    else: d[b + k] = None if disc == 'N' else int(v)\n                if key == '10': last = max(last, b + 2)\n    n_i = min(cn, last + 1); R['industry_months'] = n_i; R['industry_last'] = '%d-%02d' % ((c0 + n_i - 1) // 12, (c0 + n_i - 1) % 12 + 1) if n_i > 0 else None\n    wrote = 0; have = 0; cells = 0; held_cells = 0; cmp_n = 0; cmp_bad = 0; bad_ex = []\n    for f in sorted(mapc):\n        d = A.get(f)\n        if not d: continue\n        have += 1; v = {}\n        for c in CODES:\n            s = d.get(c)\n            if not s: v[c] = None; continue\n            arr = [s.get(i) for i in range(n_i)]; v[c] = arr if any(x is not None for x in arr) else None\n            cells += n_i; held_cells += sum(x is not None for x in arr)\n        t = v.get('10'); e = tot_e.get(f)\n        if t is not None and e is not None:\n            for i in range(min(n_i, cn)):\n                if t[i] is not None and np.isfinite(e[i]):\n                    cmp_n += 1\n                    if int(round(e[i])) != t[i]:\n                        cmp_bad += 1\n                        if len(bad_ex) < 10: bad_ex.append([f, '%d-%02d' % ((c0 + i) // 12, (c0 + i) % 12 + 1), t[i], float(e[i])])\n        wrote += put(os.path.join(WEB, 'ci', f + '.js'), 'ci', f, dict(start=V['cstart'], n=n_i, last=R['industry_last'], codes=CODES, names=NAMES, v=v))\n",
            "    files, A, n_i, wrote, have, cells, held_cells, cmp_n, cmp_bad, bad_ex = __import__('pyboot_detail').industry(QD, c0, cn, V, mapc, tot_e, R, CODES, NAMES, put, WEB)\n    # 1167f pyboot: the county jobs by industry, from ops/live_tools/pyboot/pyboot_detail.py: the same bytes, kept between runs while\n    # the QCEW county files are unchanged. These comment lines keep the line count, so every later line keeps its number.\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n    #\n")
# SHA-256 of the file as read on 25 Nov 2026 -> its replacements (each text must occur exactly once)
REWRITES = {
    '8295417d6b2e22c57c22b8a4b6e174b867b62ccf30ef2f84cd4483aca0e57f7f': [_A198],     # 1032 code/state_chronology_v4_growth_cycle_a198_1032.py
    'ae887a2170936346922b973195ce109267c19e82b9a0daa157ed203365f7bf37': [_NESTED],   # 1052 code/stress_map_v3_1_1052.py (the stress map's State layer)
    '5f824cd0c9f8ddecae6e3041c0c44ad1c259d561cb0211ce12d79fde08f3778c': [_DET_INTS, _DET_IND],   # 1052 code/stress_map_detail_1150.py (1167f, 26 Nov 2026)
    '4b7c469872b36e52ca22d19a8b3a94b0dfcca6d1550852596dcfe4b06ace48ad': [_A198_Q],   # 1032 a198 since c2f1d5e3 (#147, 26 Nov 2026; 1167m)
    '2e92b5129b7e18fe2375382c7aa57ac3216332bce1f0ac9f01363f1a5bb90bb1': [_NESTED_Q],   # 1052 stress_map_v3_1_1052.py since c2f1d5e3 (1167m)
    '46a8d0d3efd2efe215c3994210e251249783e06ae129e7a5630b9b0817b485f1': [_A198_Q],   # 1032 a198 with the repairs of 1201 (27 Nov 2026); parts() unchanged
    '24ce63e574c7b049fd8a825fe2e29d2efcf562262af2a89ef70495512edf9249': [_NESTED_Q],   # 1052 stress_map_v3_1_1052.py with the repairs of 1201
    '3c5e94de2932ffbec08fd316f1baca18665277a35bb2523eeeb62095ccdfe485': [_A198_Q],   # 1032 a198 with the payroll rule of 1207 (27 Nov 2026); parts() unchanged
    'c2697c82ba9aa1bbff9feb0e1c643c956fae62252223f4e2ec391de353e54b7f': [_NESTED_Q],   # 1052 stress_map_v3_1_1052.py with the payroll rule of 1207
}


def sha_of(path):
    with open(path, 'rb') as f: return hashlib.sha256(f.read()).hexdigest()


def main():
    target = sys.argv[1]
    path = os.path.abspath(target)
    raw = open(path, 'rb').read()
    src = raw.decode('utf-8')
    for old, new in REWRITES.get(hashlib.sha256(raw).hexdigest(), ()):
        if src.count(old) != 1 or old.count('\n') != new.count('\n'):
            raise SystemExit('pyboot run_rewritten: %s does not carry the text it rewrites' % target)
        src = src.replace(old, new)
    code = compile(src, path, 'exec')
    sys.argv = sys.argv[1:]
    sys.path[0] = os.path.dirname(path)
    import __main__, builtins, importlib.machinery
    g = __main__.__dict__
    g.clear()
    g.update(__name__='__main__', __doc__=None, __package__=None, __spec__=None, __file__=path, __cached__=None, __builtins__=builtins,
             __loader__=importlib.machinery.SourceFileLoader('__main__', path))
    exec(code, g)


if __name__ == '__main__':
    main()
