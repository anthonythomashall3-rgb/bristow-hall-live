#!/usr/bin/env python3
"""Assemble as-printed series and vintage tables from parsed fields.

Inputs : out/ei_fields_long.csv (Economic Indicators) [+ out/ee_fields_long.csv (Employment and Earnings) if present]
Outputs: out/asprinted_long.csv            tidy: series, basis, ref_month, value, source, issue, pub_date, flags ...
         out/vintages/<SERIES>_asprinted_vintages.csv   wide: date + one column per publication (SERIES_YYYYMMDD)
         out/doubtful_cells.csv            cells withheld from the wide tables (OCR not confirmed)
         out/alfred_validation.csv / out/alfred_validation_summary.csv
Publication date convention: pub_date = last calendar day of the issue month (EI and E&E print
no release day; the underlying press release came earlier in that month).
"""
import calendar, csv, glob, os, re, sys
from collections import defaultdict
import pandas as pd
import numpy as np

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(W, 'out')
ALF = '/home/user/bristow-hall-live/data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages'

# (table, field, basis) -> output series name
SERIES = {
    ('LF', 'UR', 'SA'): 'UNRATE',
    ('LF', 'UR', 'NSA'): 'UNRATENSA',
    ('LF', 'CLF', 'NSA'): 'CLF14NSA',
    ('LF', 'CLF', 'SA'): 'CLF14SA',
    ('LF', 'UNEMP', 'NSA'): 'UNEMPLOY14NSA',
    ('LF', 'UNEMP', 'SA'): 'UNEMPLOY14SA',
    ('LF', 'EMP', 'NSA'): 'CE14NSA',
    ('LF', 'EMP', 'SA'): 'CE14SA',
    ('EMP', 'MFG', 'SA'): 'MANEMP',
    ('EMP', 'MFG', 'NSA'): 'MANEMPNSA',
    ('EMP', 'NDUR', 'SA'): 'NDMANEMP',
    ('EMP', 'NDUR', 'NSA'): 'NDMANEMPNSA',
    ('EMP', 'DUR', 'SA'): 'DMANEMP',
    ('EMP', 'DUR', 'NSA'): 'DMANEMPNSA',
    ('EMP', 'PAY', 'SA'): 'PAYEMS',
    ('EMP', 'PAY', 'NSA'): 'PAYNSA',
    ('EMP', 'PAY_XAKHI', 'SA'): 'PAYEMS_XAKHI',
    ('HRS', 'HRS_MFG', 'SA'): 'AWHMAN',
    ('HRS', 'HRS_MFG', 'NSA'): 'AWHMANNSA',
    ('HRS', 'HRS_NDUR', 'NSA'): 'AWHNONDURNSA',
    ('HRS', 'HRS_DUR', 'NSA'): 'AWHDURNSA',
}
ALFRED_OF = {'UNRATE': 'UNRATE', 'CLF14SA': 'CLF16OV', 'CE14SA': 'CE16OV', 'MANEMP': 'MANEMP', 'NDMANEMP': 'NDMANEMP',
             'DMANEMP': 'DMANEMP', 'PAYEMS': 'PAYEMS', 'AWHMAN': 'AWHMAN'}

def month_end(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f'{y}{m:02d}{calendar.monthrange(y, m)[1]:02d}'

def cps_basis(ref, issue, label):
    lab = label.lower() if isinstance(label, str) else ''
    if 'area' in lab and '68' in lab:
        return '68-area sample'
    parts = []
    if ref < '1954-01' or ('68' in lab):
        parts.append('68-area sample')
    else:
        parts.append('230-area-sample era (Jan 1954 on)')
    if ref >= '1957-01' and issue >= '1957-02':
        parts.append('Jan-1957 definitions')
    else:
        parts.append('pre-1957 definitions')
    if ref >= '1960-01':
        parts.append('incl. Alaska & Hawaii')
    return '; '.join(parts) + '; age 14+'

def load():
    frames = []
    for src, fn in (('EI', 'ei_fields_long.csv'), ('EE', 'ee_fields_long.csv'), ('MLR', 'mlr_fields_long.csv')):
        p = os.path.join(OUT, fn)
        if os.path.exists(p):
            d = pd.read_csv(p, dtype=str)
            d['source'] = src
            if src == 'EE':
                # E&E pages parsed by row order; keep only cells whose table passed its identity
                # (TOTAL = sum of 8 divisions; manufacturing hours between durable and nondurable)
                d = d[d.identity == 'ok']
            if src == 'MLR':
                # single text-layer reading: keep labour-force rows only when CLF = EMP + UNEMP holds,
                # employment rows (A-2); hours parse (C-1) not reliable -> dropped
                d = d[(d.table == 'EMP') | ((d.table == 'LF') & ((d.identity == 'ok') | (d.field == 'UR')))]
            frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d['value'] = pd.to_numeric(d['value'], errors='coerce')
    d['occ'] = pd.to_numeric(d['occ'], errors='coerce').fillna(1).astype(int)
    d = d[d.ref.notna() & d.value.notna()].copy()
    d['series'] = [SERIES.get((t, f, b)) for t, f, b in zip(d.table, d.field, d.basis)]
    d = d[d.series.notna()].copy()
    # millions -> thousands for level series printed in millions (1961 EI)
    mil = (d.unit == 'millions') & d.series.str.match(r'^(CLF|UNEMPLOY|CE)')
    d.loc[mil, 'value'] = (d.loc[mil, 'value'] * 1000).round(0)
    d['precision'] = np.where(mil, 'printed in millions (1 decimal)', '')
    return d

def parse_readings(s):
    out = []
    if not isinstance(s, str):
        return out
    for part in s.split('|'):
        k, _, v = part.partition('=')
        try:
            out.append(float(v))
        except ValueError:
            pass
    return out

def locked(d, i):
    """Cell validated within its own table (accounting identity or identity-based resolution)."""
    return d.at[i, 'identity'] == 'ok' or 'resolved' in str(d.at[i, 'flags'])

def neighborhood_vote(d, window=2):
    """For each OCR'd cell, pool the readings of the same series/ref printed in the +-window
    neighbouring issues and pick, among the cell's OWN readings, the value with most support.
    Cells validated by an accounting identity are left alone."""
    d['support'] = np.nan
    d['nvote'] = ''
    cur = d[d.is_current & d.readings.notna() & (d.readings != '')]
    for (s, ref, src), g in cur.groupby(['series', 'ref', 'source']):
        g = g.sort_values('issue')
        idx = list(g.index)
        scale = [1000.0 if str(pr).startswith('printed in millions') else 1.0 for pr in g.precision]
        rds = [[round(v * sc, 6) for v in parse_readings(x)] for x, sc in zip(g.readings, scale)]
        for k, i in enumerate(idx):
            own = [v for v in rds[k] if v is not None]
            if not own:
                continue
            pool = []
            for j in range(max(0, k - window), min(len(idx), k + window + 1)):
                pool += rds[j]
            sup = {v: sum(1 for p in pool if abs(p - v) < 1e-9) for v in set(own)}
            best = max(sup.values())
            cands = [v for v, n in sup.items() if n == best]
            curv = d.at[i, 'final']
            choice = curv if curv in cands else sorted(cands)[0]
            if locked(d, i):
                choice = curv
            d.at[i, 'support'] = sum(1 for p in pool if abs(p - choice) < 1e-9)
            if choice != curv:
                d.at[i, 'final'] = choice
                d.at[i, 'nvote'] = f'neighbourhood_vote:{curv}->{choice}'
    return d

CONFUSE = {'3': '8', '8': '3', '5': '6', '6': '5'}

def variants(v):
    """Glyph-confusion variants of a one-decimal rate (italic 3/8 and 5/6)."""
    t = f'{v:.1f}'
    out = set()
    for i, ch in enumerate(t):
        if ch in CONFUSE:
            out.add(float(t[:i] + CONFUSE[ch] + t[i + 1:]))
    return out

def sa_rate_check(d, tol_bad=0.08, tol_good=0.04):
    """Seasonally adjusted rate vs the NSA rate printed in the same row: the implied factor NSA/SA
    for a calendar month is stable across years. A cell whose factor deviates by more than tol_bad
    from the median factor of that calendar month (same and adjacent years, other cells) is
    re-chosen among its own OCR readings and their italic-glyph variants (3/8, 5/6) if one fits
    within tol_good; otherwise it is flagged."""
    d['sfcheck'] = ''
    cur = d.is_current
    sa = d[cur & (d.series == 'UNRATE')]
    ns = d[cur & (d.series == 'UNRATENSA')].set_index(['source', 'issue', 'ref'])['final']
    fac = {}
    for i, r in sa.iterrows():
        n = ns.get((r.source, r.issue, r.ref))
        if n is not None and r.final:
            fac[i] = (int(r.ref[:4]), r.ref[5:7], n / r.final, n)
    for i, (y, cm, f, n) in fac.items():
        peers = [ff for j, (yy, cc, ff, _) in fac.items() if j != i and cc == cm and abs(yy - y) <= 1]
        if len(peers) < 5:
            continue
        med = float(np.median(peers))
        if abs(f - med) <= tol_bad:
            continue
        own = parse_readings(d.at[i, 'readings'])
        cands = set(own)
        for v in list(own) + [d.at[i, 'final']]:
            cands |= variants(v)
        best = min(cands, key=lambda c: abs(n / c - med)) if cands else None
        if best is not None and abs(n / best - med) <= tol_good:
            src = 'own_reading' if best in own else 'glyph_variant'
            d.at[i, 'sfcheck'] = f'sa_factor_check:{d.at[i, "final"]}->{best}({src})'
            d.at[i, 'final'] = best
        else:
            d.at[i, 'sfcheck'] = 'SA_FACTOR_IMPLAUSIBLE'
    return d

SPIKE_THR = {'PAYEMS': 0.03, 'PAYEMS_XAKHI': 0.03, 'MANEMP': 0.04, 'NDMANEMP': 0.04, 'DMANEMP': 0.05,
             'PAYNSA': 0.05, 'MANEMPNSA': 0.05, 'NDMANEMPNSA': 0.05, 'DMANEMPNSA': 0.06,
             'CLF14NSA': 0.04, 'CE14NSA': 0.05, 'CLF14SA': 0.03, 'CE14SA': 0.03,
             'AWHMAN': 0.04, 'AWHMANNSA': 0.05, 'AWHDURNSA': 0.05, 'AWHNONDURNSA': 0.05}
DIGIT_CONF = {'3': '85', '8': '3605', '5': '63', '6': '58', '1': '7', '7': '1', '0': '86', '9': '8'}

def digit_variants(v):
    t = str(int(v)) if float(v).is_integer() else f'{v:.1f}'
    out = set()
    for i, ch in enumerate(t):
        for rep in DIGIT_CONF.get(ch, ''):
            try:
                out.add(float(t[:i] + rep + t[i + 1:]))
            except ValueError:
                pass
    return out

def spike_check(d):
    """Within one issue, a level that jumps away from BOTH adjacent months while those two agree is an
    OCR spike: re-chosen among its own readings and single-digit glyph variants when one fits, else flagged."""
    d['spike'] = ''
    cur = d[d.is_current & d.series.isin(list(SPIKE_THR))]
    for (s, src, iss), g in cur.groupby(['series', 'source', 'issue']):
        g = g.sort_values('ref')
        idx = list(g.index)
        thr = SPIKE_THR[s]
        for k in range(len(idx)):
            v = d.at[idx[k], 'final']
            if 0 < k < len(idx) - 1:
                a, b = d.at[idx[k - 1], 'final'], d.at[idx[k + 1], 'final']
            elif k == 0 and len(idx) >= 3:      # first row: compare with the next two
                a, b = d.at[idx[1], 'final'], d.at[idx[2], 'final']
            elif k == len(idx) - 1 and len(idx) >= 3:  # last row: previous two
                a, b = d.at[idx[k - 2], 'final'], d.at[idx[k - 1], 'final']
            else:
                continue
            if not (a and b and v) or locked(d, idx[k]):
                continue
            if abs(v / a - 1) > thr and abs(v / b - 1) > thr and abs(b / a - 1) < thr / 2:
                own = parse_readings(d.at[idx[k], 'readings'])
                if str(d.at[idx[k], 'precision']).startswith('printed in millions'):
                    own = [x * 1000 for x in own]
                cands = set(own)   # only this cell's own OCR readings (no invented variants)
                mid = (a + b) / 2
                good = [c for c in cands if abs(c / mid - 1) <= thr / 2]
                if good:
                    best = min(good, key=lambda c: abs(c - mid))
                    d.at[idx[k], 'spike'] = f'spike_fixed:{v}->{best}'
                    d.at[idx[k], 'final'] = best
                else:
                    d.at[idx[k], 'spike'] = 'SPIKE'
    return d

LEVELS = [k for k in SPIKE_THR if not k.startswith('AWH')]

def xissue_glyph(d, thr=0.03):
    """Level printed for the same reference month in adjacent issues: a jump > thr that a single
    glyph confusion explains (variant equals the adjacent print within 0.2%) is corrected and flagged;
    an unexplained jump > 2*thr is flagged doubtful."""
    d['xglyph'] = ''
    cur = d[d.is_current & d.series.isin(LEVELS)]
    for (s, ref, src), g in cur.groupby(['series', 'ref', 'source']):
        g = g.sort_values('issue')
        idx = list(g.index)
        for k, i in enumerate(idx):
            v = d.at[i, 'final']
            adj = [d.at[idx[j], 'final'] for j in (k - 1, k + 1) if 0 <= j < len(idx)]
            if not adj or not v:
                continue
            if all(abs(v / a - 1) > thr for a in adj):
                if locked(d, i):
                    continue
                own = parse_readings(d.at[i, 'readings'])
                if str(d.at[i, 'precision']).startswith('printed in millions'):
                    own = [x * 1000 for x in own]
                hit = [(a, x) for a in adj for x in own if abs(x / a - 1) <= 0.002]
                if hit:
                    a, x = hit[0]
                    d.at[i, 'xglyph'] = f'xissue_own_reading_fix:{v}->{x}'
                    d.at[i, 'final'] = x
                elif all(abs(v / a - 1) > 2 * thr for a in adj):
                    d.at[i, 'xglyph'] = 'XISSUE_LEVEL_JUMP'
    return d

def xissue_median(d, thr=0.10, fit=0.005):
    """A level more than thr away from the median of all prints of the same reference month
    (same series and source) is replaced by an own reading or single-glyph variant lying within
    `fit` of that median; otherwise flagged."""
    d['xmed'] = ''
    cur = d[d.is_current & d.series.isin(LEVELS)]
    for (s, ref, src), g in cur.groupby(['series', 'ref', 'source']):
        if len(g) < 3:
            continue
        lk = [d.at[i, 'final'] for i in g.index if locked(d, i)]
        med = float(np.median(lk)) if len(lk) >= 2 else float(np.median(g.final))
        for i in g.index:
            v = d.at[i, 'final']
            if abs(v / med - 1) <= thr or locked(d, i):
                continue
            own = parse_readings(d.at[i, 'readings'])
            if str(d.at[i, 'precision']).startswith('printed in millions'):
                own = [x * 1000 for x in own]
            cands = set(own)   # own readings only
            good = sorted((c for c in cands if abs(c / med - 1) <= fit), key=lambda c: abs(c / med - 1))
            if good:
                d.at[i, 'xmed'] = f'xissue_median_fix:{v}->{good[0]}' + ('' if good[0] in own else '(glyph_variant)')
                d.at[i, 'final'] = good[0]
            else:
                d.at[i, 'xmed'] = 'FAR_FROM_XISSUE_MEDIAN'
    return d

PAIRS = [('PAYNSA', 'PAYEMS', 0.05), ('MANEMPNSA', 'MANEMP', 0.06), ('NDMANEMPNSA', 'NDMANEMP', 0.06),
         ('CLF14NSA', 'CLF14SA', 0.05), ('AWHMANNSA', 'AWHMAN', 0.04)]

def basis_pair_check(d):
    """NSA and SA prints of the same series, issue and month differ only by seasonality."""
    d['pair'] = ''
    cur = d[d.is_current]
    for a, b, tol in PAIRS:
        A = cur[cur.series == a].set_index(['source', 'issue', 'ref'])
        B = cur[cur.series == b].set_index(['source', 'issue', 'ref'])
        common = A.index.intersection(B.index)
        for key in common:
            ia, ib = A.loc[key, 'final'], B.loc[key, 'final']
            ia_i = cur[(cur.series == a) & (cur.source == key[0]) & (cur.issue == key[1]) & (cur.ref == key[2])].index[0]
            ib_i = cur[(cur.series == b) & (cur.source == key[0]) & (cur.issue == key[1]) & (cur.ref == key[2])].index[0]
            va, vb = d.at[ia_i, 'final'], d.at[ib_i, 'final']
            if va and vb and abs(va / vb - 1) > tol:
                for i in (ia_i, ib_i):
                    if not locked(d, i):
                        d.at[i, 'pair'] = 'NSA_SA_MISMATCH'
    return d

def column_median_check(d):
    """Within one issue, a level far from the median of its own column (all months printed in that
    issue) is flagged: 5% for SA series, 8% for NSA series."""
    d['colmed'] = ''
    cur = d[d.is_current & d.series.isin(LEVELS)]
    for (s, src, iss), g in cur.groupby(['series', 'source', 'issue']):
        if len(g) < 5:
            continue
        thr = 0.08 if 'NSA' in s else 0.05
        med = float(np.median(g.final))
        for i in g.index:
            if abs(d.at[i, 'final'] / med - 1) > thr and not locked(d, i):
                d.at[i, 'colmed'] = 'FAR_FROM_ISSUE_COLUMN_MEDIAN'
    return d

def xissue(d):
    """Cross-issue consistency: compare each print with the same series/ref in neighbouring issues."""
    d = d.sort_values(['series', 'ref', 'source', 'issue', 'occ']).copy()
    # current basis = last occurrence within an issue
    d['is_current'] = d.groupby(['series', 'ref', 'source', 'issue'])['occ'].transform('max') == d['occ']
    d['xcheck'] = ''
    d['final'] = d['value']
    d = neighborhood_vote(d)
    d = sa_rate_check(d)
    d = xissue_median(d)
    d = spike_check(d)
    d = xissue_glyph(d)
    d = basis_pair_check(d)
    d = column_median_check(d)
    for (s, ref, src), g in d[d.is_current].groupby(['series', 'ref', 'source']):
        idx = list(g.index)
        vals = list(g.final)
        alts = [str(a) if isinstance(a, str) else '' for a in g.alts]
        for k, i in enumerate(idx):
            prv = vals[k - 1] if k > 0 else None
            nxt = vals[k + 1] if k + 1 < len(vals) else None
            v = vals[k]
            same = (prv is not None and abs(v - prv) < 1e-9) or (nxt is not None and abs(v - nxt) < 1e-9)
            if same:
                d.at[i, 'xcheck'] = 'confirmed_by_adjacent_issue'
            elif prv is not None and nxt is not None and abs(prv - nxt) < 1e-9:
                altv = [float(a) for a in alts[k].split(';') if a not in ('', 'nan')]
                if any(abs(a - prv) < 1e-9 for a in altv):
                    d.at[i, 'final'] = prv
                    d.at[i, 'xcheck'] = 'resolved_to_alternate_reading_matching_adjacent_issues'
                else:
                    d.at[i, 'xcheck'] = 'OUTLIER_vs_adjacent_issues'
            elif prv is None and nxt is None:
                d.at[i, 'xcheck'] = 'single_print'
            else:
                d.at[i, 'xcheck'] = 'differs_from_adjacent (revision or OCR)'
    return d

def doubtful(r):
    reasons = []
    if r.get('identity') == 'FAIL':
        reasons.append('identity_fail')
    if r['xcheck'] == 'OUTLIER_vs_adjacent_issues':
        reasons.append('xissue_outlier')
    try:
        na, nv = int(r['n_agree']), int(r['n_valid'])
    except (ValueError, TypeError):
        na, nv = None, None
    confirmed = r['xcheck'].startswith('confirmed') or r['xcheck'].startswith('resolved') or r.get('identity') == 'ok' \
        or str(r.get('flags', '')).startswith('identity_resolved')
    sup = r.get('support')
    if na is not None and nv is not None and na < 2 and not confirmed and not (sup == sup and sup is not None and sup >= 3):
        reasons.append('ocr_readings_disagree_unconfirmed')
    if r.get('colmed') == 'FAR_FROM_ISSUE_COLUMN_MEDIAN':
        reasons.append('far_from_issue_column_median')
    if r.get('pair') == 'NSA_SA_MISMATCH':
        reasons.append('nsa_sa_totals_inconsistent')
    if r.get('xmed') == 'FAR_FROM_XISSUE_MEDIAN':
        reasons.append('far_from_median_of_all_prints')
    if r.get('xglyph') == 'XISSUE_LEVEL_JUMP':
        reasons.append('level_jump_vs_adjacent_issues')
    if r.get('spike') == 'SPIKE':
        reasons.append('isolated_spike_vs_adjacent_months')
    if r.get('sfcheck') == 'SA_FACTOR_IMPLAUSIBLE':
        reasons.append('sa_nsa_factor_implausible')
    if str(r.get('month_inferred')) == '1' and not confirmed:
        reasons.append('month_label_inferred')
    return ';'.join(reasons)

def main():
    d = load()
    d = xissue(d)
    d['doubt'] = [doubtful(r) for _, r in d.iterrows()]
    d['pub_date'] = [month_end(i) for i in d.issue]
    d['pub_date_basis'] = d.source.map({
        'EI': 'Economic Indicators issue month (last day); press release was earlier in that month',
        'EE': 'Employment and Earnings issue month (last day)',
        'MLR': 'Monthly Labor Review issue month (last day)'})
    d['cps_basis'] = [cps_basis(r, i, l) if t == 'LF' else '' for r, i, l, t in zip(d.ref, d.issue, d.row_basis_label, d.table)]
    cols = ['series', 'basis', 'ref', 'final', 'value', 'source', 'issue', 'pub_date', 'pub_date_basis', 'occ', 'is_current',
            'row_basis_label', 'cps_basis', 'unit', 'precision', 'derived', 'n_agree', 'n_valid', 'alts', 'readings',
            'identity', 'flags', 'nvote', 'sfcheck', 'xmed', 'spike', 'xglyph', 'pair', 'colmed', 'support', 'xcheck', 'doubt', 'page', 'month_inferred']
    long = d[cols].rename(columns={'ref': 'ref_month', 'final': 'value', 'value': 'value_ocr_consensus'})
    long.sort_values(['series', 'ref_month', 'pub_date', 'source', 'occ']).to_csv(os.path.join(OUT, 'asprinted_long.csv'), index=False)
    long[long.doubt != ''].to_csv(os.path.join(OUT, 'doubtful_cells.csv'), index=False)
    # wide vintage tables: current occurrence, not doubtful
    vd = os.path.join(OUT, 'vintages')
    os.makedirs(vd, exist_ok=True)
    good = long[(long.is_current) & (long.doubt == '')]
    os.makedirs(os.path.join(vd, 'by_source'), exist_ok=True)
    for s, g in good.groupby('series'):
        g = g.copy()
        # per-source tables
        for src, gs in g.groupby('source'):
            w = gs.pivot_table(index='ref_month', columns='pub_date', values='value', aggfunc='first')
            w.columns = [f'{s}_{c}' for c in w.columns]
            w.index = [f'{x}-01' for x in w.index]
            w.index.name = 'date'
            w.to_csv(os.path.join(vd, 'by_source', f'{s}_{src}_vintages.csv'))
        # merged table in the ALFRED layout (SERIES_YYYYMMDD); on a shared issue month the
        # Economic Indicators print is used (E&E / MLR prints of that month are in by_source/)
        g['prio'] = g.source.map({'EI': 0, 'EE': 1, 'MLR': 2})
        g = g.sort_values('prio').drop_duplicates(['ref_month', 'pub_date'])
        keep_src = g.groupby('pub_date').source.agg(lambda x: sorted(set(x)))
        # one source per publication column
        first_src = g.groupby('pub_date').prio.min()
        g = g[g.prio == g.pub_date.map(first_src)]
        w = g.pivot_table(index='ref_month', columns='pub_date', values='value', aggfunc='first')
        w.columns = [f'{s}_{c}' for c in w.columns]
        w.index = [f'{x}-01' for x in w.index]
        w.index.name = 'date'
        w.to_csv(os.path.join(vd, f'{s}_asprinted_vintages.csv'))
        srcmap = g.drop_duplicates('pub_date')[['pub_date', 'source', 'issue']]
        srcmap.insert(0, 'column', [f'{s}_{c}' for c in srcmap.pub_date])
        srcmap.to_csv(os.path.join(vd, 'by_source', f'{s}_columns_source.csv'), index=False)
    validate(long)
    print(long.groupby(['series']).agg(n=('value', 'size'), doubtful=('doubt', lambda x: (x != '').sum()),
                                       first_ref=('ref_month', 'min'), last_ref=('ref_month', 'max'),
                                       first_issue=('issue', 'min'), last_issue=('issue', 'max')).to_string())

def validate(long):
    rows = []
    for s, a in ALFRED_OF.items():
        fn = os.path.join(ALF, f'{a}_all_vintages.csv')
        if not os.path.exists(fn):
            continue
        al = pd.read_csv(fn)
        al['ref'] = al['date'].str[:7]
        al = al.set_index('ref')
        vcols = sorted([c for c in al.columns if re.match(rf'{a}_\d{{8}}$', c)], key=lambda c: c[-8:])
        g = long[(long.series == s) & (long.is_current)]
        for (issue, src), gi in g.groupby(['issue', 'source']):
            pd_ = month_end(issue)
            cand = [c for c in vcols if c[-8:] <= pd_]
            if not cand:
                continue
            vc = cand[-1]
            # EI/E&E print no release day: a vintage released late in the issue month may postdate
            # the print, so the previous vintage is also an admissible comparator.
            vprev = cand[-2] if len(cand) > 1 and cand[-1][-8:-2] == pd_[:6] else None
            for _, r in gi.iterrows():
                if r.ref_month not in al.index:
                    continue
                av = al.at[r.ref_month, vc]
                if pd.isna(av):
                    continue
                pv = r.value
                def eq(a):
                    if pd.isna(a):
                        return False
                    if s.startswith(('CLF', 'CE')) and r.precision:
                        return abs(a - pv) <= 50
                    return abs(a - pv) < 1e-6
                match = eq(av)
                matched_vintage = vc[-8:] if match else ''
                if not match and vprev is not None and r.ref_month in al.index:
                    avp = al.at[r.ref_month, vprev]
                    if eq(avp):
                        match, matched_vintage, av = True, vprev[-8:], avp
                rows.append(dict(series=s, alfred_series=a, source=src, issue=issue, pub_date=pd_, alfred_vintage=vc[-8:],
                                 matched_vintage=matched_vintage,
                                 ref_month=r.ref_month, printed=pv, alfred=av, match=match, doubt=r.doubt,
                                 xcheck=r.xcheck, readings=r.readings))
    v = pd.DataFrame(rows)
    if v.empty:
        return
    v.to_csv(os.path.join(OUT, 'alfred_validation.csv'), index=False)
    summ = v.groupby(['series', 'source']).agg(n=('match', 'size'), n_match=('match', 'sum'),
                                               first_issue=('issue', 'min'), last_issue=('issue', 'max')).reset_index()
    summ['share_match'] = (summ.n_match / summ.n).round(3)
    summ.to_csv(os.path.join(OUT, 'alfred_validation_summary.csv'), index=False)
    print(summ.to_string())

if __name__ == '__main__':
    main()
