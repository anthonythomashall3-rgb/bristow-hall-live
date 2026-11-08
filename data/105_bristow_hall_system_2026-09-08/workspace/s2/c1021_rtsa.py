"""s2/c1021_rtsa.py - collection 298's real-time seasonal adjustment of a weekly NSA series, VERBATIM (build_panel.py helpers: holidays, week keys,
10 harmonics, 7-year medians, factors refitted every 1 January from data published before it). Collection 300 used it to build the
record's real-time SA claims (weekly_claims_rtsa_1946_2026.csv); C1021's count door reads the same construction live (1022)."""
import numpy as np, pandas as pd
import datetime as _dt
def _nthwd(y, m, wd, n):
    d = _dt.date(y, m, 1); d += _dt.timedelta(days=(wd - d.weekday()) % 7); return d + _dt.timedelta(weeks=n - 1)
def _lastmon(y, m):
    d = _dt.date(y + (m == 12), (m % 12) + 1, 1) - _dt.timedelta(days=1); return d - _dt.timedelta(days=d.weekday())
HOL = {}
for _y in range(1940, 2061):   # 1022: through 2060 (298: 2032)
    HOL[_y] = {'TG': pd.Timestamp(_nthwd(_y, 11, 3, 4)), 'J4': pd.Timestamp(_dt.date(_y, 7, 4)),
               'MD': pd.Timestamp(_lastmon(_y, 5)), 'LD': pd.Timestamp(_nthwd(_y, 9, 0, 1)), 'XM': pd.Timestamp(_dt.date(_y, 12, 25))}
HKEYS = [('TG', -1), ('TG', 0), ('TG', 1), ('TG', 2), ('J4', 0), ('J4', 1), ('MD', 0), ('MD', 1), ('LD', 0), ('LD', 1),
         ('XM', -1), ('XM', 0), ('XM', 1), ('XM', 2)]
KH = 10                                                     # harmonics of the smooth (non-holiday) seasonal curve
def fourier_smooth(f52, K=KH):
    x = np.arange(52) * 2 * np.pi / 52
    X = np.column_stack([np.ones(52)] + [g(k * x) for k in range(1, K + 1) for g in (np.cos, np.sin)])
    b, *_ = np.linalg.lstsq(X, f52, rcond=None); return X @ b
def week_key(t):
    """week-of-year 0..51 by day of year, except the weeks around the moving holidays, keyed to the holiday:
    52+i for HKEYS[i] (the week ended Saturday t contains the holiday when t-6 <= h <= t; k weeks after for offset k)."""
    for i, (h, k) in enumerate(HKEYS):
        for yy in (t.year - 1, t.year):
            d = HOL[yy][h] + pd.Timedelta(days=7 * k)
            if t - pd.Timedelta(days=6) <= d <= t: return 52 + i
    return min((t.dayofyear - 1) // 7, 51)
NK = 52 + len(HKEYS)

def rtsa(r, win=7, back=15, minv=3):
    """real-time multiplicative seasonal adjustment of one weekly NSA series (index: Saturdays), holiday-keyed."""
    r = r.where(r > 0)
    y = np.log(r)
    m52 = y.rolling(52, min_periods=39).mean()
    trend = (m52.shift(-26) + m52.shift(-25)) / 2               # centred 2x52 moving average
    si = y - trend
    key = np.array([KEY[t] for t in y.index]); yr = y.index.year
    reg = np.array([min((t.dayofyear - 1) // 7, 51) for t in y.index])
    d0 = pd.DataFrame({'yr': yr, 'k': key, 'si': si.values, 't': y.index}).dropna()
    tab = d0.groupby(['yr', 'k'])['si'].mean().unstack().reindex(index=range(yr.min(), yr.max() + 1), columns=range(NK))
    tdt = d0.groupby(['yr', 'k'])['t'].max().unstack().reindex(index=tab.index, columns=tab.columns)
    T = tab.values; TT = tdt.values; years = list(tab.index); F = np.full_like(T, np.nan)
    for i, Y in enumerate(years):
        # usable at the 1 January refit of year Y: a centred value needs 26 weeks after it, so year Y-1 contributes
        # only the weeks up to 26 weeks before its last Saturday; earlier years contribute every week
        cut = pd.Timestamp(Y - 1, 12, 31) - pd.Timedelta(days=7 * 26 + 6)
        past = T[max(0, i - back):i].copy()
        if i >= 1:
            bad = ~(tdt.iloc[i - 1] <= cut).values          # NaT compares False: treated as not usable
            past[-1, bad] = np.nan
        for w in range(NK):
            v = past[:, w]; ok = ~np.isnan(v)
            if ok.sum() >= minv: F[i, w] = np.median(v[ok][-win:]); continue
            if w < 52:
                nb = [(w - 1) % 52, w, (w + 1) % 52]
                rows = np.where(~np.all(np.isnan(past[:, nb]), axis=1))[0][-win:]
                vv = past[rows][:, nb].ravel(); vv = vv[~np.isnan(vv)]
                if len(vv) >= minv: F[i, w] = np.median(vv)
        k = np.isfinite(F[i, :52])            # ordinary-week slots; those always taken by a holiday week stay empty
        if k.sum() >= 30:
            if not k.all():
                xs = np.arange(52); xp = np.concatenate([xs[k] - 52, xs[k], xs[k] + 52]); fp = np.tile(F[i, :52][k], 3)
                F[i, :52] = np.interp(xs, xp, fp)
            F[i, :52] = fourier_smooth(F[i, :52])
        else: F[i, :] = np.nan
    Fd = pd.DataFrame(F, index=years, columns=range(NK))
    f = np.array([Fd.at[a, b] if np.isfinite(Fd.at[a, b]) else Fd.at[a, c] for a, b, c in zip(yr, key, reg)])
    f = pd.Series(f, index=r.index)
    f = f - f.groupby(f.index.year).transform('mean')          # centre each calendar year's factors on zero
    return (r * np.exp(-f)).rename(r.name), f


KEY = {t: week_key(t) for t in pd.date_range('1945-01-06', '2059-12-27', freq='W-SAT')}
