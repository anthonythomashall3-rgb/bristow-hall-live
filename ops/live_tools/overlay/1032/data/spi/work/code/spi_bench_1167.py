"""1167 limit 3, Amendment 1 (Change B): the State production index benchmarked (Denton, proportional first differences) to BEA's official
real output of mining + manufacturing + utilities by State, annual 1977-2025 (SIC to 1997, NAICS from 1997, linked at 1997) and quarterly
2005 Q1 on; and the out-of-sample test T1b/T2b of doc/PREREG-1167-limit-3-state-production-2026-11-24.md. No AI.
Usage: python3 -I spi_bench_1167.py <collection dir>   writes data/l3/spi_state_monthly_benchmarked_1167.csv, out/spi_bench_tests_1167.json"""
import os, sys, json, glob, numpy as np, pandas as pd
C = sys.argv[1]; L3 = os.path.join(C, 'data', 'l3'); OUT = os.path.join(C, 'out')
ST = {'AL':'01','AK':'02','AZ':'04','AR':'05','CA':'06','CO':'08','CT':'09','DE':'10','FL':'12','GA':'13','HI':'15','ID':'16','IL':'17','IN':'18','IA':'19','KS':'20','KY':'21','LA':'22','ME':'23','MD':'24','MA':'25','MI':'26','MN':'27','MS':'28','MO':'29','MT':'30','NE':'31','NV':'32','NH':'33','NJ':'34','NM':'35','NY':'36','NC':'37','ND':'38','OH':'39','OK':'40','OR':'41','PA':'42','RI':'44','SC':'45','SD':'46','TN':'47','TX':'48','UT':'49','VT':'50','VA':'51','WA':'53','WV':'54','WI':'55','WY':'56'}
S = pd.read_csv(os.path.join(L3, 'spi_state_monthly_1167.csv'), index_col=0, parse_dates=True)

def bea_sum(path, codes, kind):
    X = pd.read_csv(path, encoding='latin-1', dtype=str); X['fips'] = X.GeoFIPS.str.strip().str.strip('"').str[:2]; X['ic'] = X.IndustryClassification.str.strip().str.strip('"')
    cols = [c for c in X.columns if c.strip()[:4].isdigit()]; out = {}; supp = {}
    for st, f in ST.items():
        v = X[(X.fips == f) & X.ic.isin(codes)].set_index('ic')[cols]
        num = v.apply(pd.to_numeric, errors='coerce'); supp[st] = int(num.isna().sum().sum())
        num = num.T.interpolate(limit_area='inside').T                      # a suppressed cell inside the run: straight line between its neighbours
        tot = num.sum(min_count=len(codes))
        tot.index = pd.PeriodIndex([c.replace(':', '') for c in cols], freq='Q') if kind == 'q' else pd.PeriodIndex(cols, freq='Y')
        out[st] = tot.dropna()
    return out, supp
A_sic, s1 = bea_sum(os.path.join(L3, 'bea', 'SAGDP9S__ALL_AREAS_1977_1997.csv'), ['B', 'D', '49'], 'a')
A_nai, s2 = bea_sum(os.path.join(L3, 'bea', 'SAGDP9__ALL_AREAS_1997_2025.csv'), ['21', '31-33', '22'], 'a')
Q_nai, s3 = bea_sum(glob.glob(os.path.join(L3, 'bea', 'SQGDP9__ALL_AREAS_*.csv'))[0], ['21', '31-33', '22'], 'q')
ANN = {}
for st in ST:
    a, b = A_sic.get(st), A_nai.get(st)
    if b is None or not len(b): continue
    if a is not None and pd.Period('1997', 'Y') in a.index and pd.Period('1997', 'Y') in b.index:
        k = b[pd.Period('1997', 'Y')] / a[pd.Period('1997', 'Y')]; ANN[st] = pd.concat([a[a.index < pd.Period('1997', 'Y')] * k, b]).sort_index()
    else: ANN[st] = b

def denton(ind, bench, freq):
    """monthly x with mean over each benchmark period = the benchmark, x/ind as smooth as possible (first differences); ind: monthly Series
    bench: list of (Period, value) with freq 'Y' or 'Q' (or a mix)"""
    n = len(ind); I = ind.values.astype(float); per = ind.index
    rows = []; rhs = []
    for p, v in bench:
        m = np.array([(t.to_period(p.freqstr[0]) == p) for t in per])
        if m.sum() != (12 if p.freqstr[0] == 'Y' else 3): continue
        a = np.zeros(n); a[m] = I[m] / m.sum(); rows.append(a); rhs.append(v)
    A = np.array(rows); k = len(rows)
    D = np.diff(np.eye(n), axis=0); K = np.zeros((n + k, n + k)); K[:n, :n] = 2 * D.T @ D; K[:n, n:] = A.T; K[n:, :n] = A
    sol = np.linalg.lstsq(K, np.r_[np.zeros(n), np.array(rhs)], rcond=None)[0]
    return pd.Series(sol[:n] * I, index=per)

def qmean(x):
    g = x.groupby(x.index.to_period('Q')); m = g.mean(); c = g.size(); return m[c == 3]

res = {}; T1 = {}; T2 = {}; DEP = []; BEN = {}
for st in ST:
    if st not in ANN or st not in Q_nai: continue
    i = S[st].dropna(); i = i[i.index >= pd.Timestamp('1975-01-01')]
    ab = [(p, v) for p, v in ANN[st].items() if p.year >= 1977]
    x_a = denton(i, ab, 'Y')                                                    # annual only (the test)
    qb = [(p, v) for p, v in Q_nai[st].items()]
    x_q = denton(i, [(p, v) for p, v in ab if p.year < 2005] + qb, 'mix')       # the index adopted if the tests pass
    BEN[st] = x_q / x_q[x_q.index.year == 2017].mean() * 100
    q = qmean(x_a); b = Q_nai[st]
    j4 = [p for p in q.index.intersection(b.index) if p >= pd.Period('2006Q1', 'Q')]
    a4 = q.pct_change(4)[j4]; b4 = b.pct_change(4)[j4]; T1[st] = round(float(np.corrcoef(a4, b4)[0, 1]), 3)
    j1 = [p for p in q.index.intersection(b.index) if p >= pd.Period('2005Q2', 'Q')]
    a1 = q.pct_change()[j1]; b1 = b.pct_change()[j1]; T2[st] = round(float(np.corrcoef(a1, b1)[0, 1]), 3)
    def fall(s, a, z):
        w = s[(s.index >= pd.Period(a, 'Q')) & (s.index <= pd.Period(z, 'Q'))]; pk = w.idxmax(); return float(100 * (1 - w[w.index >= pk].min() / w.max()))
    DEP.append(dict(st=st, f0809_index=fall(q, '2007Q3', '2010Q4'), f0809_bea=fall(b, '2007Q3', '2010Q4'), f2020_index=fall(q, '2019Q4', '2021Q2'), f2020_bea=fall(b, '2019Q4', '2021Q2')))
DP = pd.DataFrame(DEP)
# 24 Nov 2026: a State with no quarterly BEA total (Delaware) has no correlation (NaN). The test is read over the States that can be scored, and
# again with every unscored State counted as a failure (below every scored State), as the PREREG result states.
def _med(T, worst=False):
    v = [x for x in T.values() if x is not None and np.isfinite(x)]; k = len(T) - len(v)
    return float(np.median(v + [-9.0] * k)) if worst else float(np.median(v))
m1 = _med(T1); m2 = _med(T2); m1w = _med(T1, True); m2w = _med(T2, True)
out = dict(T1b=dict(median=round(m1, 3), median_unscored_as_failure=round(m1w, 3), scored=int(sum(1 for x in T1.values() if x is not None and np.isfinite(x))), bar=0.80, passed=bool(m1 >= 0.80 and m1w >= 0.80), by_state=T1), T2b=dict(median=round(m2, 3), median_unscored_as_failure=round(m2w, 3), scored=int(sum(1 for x in T2.values() if x is not None and np.isfinite(x))), bar=0.40, passed=bool(m2 >= 0.40 and m2w >= 0.40), by_state=T2),
           depth_corr=dict(f2007_09=round(float(DP.f0809_index.corr(DP.f0809_bea)), 3), f2020=round(float(DP.f2020_index.corr(DP.f2020_bea)), 3)),
           suppressed_cells=dict(sic_annual=s1, naics_annual=s2, naics_quarterly=s3), adopted=bool(m1 >= 0.80 and m2 >= 0.40), states=len(T1))
json.dump(out, open(os.path.join(OUT, 'spi_bench_tests_1167.json'), 'w'), indent=1)
B = pd.DataFrame(BEN); B.index.name = 'month'; B.round(4).to_csv(os.path.join(L3, 'spi_state_monthly_benchmarked_1167.csv'))
DP.round(3).to_csv(os.path.join(OUT, 'spi_bench_depths_1167.csv'), index=False)
print(json.dumps({k: ({kk: vv for kk, vv in v.items() if kk != 'by_state'} if isinstance(v, dict) and 'by_state' in v else v) for k, v in out.items() if k != 'suppressed_cells'}, indent=1))
print('lowest T1b', sorted((v, k) for k, v in T1.items())[:6]); print('lowest T2b', sorted((v, k) for k, v in T2.items())[:6])
