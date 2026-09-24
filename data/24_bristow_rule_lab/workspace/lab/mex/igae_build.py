"""Extract the IGAE (INEGI open data, base 2018=100, original series, 1993-01 on) and
seasonally adjust it with the same routine the speed section uses: month-of-year factors
estimated on a MOVING SEVEN-YEAR WINDOW as medians, re-estimated each December from the
data available then and applied unchanged for the following twelve months.  In logs.

Also (adopted 2 September 2026 on Anthony's word): INEGI's monthly motor-vehicle production,
1983-01 on, from INEGI's short-term indicators on DBnomics (INEGI/DF_STEI, series
MX.M.C5003.N.28.Z.Z.Z, keyless; saved as lab/acq/imss/INEGI_STEI_C5003.N.28.Z.Z.Z.csv),
adjusted with the same routine -> MEX_vehicles_sa.csv.  It is the fifth monthly series the
1985 window has; the committee does not name it.
"""
import csv, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')

MES = {'Enero':1,'Febrero':2,'Marzo':3,'Abril':4,'Mayo':5,'Junio':6,'Julio':7,
       'Agosto':8,'Septiembre':9,'Octubre':10,'Noviembre':11,'Diciembre':12}
SRC = 'igae_open/conjunto_de_datos/conjunto_de_datos_igae_igae2025_03.csv'

def series(label):
    rows = list(csv.reader(open(SRC, encoding='utf-8', errors='replace')))
    hdr = rows[0]
    row = next((r for r in rows[1:] if r[0] == label), None)
    if row is None:
        raise SystemExit(f'no row {label!r}')
    d, v = [], []
    for h, x in zip(hdr[1:], row[1:]):
        if '|' not in h: continue
        y, m = h.split('|')
        m = m.split('<')[0]                           # strips INEGI's <R> / <P> revision flags
        if m not in MES: continue                     # skips the |Anual columns
        try: val = float(x)
        except ValueError: continue
        d.append(pd.Timestamp(int(y), MES[m], 1)); v.append(val)
    return pd.Series(v, index=pd.DatetimeIndex(d)).sort_index()

def sa_realtime(s, win=7):
    """Month-of-year medians on a moving `win`-year window, refitted each December."""
    x = np.log(s) * 100.0
    tr = x.rolling(13, center=True, min_periods=7).mean().bfill().ffill()
    r = x - tr                                        # detrended, for the factors only
    out = pd.Series(np.nan, index=x.index)
    for yr in range(x.index.year.min(), x.index.year.max() + 1):
        hist = r[(r.index.year < yr) & (r.index.year >= yr - win)]
        if len(hist) < 24:                            # warm-up: use what exists
            hist = r[r.index.year < yr]
        if len(hist) < 12:
            out[x.index.year == yr] = x[x.index.year == yr]; continue
        f = hist.groupby(hist.index.month).median()
        f = f - f.mean()
        for t in x.index[x.index.year == yr]:
            out[t] = x[t] - float(f.get(t.month, 0.0))
    return np.exp(out / 100.0)

if __name__ == '__main__':
    tot = series('Índice de volumen físico base 2018=100|Total')
    print(f'IGAE total, original: {tot.index.min().date()}..{tot.index.max().date()}  n={len(tot)}')
    sa = sa_realtime(tot)
    # how much month-of-year pattern is left, in log points, before and after
    for nm, z in (('original', tot), ('adjusted', sa)):
        y = np.log(z) * 100.0
        d = y - y.rolling(13, center=True, min_periods=7).mean()
        g = d.groupby(d.index.month).median()
        print(f'  {nm}: month-of-year spread {float(g.max()-g.min()):.1f} log points')
    sa.rename('v').to_csv('MEX_igae_sa.csv', header=['value'], index_label='date')
    print('wrote MEX_igae_sa.csv')
    VEH = '/home/claude/lab/acq/imss/INEGI_STEI_C5003.N.28.Z.Z.Z.csv'
    v = pd.read_csv(VEH, index_col=0, parse_dates=True).iloc[:, 0].dropna()
    v = v[v > 0]
    print(f'vehicle production, original: {v.index.min().date()}..{v.index.max().date()}  n={len(v)}')
    vsa = sa_realtime(v)
    for nm, z in (('original', v), ('adjusted', vsa)):
        y = np.log(z) * 100.0
        d = y - y.rolling(13, center=True, min_periods=7).mean()
        g = d.groupby(d.index.month).median()
        print(f'  {nm}: month-of-year spread {float(g.max()-g.min()):.1f} log points')
    vsa.rename('v').to_csv('MEX_vehicles_sa.csv', header=['value'], index_label='date')
    print('wrote MEX_vehicles_sa.csv')
