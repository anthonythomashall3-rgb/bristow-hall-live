#!/usr/bin/env python3
"""Map extracted Economic Indicators table cells (out/ei_cells/ei_<issue>.csv) to named fields.

For each cell the three OCR readings (text layer, tesseract 300dpi de-ruled, tesseract 400dpi)
are normalised for the column type and majority-voted (consensus.py). Column roles are
found from accounting identities, and the basis (NSA/SA) from the printed headers.

Output: out/ei_fields_long.csv with one row per (issue, table, ref month, occurrence, field):
  value, basis (NSA|SA), n_agree/n_valid readings, alternates, check (identity result), flags.

Fields (thousands unless noted):
  LF : TLF, AF, CLF, EMP, AGR, NAG, UNEMP, UR (percent)   [+ *_SA and UR_SA]
       1961 issues print levels in millions -> unit column says 'millions'.
  EMP: PAY (total nonagricultural payroll employment), MFG, DUR, NDUR  (+ derived sums flagged)
  HRS: HRS_MFG, HRS_DUR, HRS_NDUR (hours per week)
"""
import csv, glob, os, re, sys, itertools
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consensus import norm_reading, vote, READERS

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELLDIR = os.path.join(W, 'out', 'ei_cells')
PAGEDIR = os.path.join(W, 'raw', 'ei_pages')
RANGES = {'LF': (0.5, 99.9), 'EMP': (0.5, 99.9), 'HRS': (20.0, 55.0)}

def col_types(cells):
    votes = defaultdict(Counter)
    for c in cells:
        for r in READERS:
            raw = c.get(r + '_raw', '')
            if not raw:
                continue
            s = re.sub(r'\s', '', raw)
            if re.search(r'\d[,.*]\d{3}(\D|$)', s) or re.fullmatch(r'\d{4,5}', s):
                votes[int(c['col'])]['thou'] += 1
            elif re.search(r'\d[.,]\d(\D|$)', s):
                votes[int(c['col'])]['dec'] += 1
            elif re.fullmatch(r'\d{3}', s):
                votes[int(c['col'])]['thou3'] += 1
    return {col: ('dec' if v['dec'] > v['thou'] + v['thou3'] else 'thou') for col, v in votes.items()}

def build(cells, kind):
    types = col_types(cells)
    lo, hi = RANGES[kind]
    rows, order = {}, []
    for c in cells:
        key = (int(c['row']))
        if key not in rows:
            rows[key] = dict(row=key, ref=c['ref'], occ=int(c['occ']), basis=c['basis'] or '', label=c['label'] or '',
                             inferred=c['month_inferred'], cells={}, page=c['page'])
            order.append(key)
        col = int(c['col'])
        ct = types.get(col, 'thou')
        rd = []
        for r in READERS:
            v, fl = norm_reading(c.get(r + '_raw'), ct, lo if ct == 'dec' else None, hi if ct == 'dec' else None)
            rd.append((r, v, fl))
        best, nag, nval, alts = vote(rd)
        rows[key]['cells'][col] = dict(best=best, nag=nag, nval=nval, alts=alts, rd=rd, ctype=ct)
    # drop readings far below the column's typical magnitude (lost leading digit, e.g. '1,582' -> '582')
    colmed = {}
    for col in types:
        vs = sorted(r['cells'][col]['best'] for r in rows.values() if col in r['cells'] and r['cells'][col]['best'] is not None)
        colmed[col] = vs[len(vs) // 2] if vs else None
    for r in rows.values():
        for col, cell in r['cells'].items():
            md = colmed.get(col)
            if cell['ctype'] != 'thou' or not md or md < 1500:
                continue
            low = [v for k, v, fl in cell['rd'] if v is not None and v < 1000]
            rd = [(k, (v if (v is None or v >= 1000) else None), (fl if (v is None or v >= 1000) else 'below_column_magnitude'))
                  for k, v, fl in cell['rd']]
            best, nag, nval, alts = vote(rd)
            # a thin leading '1' next to a rule line is often lost: offer v+1000 as a candidate
            # (never voted; used only if an accounting identity selects it)
            extra = sorted({v + 1000 for v in low} - set(alts) - {best})
            cell.update(best=best, nag=nag, nval=nval, alts=list(alts) + extra, rd=rd,
                        restored=set(extra))
    return [rows[k] for k in sorted(order)], types

def V(r, c):
    x = r['cells'].get(c)
    return None if x is None else x['best']

def C(r, c):
    x = r['cells'].get(c)
    if x is None:
        return []
    out = [x['best']] + list(x['alts'])
    return [v for v in out if v is not None]

def score(rows, f):
    n = 0
    for r in rows:
        try:
            if f(r):
                n += 1
        except TypeError:
            pass
    return n

def score_any(rows, cols_, fn, maxc=3):
    """Rows where some combination of candidate readings satisfies fn."""
    n = 0
    for r in rows:
        cand = [C(r, c)[:maxc] for c in cols_]
        if any(not c for c in cand):
            continue
        if any(fn(*combo) for combo in itertools.product(*cand)):
            n += 1
    return n

def med(rows, c):
    v = sorted(V(r, c) for r in rows if V(r, c) is not None)
    return v[len(v) // 2] if v else None

def page_text(issue, kind, page):
    fn = os.path.join(PAGEDIR, f'ei_{issue}_{kind}_p{int(page):02d}.txt')
    return open(fn).read() if os.path.exists(fn) else ''

# ------------------------------------------------------------------ LF
def map_lf(rows, types, issue):
    cols = sorted({c for r in rows for c in r['cells']})
    n = len(rows)
    m0 = med(rows, cols[0]) if cols else None
    mil = m0 is not None and m0 < 300
    tol = 0.15 if mil else 3
    if mil:
        L = [c for c in cols if (med(rows, c) or 0) > 1.5]
    else:
        L = [c for c in cols if types.get(c) == 'thou']
    def ok3(a, b, c):
        return score_any(rows, (a, b, c), lambda x, y, z: abs(x - y - z) <= tol)
    m = {}
    # 1. employment decomposition E = A + N with A, N the two columns right after E
    decs = []
    for i in range(len(L) - 2):
        e, a, b = L[i], L[i + 1], L[i + 2]
        s = ok3(e, a, b)
        if s >= 0.5 * n:
            decs.append((i, e, a, b, s))
    sets = []
    for (i, e, a, b, s) in decs:
        # CLF column c left of e with CLF - E = U for U right of b
        best = None
        for c in [x for x in L if x < e]:
            for u in [x for x in L if x > b]:
                s2 = ok3(c, e, u)
                if s2 >= 0.5 * n and (best is None or s2 > best[0]):
                    best = (s2, c, u)
        if best:
            sets.append(dict(CLF=best[1], EMP=e, A=a, B=b, UNEMP=best[2], score=best[0]))
            continue
        # 1948-50 layout: TLF, EMP, NAG, AGR, AF, UNEMP  (TLF = EMP + AF + U)
        for t in [x for x in L if x < e]:
            for af, u in itertools.permutations([x for x in L if x > b], 2):
                s2 = score_any(rows, (t, e, af, u), lambda w, x, y, z: abs(w - x - y - z) <= tol, maxc=2)
                if s2 >= 0.6 * n and (best is None or s2 > best[0]):
                    best = (s2, t, af, u)
        if best:
            sets.append(dict(TLF=best[1], EMP=e, A=a, B=b, AF=best[2], UNEMP=best[3], score=best[0]))
    if not sets and mil:
        # fall back: triples c<e<u with c-e=u and u small
        for c, e, u in itertools.combinations(L, 3):
            s2 = ok3(c, e, u)
            if s2 >= 0.6 * n and (med(rows, u) or 99) < 10:
                sets.append(dict(CLF=c, EMP=e, UNEMP=u, score=s2))
    sets.sort(key=lambda s: s['EMP'])
    # dedupe overlapping sets: keep leftmost as NSA, a second disjoint one to the right as SA (millions era)
    chosen = []
    for s in sets:
        if not chosen or s.get('CLF', s.get('TLF')) > chosen[-1]['UNEMP']:
            chosen.append(s)
    if not chosen:
        # NSA layout in 1961: TLF, CLF, EMP, NAG, UNEMP (no AGR) -> CLF - EMP = U with u right after nag
        for c, e, u in itertools.combinations(L, 3):
            s2 = ok3(c, e, u)
            if s2 >= 0.6 * n and u - e == 2:
                chosen.append(dict(CLF=c, EMP=e, NAGONLY=e + 1, UNEMP=u, score=s2))
                break
    if mil and len(chosen) == 1 and 'A' in chosen[0]:
        # NSA part without agriculture sits left of the SA part
        s0 = chosen[0]
        for c, e, u in itertools.combinations([x for x in L if x < s0.get('CLF', 99)], 3):
            if ok3(c, e, u) >= 0.6 * n and u - e == 2:
                chosen.insert(0, dict(CLF=c, EMP=e, NAGONLY=e + 1, UNEMP=u, score=0))
                break
    for k, s in enumerate(chosen[:2]):
        suf = '' if k == 0 else '_SA'
        for f in ('TLF', 'AF', 'CLF', 'EMP', 'UNEMP'):
            if f in s:
                m[f + suf] = s[f]
        if 'A' in s:
            ma, mb = med(rows, s['A']), med(rows, s['B'])
            if ma is not None and mb is not None and ma < mb:
                m['AGR' + suf], m['NAG' + suf] = s['A'], s['B']
            else:
                m['AGR' + suf], m['NAG' + suf] = s['B'], s['A']
        if 'NAGONLY' in s:
            m['NAG' + suf] = s['NAGONLY']
        if suf == '' and 'CLF' in s:
            left = [x for x in cols if x < s['CLF']]
            if left and 'TLF' not in m and (med(rows, left[-1]) or 0) > (med(rows, s['CLF']) or 0):
                m['TLF'] = left[-1]
    # unemployment rates
    if 'UNEMP' in m:
        u = m['UNEMP']
        after = max(v for k, v in m.items())
        ratecols = [c for c in cols if c > after and types.get(c) == 'dec'] if not mil else [c for c in cols if c > after]
        def clf(r):
            if 'CLF' in m:
                return V(r, m['CLF'])
            return V(r, m['TLF']) - V(r, m['AF'])
        bestr = None
        for rc in ratecols:
            s = score(rows, lambda r: any(abs(x - 100.0 * y / clf(r)) <= 0.16 for x in C(r, rc) for y in C(r, u)))
            if bestr is None or s > bestr[0]:
                bestr = (s, rc)
        if bestr and bestr[0] >= 0.4 * n:
            m['UR'] = bestr[1]
            nxt = [c for c in cols if c > bestr[1]]
            if nxt and issue >= '1957-07' and types.get(nxt[0]) == 'dec':
                m['UR_SA'] = nxt[0]
    return m, ('millions' if mil else 'thousands'), tol

# ------------------------------------------------------------------ EMP
def emp_era(issue, text):
    t = re.sub(r'\s+', ' ', text).lower()
    if 'alaska' in t:
        return 'F'
    if 'unad' in t and ('adjusted for seasonal' in t or 'seasonally adjusted' in t or 'seasonal variation' in t):
        return 'E'
    if 'unad' in t:
        return 'E'
    if 'seasonal variation' in t or 'adjusted for seasonal' in t or 'adjusted for sea' in t:
        return 'D'
    return 'ABC'

EMP_TEMPLATES = {
    # era: (field -> position among thousands-columns), expected column count (for derived sums)
    'A': ({'PAY': 0, 'MFG': 1}, 5),
    'B': ({'DUR': 0, 'NDUR': 1}, 8),
    'C': ({'MFG': 0, 'DUR': 1, 'NDUR': 2}, 9),
    'D': ({'PAY_SA': 0, 'PAY': 1, 'MFG': 2, 'DUR': 3, 'NDUR': 4}, 10),
    'E': ({'PAY': 0, 'PAY_SA': 1, 'MFG': 2, 'DUR': 3, 'NDUR': 4}, 10),
    'F': ({'PAY': 0, 'PAY_SA': 1, 'PAY_SA_XAKHI': 2, 'MFG': 3, 'DUR': 4, 'NDUR': 5}, 10),
}

def map_emp(rows, types, issue, text):
    cols = sorted({c for r in rows for c in r['cells']})
    L = [c for c in cols if types.get(c) == 'thou']
    n = len(rows)
    era = emp_era(issue, text)
    if era == 'ABC':
        era = 'A' if issue <= '1948-11' else ('B' if issue <= '1949-09' else 'C')
    tmpl, ncol = EMP_TEMPLATES[era]
    info = {'era': era, 'ncols': len(L), 'expected_cols': ncol, 'sa_mfg': era in ('E', 'F')}
    # anchor on the manufacturing identity where the era has a manufacturing total
    best = None
    for i in range(len(L) - 2):
        a, b, c = L[i], L[i + 1], L[i + 2]
        s = score_any(rows, (a, b, c), lambda x, y, z: abs(x - y - z) <= 3)
        if s >= 0.5 * n and (best is None or s > best[0]):
            best = (s, i)
    m = {}
    if 'MFG' in tmpl and 'DUR' in tmpl:
        if best is not None:
            shift = best[1] - tmpl['MFG']
            info['anchor'] = 'identity'
        else:
            shift = 0
            info['anchor'] = 'template'
        for f, pos in tmpl.items():
            if f.startswith('PAY'):
                continue
            if 0 <= pos + shift < len(L):
                m[f] = L[pos + shift]
        # total columns left of manufacturing, by era and by how many are printed
        mi = tmpl['MFG'] + shift
        left = L[:mi] if 0 <= mi <= len(L) else []
        LEFT = {'D': {2: ['PAY_SA', 'PAY'], 1: ['PAY']},
                'E': {2: ['PAY', 'PAY_SA'], 1: ['PAY_SA']},
                'F': {3: ['PAY', 'PAY_SA', 'PAY_SA_XAKHI'], 2: ['PAY', 'PAY_SA'], 1: ['PAY_SA']}}
        if era in LEFT and len(left) in LEFT[era]:
            for f, c in zip(LEFT[era][len(left)], left):
                m[f] = c
        info['left_cols'] = len(left)
        if era == 'C' and len(L) == ncol and shift == 0:
            info['derive_pay'] = [L[0]] + L[3:]
        if era == 'C' and shift >= 1:
            m['PAY'] = L[best[1] - 1]   # 1953-54 issues print a nonfarm 'Total' left of manufacturing
        if era == 'A':
            m['PAY'] = L[0]
    else:
        for f, pos in tmpl.items():
            if pos < len(L):
                m[f] = L[pos]
        info['anchor'] = 'template'
        if era == 'B':
            info['derive_mfg'] = [L[0], L[1]]
            if len(L) == ncol:
                info['derive_pay'] = L[:]
    return m, info

# ------------------------------------------------------------------ HRS
def map_hrs(rows, types, issue, text):
    cols = sorted({c for r in rows for c in r['cells']})
    m = {}
    if not cols:
        return m, {}
    m['HRS_MFG'] = cols[0]
    if len(cols) >= 3:
        a, b, c = cols[0], cols[1], cols[2]
        s = score(rows, lambda r: min(V(r, b), V(r, c)) - 0.05 <= V(r, a) <= max(V(r, b), V(r, c)) + 0.05)
        if s >= 0.5 * len(rows):
            m.update(HRS_DUR=b, HRS_NDUR=c)
    t = re.sub(r'\s+', ' ', text).lower()
    sa = 'seasonally adjusted' in t and issue >= '1960-11'
    return m, {'sa': sa}

GLYPH = {'3': '85', '8': '3605', '5': '63', '6': '58', '1': '7', '7': '1', '0': '86', '9': '8'}

def glyph_variants(v):
    t = str(int(v)) if float(v).is_integer() else f'{v:.1f}'
    out = set()
    for i, ch in enumerate(t):
        for rep in GLYPH.get(ch, ''):
            try:
                out.add(float(t[:i] + rep + t[i + 1:]))
            except ValueError:
                pass
    return out

# ------------------------------------------------------------------ per-row resolution
def resolve(row, eqs):
    """eqs: list of (fields_cols, fn) identities over candidate values; try alternates to satisfy.
    Returns dict col->(value, flag)."""
    out = {c: (V(row, c), '') for c in row['cells']}
    for cols_, fn in eqs:
        if any(V(row, c) is None for c in cols_):
            # try fill from alternates
            pass
        try:
            if fn(*[out[c][0] for c in cols_]):
                continue
        except (TypeError, KeyError):
            pass
        # search alternates (at most 2 cells changed)
        cand = [(C(row, c) or [None])[:4] for c in cols_]
        sols = []
        for combo in itertools.product(*cand):
            try:
                if fn(*combo):
                    nchg = sum(1 for c, v in zip(cols_, combo) if v != V(row, c))
                    sols.append((nchg, combo))
            except TypeError:
                continue
        if sols:
            sols.sort(key=lambda x: x[0])
            if len(sols) == 1 or sols[0][0] < sols[1][0] or sols[0][1] == sols[1][1]:
                for c, v in zip(cols_, sols[0][1]):
                    if v != out[c][0]:
                        out[c] = (v, 'identity_resolved')
    return out

def process_issue(fn, writer):
    issue = os.path.basename(fn)[3:10]
    with open(fn) as f:
        cells = list(csv.DictReader(f))
    for kind in ('LF', 'EMP', 'HRS'):
        cs = [c for c in cells if c['kind'] == kind]
        if not cs:
            continue
        # if two pages carry the table, keep the one with more rows
        pages = Counter(c['page'] for c in cs)
        pg = max(pages, key=lambda p: len({c['row'] for c in cs if c['page'] == p}))
        cs = [c for c in cs if c['page'] == pg]
        rows, types = build(cs, kind)
        text = page_text(issue, kind, pg)
        unit = 'thousands'
        info = {}
        if kind == 'LF':
            m, unit, tol = map_lf(rows, types, issue)
        elif kind == 'EMP':
            m, info = map_emp(rows, types, issue, text)
            tol = 3
        else:
            m, info = map_hrs(rows, types, issue, text)
            unit = 'hours'
            tol = 0.05
        # seasonally adjusted rate column is set in italics: italic '3' is read as '8'.
        # Rule: a reading >= 8.0 whose NSA rate (same row) is < 6.5 becomes 3.x; readings
        # more than 2.5 points from the NSA rate are discarded.
        if kind == 'LF' and 'UR_SA' in m and 'UR' in m:
            for r in rows:
                cell = r['cells'].get(m['UR_SA'])
                nsa = V(r, m['UR'])
                if cell is None or nsa is None:
                    continue
                rd = []
                for k, v, fl in cell['rd']:
                    if v is not None and v >= 8.0 and nsa < 6.5:
                        v, fl = round(v - 5.0, 1), 'italic_3_misread_as_8_corrected'
                    if v is not None and abs(v - nsa) > 2.5:
                        v, fl = None, 'implausible_vs_nsa'
                    rd.append((k, v, fl))
                best, nag, nval, alts = vote(rd)
                cell.update(best=best, nag=nag, nval=nval, alts=alts, rd=rd)
        # identities per row
        eqs = []
        if kind == 'LF':
            for suf in ('', '_SA'):
                # SA totals and components are adjusted separately (EI footnote): loose tolerance
                t_ = tol if suf == '' else 0.35
                if 'EMP' + suf in m and 'AGR' + suf in m:
                    eqs.append(((m['EMP' + suf], m['AGR' + suf], m['NAG' + suf]), lambda e, a, b, t_=t_: abs(e - a - b) <= t_))
                if 'CLF' + suf in m and 'EMP' + suf in m and 'UNEMP' + suf in m:
                    eqs.append(((m['CLF' + suf], m['EMP' + suf], m['UNEMP' + suf]), lambda c, e, u, t_=t_: abs(c - e - u) <= t_))
            if 'TLF' in m and 'AF' in m:
                eqs.append(((m['TLF'], m['EMP'], m['AF'], m['UNEMP']), lambda t, e, af, u: abs(t - e - af - u) <= tol))
        if kind == 'EMP' and 'MFG' in m and 'DUR' in m:
            eqs.append(((m['MFG'], m['DUR'], m['NDUR']), lambda a, b, c: abs(a - b - c) <= 3))
        for r in rows:
            res = resolve(r, eqs)
            # identity check results per field
            chk = {}
            for cols_, fn_ in eqs:
                try:
                    okk = fn_(*[res[c][0] for c in cols_])
                except (TypeError, KeyError):
                    okk = None
                for c in cols_:
                    prev = chk.get(c)
                    chk[c] = okk if prev is None else (prev and okk)
            # nonfarm total vs sum of printed industry divisions (MFG + columns right of NDUR):
            # NSA totals add exactly (+-5); SA totals are adjusted separately (+-1.5%).
            if kind == 'EMP' and 'MFG' in m and 'NDUR' in m:
                divs = [c for c in sorted(r['cells']) if c > m['NDUR']]
                try:
                    dsum = res[m['MFG']][0] + sum(res[c][0] for c in divs)
                except (TypeError, KeyError):
                    dsum = None
                era = info.get('era')
                n_div_ok = len(divs) == info.get('expected_cols', 0) - 3 - info.get('left_cols', 0)
                for f_, tolp in (('PAY', None), ('PAY_SA', 0.015)):
                    if f_ not in m or m[f_] not in r['cells'] or dsum is None or not n_div_ok:
                        continue
                    # which total matches the basis of the divisions? era D: NSA; E/F: SA
                    same_basis = (era == 'D' and f_ == 'PAY') or (era == 'E' and f_ == 'PAY_SA')
                    if not same_basis:
                        continue
                    tol_ = 5 if tolp is None else tolp * dsum
                    col = m[f_]
                    cur = res[col][0]
                    if cur is not None and abs(cur - dsum) <= tol_:
                        chk[col] = True
                        continue
                    cands = set(C(r, col))
                    for v0 in list(cands):
                        cands |= glyph_variants(v0)
                    good = sorted((c for c in cands if abs(c - dsum) <= tol_), key=lambda c: abs(c - dsum))
                    if good:
                        res[col] = (good[0], 'total_vs_divisions_resolved' + ('' if good[0] in C(r, col) else '(glyph_variant)'))
                        chk[col] = True
                    else:
                        chk[col] = False
            # SA vs NSA nonfarm totals in the same row differ by seasonality only (< 4%)
            if kind == 'EMP' and 'PAY' in m and 'PAY_SA' in m and m['PAY'] in r['cells'] and m['PAY_SA'] in r['cells']:
                a_, b_ = res[m['PAY']][0], res[m['PAY_SA']][0]
                if a_ and b_ and abs(a_ / b_ - 1) > 0.04:
                    # fix the one not confirmed by the division identity
                    for col, other in ((m['PAY'], b_), (m['PAY_SA'], a_)):
                        if chk.get(col):
                            continue
                        cands = set(C(r, col))   # own readings only; not treated as validated
                        good = sorted((c for c in cands if abs(c / other - 1) <= 0.03), key=lambda c: abs(c / other - 1))
                        if good:
                            res[col] = (good[0], 'sa_vs_nsa_total_reading_choice')
                            break
            # rate check
            if kind == 'LF' and 'UR' in m and 'UNEMP' in m:
                try:
                    u = res[m['UNEMP']][0]
                    cl = res[m['CLF']][0] if 'CLF' in m else res[m['TLF']][0] - res[m['AF']][0]
                    urv = res[m['UR']][0]
                    okr = abs(urv - 100.0 * u / cl) <= 0.16 if unit == 'thousands' else abs(urv - 100.0 * u / cl) <= 0.35
                    chk[m['UR']] = okr
                    if not okr:
                        for alt in C(r, m['UR']):
                            if abs(alt - 100.0 * u / cl) <= 0.16:
                                res[m['UR']] = (alt, 'identity_resolved')
                                chk[m['UR']] = True
                                break
                except (TypeError, KeyError, ZeroDivisionError):
                    pass
            if kind == 'HRS' and 'HRS_DUR' in m:
                try:
                    a, b, c = (res[m['HRS_MFG']][0], res[m['HRS_DUR']][0], res[m['HRS_NDUR']][0])
                    okh = min(b, c) - 0.05 <= a <= max(b, c) + 0.05
                    for col in (m['HRS_MFG'], m['HRS_DUR'], m['HRS_NDUR']):
                        chk[col] = okh
                except (TypeError, KeyError):
                    pass
            basis_lab = r['basis']
            for field, col in m.items():
                if field.startswith('_') or col not in r['cells']:
                    continue
                val, fl = res.get(col, (None, ''))
                cell = r['cells'][col]
                if val is not None and val in cell.get('restored', set()):
                    fl = (fl + ';' if fl else '') + 'leading_1_restored_by_identity'
                rflags = sorted({f'{k}:{f2}' for k, v2, f2 in cell['rd'] if f2 and v2 == val})
                if rflags:
                    fl = (fl + ';' if fl else '') + ','.join(rflags)
                basis = 'NSA'
                if field.endswith('_SA') or field in ('PAY_SA', 'PAY_SA_XAKHI'):
                    basis = 'SA'
                if kind == 'EMP' and info.get('sa_mfg') and field in ('MFG', 'DUR', 'NDUR'):
                    basis = 'SA'
                if kind == 'HRS' and info.get('sa'):
                    basis = 'SA'
                fname = field.replace('_SA', '') if field != 'PAY_SA_XAKHI' else 'PAY_XAKHI'
                writer.writerow(dict(issue=issue, table=kind, page=pg, ref=r['ref'], occ=r['occ'], row_basis_label=basis_lab,
                                     month_inferred=r['inferred'], field=fname, basis=basis, unit=unit if kind != 'LF' or not fname.startswith('UR') else 'percent',
                                     value=val, n_agree=cell['nag'], n_valid=cell['nval'],
                                     alts=';'.join(str(a) for a in cell['alts']),
                                     readings='|'.join(f"{rr}={'' if v is None else v}" for rr, v, _ in cell['rd']),
                                     identity={True: 'ok', False: 'FAIL', None: ''}.get(chk.get(col)),
                                     flags=fl, derived=''))
            # derived fields
            if kind == 'EMP' and info.get('derive_mfg'):
                a, b = info['derive_mfg']
                try:
                    v = res[a][0] + res[b][0]
                    writer.writerow(dict(issue=issue, table=kind, page=pg, ref=r['ref'], occ=r['occ'], row_basis_label=basis_lab,
                                         month_inferred=r['inferred'], field='MFG', basis='NSA', unit='thousands', value=v,
                                         n_agree='', n_valid='', alts='', readings='', identity='', flags='',
                                         derived='DUR+NDUR (no manufacturing total printed)'))
                except (TypeError, KeyError):
                    pass
            if kind == 'EMP' and info.get('derive_pay'):
                try:
                    v = sum(res[c][0] for c in info['derive_pay'])
                    writer.writerow(dict(issue=issue, table=kind, page=pg, ref=r['ref'], occ=r['occ'], row_basis_label=basis_lab,
                                         month_inferred=r['inferred'], field='PAY', basis='NSA', unit='thousands', value=v,
                                         n_agree='', n_valid='', alts='', readings='', identity='', flags='',
                                         derived='sum of printed industry divisions (no total printed)'))
                except (TypeError, KeyError):
                    pass
            if kind == 'LF' and 'UR' not in m and 'UNEMP' in m:
                try:
                    u = res[m['UNEMP']][0]
                    cl = res[m['CLF']][0] if 'CLF' in m else res[m['TLF']][0] - res[m['AF']][0]
                    writer.writerow(dict(issue=issue, table=kind, page=pg, ref=r['ref'], occ=r['occ'], row_basis_label=basis_lab,
                                         month_inferred=r['inferred'], field='UR', basis='NSA', unit='percent',
                                         value=round(100.0 * u / cl, 1), n_agree='', n_valid='', alts='', readings='',
                                         identity='', flags='', derived='100*UNEMP/CLF (rate not printed)'))
                    if 'CLF' not in m:
                        writer.writerow(dict(issue=issue, table=kind, page=pg, ref=r['ref'], occ=r['occ'], row_basis_label=basis_lab,
                                             month_inferred=r['inferred'], field='CLF', basis='NSA', unit='thousands',
                                             value=cl, n_agree='', n_valid='', alts='', readings='', identity='',
                                             flags='', derived='TLF-AF (civilian labor force not printed)'))
                except (TypeError, KeyError, ZeroDivisionError):
                    pass
        yield issue, kind, m, info, unit

FIELDS = ['issue', 'table', 'page', 'ref', 'occ', 'row_basis_label', 'month_inferred', 'field', 'basis', 'unit', 'value',
          'n_agree', 'n_valid', 'alts', 'readings', 'identity', 'flags', 'derived']

def main():
    fns = sorted(glob.glob(os.path.join(CELLDIR, 'ei_*.csv')))
    if len(sys.argv) > 1:
        fns = [f for f in fns if any(a in f for a in sys.argv[1:])]
    out = os.path.join(W, 'out', 'ei_fields_long.csv' if len(sys.argv) == 1 else 'ei_fields_test.csv')
    lay = os.path.join(W, 'out', 'ei_layouts.csv' if len(sys.argv) == 1 else 'ei_layouts_test.csv')
    with open(out, 'w', newline='') as f, open(lay, 'w', newline='') as g:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        lw = csv.writer(g)
        lw.writerow(['issue', 'table', 'unit', 'mapping', 'info'])
        for fn in fns:
            for issue, kind, m, info, unit in process_issue(fn, w):
                lw.writerow([issue, kind, unit, {k: v for k, v in m.items()}, info])
    print('wrote', out)

if __name__ == '__main__':
    main()
