"""1167 limit 3: the State production index (SPI) and the tests of doc/PREREG-1167-limit-3-state-production-2026-11-24.md. No AI.
Usage: python3 -I spi_1167.py <collection dir>   writes data/l3/spi_state_monthly_1167.csv and out/spi_tests_1167.json"""
import os, sys, json, glob, numpy as np, pandas as pd
C = sys.argv[1]; L3 = os.path.join(C, 'data', 'l3'); OUT = os.path.join(C, 'out'); os.makedirs(OUT, exist_ok=True)
ST = {'AL':'01','AK':'02','AZ':'04','AR':'05','CA':'06','CO':'08','CT':'09','DE':'10','FL':'12','GA':'13','HI':'15','ID':'16','IL':'17','IN':'18','IA':'19','KS':'20','KY':'21','LA':'22','ME':'23','MD':'24','MA':'25','MI':'26','MN':'27','MS':'28','MO':'29','MT':'30','NE':'31','NV':'32','NH':'33','NJ':'34','NM':'35','NY':'36','NC':'37','ND':'38','OH':'39','OK':'40','OR':'41','PA':'42','RI':'44','SC':'45','SD':'46','TN':'47','TX':'48','UT':'49','VT':'50','VA':'51','WA':'53','WV':'54','WI':'55','WY':'56'}
IND = ['manufacturing', 'mining', 'utilities']

def sa_log(x):   # the stress map's seasonal adjustment (collection 1052, stress_map_v3_1_1052.py), verbatim
    x = x.astype(float); T = x.rolling(12, center=True).mean().rolling(2).mean().shift(-1); r = x - T
    S = pd.Series(np.nan, index=x.index)
    for mo in range(1, 13):
        k = x.index.month == mo; s = r[k].rolling(7, center=True, min_periods=3).mean(); S[k] = s.ffill().bfill().values
    S = S - S.rolling(12, center=True).mean().rolling(2).mean().shift(-1).ffill().bfill()
    return x - S

def fred(i):
    f = os.path.join(L3, 'fred', i + '.csv')
    if not os.path.exists(f): return None
    x = pd.read_csv(f); s = pd.Series(pd.to_numeric(x.iloc[:, 1], errors='coerce').values, index=pd.to_datetime(x.iloc[:, 0])).dropna()
    return s if len(s) else None

# national output per job
NAT = {'manufacturing': (fred('IPMAN'), fred('MANEMP')), 'mining': (fred('IPMINE'), fred('USMINE')), 'utilities': (fred('IPUTIL'), fred('CES4422000001'))}
PI = {i: np.log(a / b.reindex(a.index)).dropna() for i, (a, b) in NAT.items()}

# State jobs: BLS 1990 on; QCEW SIC 1975-1991 linked on 1990-1991
Q = pd.read_csv(glob.glob(os.path.join(C, 'data', 'l3', 'qcew_sic_state_industry_1975_1991.csv'))[0] if glob.glob(os.path.join(C, 'data', 'l3', 'qcew_sic_state_industry_1975_1991.csv')) else sys.argv[2], dtype={'state_fips': str})
Q['date'] = pd.to_datetime(dict(year=Q.year, month=Q.month, day=1)); Q['employment'] = pd.to_numeric(Q.employment, errors='coerce') / 1000.0
BLS = {'manufacturing': '{st}MFGN', 'mining': '{st}NRMNN', 'utilities': 'SMU{f}000004322000001'}
E = {}; link = []
for st, f in ST.items():
    for i in IND:
        b = fred(BLS[i].format(st=st, f=f))
        if b is None: continue
        q = Q[(Q.state_fips == f) & (Q.industry == i)].set_index('date')['employment'].sort_index()
        q = q.where(q > 0)
        ov = pd.date_range('1990-01-01', '1991-12-01', freq='MS')
        if q.reindex(ov).notna().sum() >= 18 and (q.reindex(ov) > 0).sum() >= 18:
            ratio = float(b.reindex(ov).mean() / q.reindex(ov).mean()); pre = q[q.index < pd.Timestamp('1990-01-01')] * ratio
            s = pd.concat([pre, b]).sort_index(); link.append(dict(st=st, ind=i, ratio=round(ratio, 4), sic_from=str(q.first_valid_index())[:7]))
        else:
            s = b; link.append(dict(st=st, ind=i, ratio=None, sic_from=None))
        s = s.dropna(); s = s[s > 0]
        full = pd.date_range(s.index[0], s.index[-1], freq='MS'); s = s.reindex(full).interpolate(limit=3)
        if s.isna().any(): s = s[s.index > s[s.isna()].index[-1]]
        E[(st, i)] = np.log(np.exp(sa_log(np.log(s))))
# value-added weights (BEA SAGDP2, NAICS 1997 on; the 1997 shares before)
V = pd.read_csv(os.path.join(L3, 'bea', 'SAGDP2__ALL_AREAS_1997_2025.csv'), encoding='latin-1', dtype=str)
V['fips'] = V.GeoFIPS.str.strip().str.strip('"').str[:2]; V['ic'] = V.IndustryClassification.str.strip()
yrs = [c for c in V.columns if c.strip().isdigit()]
W = {}
for st, f in ST.items():
    v = V[(V.fips == f) & (V.ic.isin(['31-33', '21', '22']))].set_index('ic')[yrs].apply(pd.to_numeric, errors='coerce')
    W[st] = {'manufacturing': v.loc['31-33'], 'mining': v.loc['21'], 'utilities': v.loc['22']}
def weights(st, year):
    y = str(max(1997, min(int(yrs[-1]), year - 1)))
    w = {i: float(W[st][i][y]) for i in IND if (st, i) in E and pd.notna(W[st][i][y]) and W[st][i][y] > 0}
    t = sum(w.values()); return {i: v / t for i, v in w.items()}
idx = pd.date_range('1975-01-01', max(max(s.index[-1] for s in PI.values()), pd.Timestamp('1975-01-01')), freq='MS')
SPI = {}; COMP = {}
for st in ST:
    g = pd.Series(0.0, index=idx[1:]); okm = pd.Series(True, index=idx[1:])
    for t in idx[1:]:
        w = weights(st, t.year); tot = 0.0; ws = 0.0
        for i, wi in w.items():
            e = E[(st, i)]; p = PI[i]
            if t in e.index and t - pd.DateOffset(months=1) in e.index and t in p.index and t - pd.DateOffset(months=1) in p.index:
                tot += wi * (e[t] - e[t - pd.DateOffset(months=1)] + p[t] - p[t - pd.DateOffset(months=1)]); ws += wi
        if ws > 0: g[t] = tot / ws
        else: okm[t] = False
    last = okm[okm].index[-1]; g = g[g.index <= last]
    SPI[st] = pd.Series(100 * np.exp(np.r_[0.0, g.cumsum().values]), index=[idx[0]] + list(g.index)); COMP[st] = sorted(i for i in IND if (st, i) in E)
S = pd.DataFrame(SPI); S.index.name = 'month'; S.round(4).to_csv(os.path.join(L3, 'spi_state_monthly_1167.csv'))
# ---- tests
def bea(path, kind):
    X = pd.read_csv(path, encoding='latin-1', dtype=str); X['fips'] = X.GeoFIPS.str.strip().str.strip('"').str[:2]; X['ic'] = X.IndustryClassification.str.strip()
    cols = [c for c in X.columns if c.strip()[:4].isdigit()]; out = {}
    for st, f in ST.items():
        v = X[(X.fips == f) & X.ic.isin(['31-33', '21', '22'])][cols].apply(pd.to_numeric, errors='coerce')
        if len(v) < 1: continue
        tot = v.sum(min_count=1)
        if kind == 'q': tot.index = pd.PeriodIndex([c.replace(':', '') for c in cols], freq='Q')
        else: tot.index = pd.PeriodIndex(cols, freq='Y')
        out[st] = tot.dropna()
    return out
BQ = bea(glob.glob(os.path.join(L3, 'bea', 'SQGDP9__ALL_AREAS_*.csv'))[0], 'q'); BA = bea(os.path.join(L3, 'bea', 'SAGDP9__ALL_AREAS_1997_2025.csv'), 'a')
t1 = {}; t2 = {}
for st in ST:
    s = S[st].dropna(); sq = s.groupby(s.index.to_period('Q')).mean(); sa = s.groupby(s.index.to_period('Y')).mean()
    sq = sq[sq.index.map(lambda p: ((s.index.to_period('Q') == p).sum() == 3))]; sa = sa[sa.index.map(lambda p: ((s.index.to_period('Y') == p).sum() == 12))]
    if st in BQ:
        a = (sq.pct_change(4) * 100); b = (BQ[st].pct_change(4) * 100); j = a.index.intersection(b.index); j = [k for k in j if k >= pd.Period('2006Q1', 'Q')]
        t1[st] = round(float(np.corrcoef(a[j], b[j])[0, 1]), 3) if len(j) > 8 else None
    if st in BA:
        a = (sa.pct_change() * 100); b = (BA[st].pct_change() * 100); j = [k for k in a.index.intersection(b.index) if k >= pd.Period('1998', 'Y')]
        t2[st] = round(float(np.corrcoef(a[j], b[j])[0, 1]), 3) if len(j) > 8 else None
m1 = float(np.median([v for v in t1.values() if v is not None])); m2 = float(np.median([v for v in t2.values() if v is not None]))
# T3: the States' indexes summed with 1997 value-added weights against national IP (manufacturing, mining, utilities = total IP)
base = {st: sum(float(W[st][i]['1997']) for i in COMP[st]) for st in ST}; tw = sum(base.values())
agg = sum(np.log(S[st]) * base[st] / tw for st in ST); ip = fred('INDPRO')
a = agg.diff(12) * 100; b = np.log(ip).reindex(agg.index).diff(12) * 100; j = a.dropna().index.intersection(b.dropna().index)
t3 = round(float(np.corrcoef(a[j], b[j])[0, 1]), 3)
res = dict(T1=dict(median=round(m1, 3), bar=0.60, passed=bool(m1 >= 0.60), by_state=t1), T2=dict(median=round(m2, 3), bar=0.60, passed=bool(m2 >= 0.60), by_state=t2),
           T3=dict(corr_12m_changes_with_national_IP=t3), components=COMP, link=link, months=[str(S.index[0])[:7], str(S.index[-1])[:7]], adopted=bool(m1 >= 0.60 and m2 >= 0.60))
json.dump(res, open(os.path.join(OUT, 'spi_tests_1167.json'), 'w'), indent=1)
print(json.dumps({k: (v if k not in ('T1', 'T2') else {kk: vv for kk, vv in v.items() if kk != 'by_state'}) for k, v in res.items() if k not in ('components', 'link')}, indent=1))
print('lowest T1', sorted([(v, k) for k, v in t1.items() if v is not None])[:6]); print('lowest T2', sorted([(v, k) for k, v in t2.items() if v is not None])[:6])
