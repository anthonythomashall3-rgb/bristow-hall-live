# -*- coding: utf-8 -*-
"""CL1 families F1-F8 (PREREG-CL1-A section 3): each family's reading on every calendar day, from what was published by
that day. Deterministic; no AI. Run: python3 panel/families.py  ->  private/panel/families_daily.parquet (and .csv.gz)
plus panel/families_sources.json (every source path, its vintage class and the publication-day rule).

Sources (repository paths; the cloud inbox is the worktree of branch claude/exciting-gates-rsmjc3 of bristow-hall-live;
the private repository is bristow-hall-private-data and its branch claude/c13-538-2026-10-01):
  F1 initial claims  Choi-Munro weekly NSA counts 1946-07.. (digitized DOL reports; private) with this file's real-time
                     seasonal adjustment, known week end + 12 days, to the week ending 1975-07-26; from the week ending
                     1975-08-02 the Department's first-printed SA figure on its documented release day (collection 105
                     cache national_first_prints_1985_live.csv, built from collection 45 and the press archive).
  F2 insured rate    collection 59 real-time SA weekly rate 1949-01-01..1975-07-26 (known week end + 12 days); from
                     1975-08-02 the Department's first-printed SA rate on its release day (same file as F1).
  F3 unemployment    ALFRED UNRATE vintages from 1960-03-15 (this collection); before, the as-printed SA rate (Economic
                     Indicators, from the July 1957 issue; cloud inbox), and before that this file's real-time seasonal
                     adjustment of the as-printed NSA rate (cloud inbox, from May 1948). Publication day: the vintage
                     date (ALFRED) or the last day of the issue month (as printed; conservative).
  F4 payrolls        ALFRED PAYEMS vintages from 1955-05-06; before, the as-printed SA total (EI from Dec 1954), and
                     before that the real-time SA of the as-printed NSA total.
  F5 production      ALFRED INDPRO vintages from 1927-01-26 (complete).
  F6 equity          S&P 500 daily close from 1927-12-30 (private repository; never committed publicly), known next day.
  F7 credit          Moody's Baa - Aaa (FRED BAA, AAA monthly, known 7 days after month end; DBAA, DAAA daily from
                     1986-01-02, known next day) (private: rating-agency data).
  F8 money           10-year minus 3-month bill (FRED GS10 - TB3MS monthly from 1953-04, known 7 days after month end;
                     DGS10 - DTB3 daily from 1962-01-02, known next day). Never revised.
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, 'data')
PRIV = os.environ.get('BH_PRIVATE', '/home/user/bristow-hall-private-data/data')
CM = os.environ.get('BH_CHOI_MUNRO', '/home/user/c538/data/external/choi_munro/Claims_Data.xlsx')
INBOX = os.environ.get('BH_INBOX', '/home/user/inbox/data/_cloud_inbox_2026-09-29/labour_1948_1961/out/vintages')
sys.path.insert(0, os.path.join(HERE, 'harness'))
import rt  # noqa: E402

D0, D1 = pd.Timestamp('1946-01-01'), pd.Timestamp('2026-10-05')
CAL = pd.date_range(D0, D1, freq='D')
SOURCES = {}


def note(fam, **kw): SOURCES.setdefault(fam, []).append(kw)


# ---------------------------------------------------------------------------------------------------------- helpers
def woy(idx): return np.array([min(52, (t.dayofyear - 1) // 7 + 1) for t in idx])


def weekly_sa_realtime(nsa, min_years=3, max_years=7):
    """real-time multiplicative seasonal adjustment of a weekly NSA count: for year y, week-of-year factors are the
    median, over the prior min_years..max_years complete years, of log(NSA) minus that year's mean log level; applied
    unchanged through year y. No factor uses year y or later. Years without min_years of history stay unadjusted (NaN)."""
    x = np.log(nsa.astype(float).replace(0, np.nan)).dropna()
    yrs = sorted(set(x.index.year)); out = pd.Series(np.nan, index=x.index)
    dev = x - x.groupby(x.index.year).transform('mean'); w = pd.Series(woy(x.index), index=x.index)
    for y in yrs:
        hist = [z for z in yrs if y - max_years <= z < y and (x.index.year == z).sum() >= 50]
        if len(hist) < min_years: continue
        m = x.index.year.isin(hist)
        fac = dev[m].groupby(w[m]).median(); fac = fac - fac.mean()
        cur = x.index.year == y
        out[cur] = x[cur].values - w[cur].map(fac).fillna(0.0).values
    return np.exp(out).dropna()


def monthly_sa_realtime(nsa, min_years=3, max_years=7, log=True):
    """the same discipline for a monthly NSA series (rates are adjusted additively: log=False)"""
    x = (np.log(nsa) if log else nsa).dropna()
    yrs = sorted(set(x.index.year)); out = pd.Series(np.nan, index=x.index)
    dev = x - x.groupby(x.index.year).transform('mean')
    for y in yrs:
        hist = [z for z in yrs if y - max_years <= z < y and (x.index.year == z).sum() == 12]
        if len(hist) < min_years: continue
        m = x.index.year.isin(hist)
        fac = dev[m].groupby(x.index.month[m]).median(); fac = fac - fac.mean()
        cur = x.index.year == y
        out[cur] = x[cur].values - pd.Series(x.index.month[cur]).map(fac).fillna(0.0).values
    return (np.exp(out) if log else out).dropna()


def wide_vintages_to_long(path, prefix):
    w = pd.read_csv(path, parse_dates=['date'])
    L = w.melt(id_vars='date', var_name='col', value_name='value').dropna(subset=['value'])
    L['vintage'] = pd.to_datetime(L['col'].str.replace(prefix + '_', '', regex=False), format='%Y%m%d')
    return pd.DataFrame({'obs': L['date'], 'vintage': L['vintage'], 'value': L['value'].astype(float)})


def firstprint_vintages(series, pub):
    """a series of first prints (obs-indexed) with publication days (obs-indexed) -> vintage table"""
    return pd.DataFrame({'obs': series.index, 'vintage': pub.reindex(series.index).values, 'value': series.values}).dropna()


DARK = -9.99e99


def daily(s):
    """forward-fill a reading from its publication days onto the calendar; an explicit NaN reading (a dark spell, e.g. a
    basis break) stays dark until the next real reading"""
    s = s[~s.index.duplicated(keep='last')].sort_index().fillna(DARK)
    d = s.reindex(CAL.union(s.index)).ffill().reindex(CAL)
    return d.where(d != DARK)


def weekly_reading(series, pub, f):
    """series: weekly SA levels (week index); pub: publication day of each week. Reading on each publication day =
    f(the weeks published by then). First prints are not revised in this model (each week enters once)."""
    df = pd.DataFrame({'v': series, 'pub': pub.reindex(series.index)}).dropna().sort_index()
    out = {}
    vals = df['v']
    for k in range(len(df)):
        r = df['pub'].iloc[k]
        out[r] = f(vals.iloc[:k + 1])
    return pd.Series(out).sort_index()


# ---------------------------------------------------------------------------------------------------------- F1, F2
def f1_f2():
    cmx = pd.read_excel(CM).rename(columns=lambda c: c.strip())
    cmx['Date'] = pd.to_datetime(cmx['Date'])
    ic_nsa = cmx.set_index('Date')['Initial Claims'].astype(float)
    ic_sa_cm = weekly_sa_realtime(ic_nsa)
    note('F1', source=CM, what='Choi-Munro weekly NSA initial claims (digitized DOL reports pre-1967; FRED ICNSA after)',
         treatment='weekly_sa_realtime(min 3, max 7 prior years)', known='week end + 12 days', use='to week ending 1975-07-26',
         vintage_class='unrevised administrative count, lab real-time SA')
    fp = pd.read_csv(os.path.join(DATA, '105_bristow_hall_system_2026-09-08', 'workspace', 'cache',
                                  'national_first_prints_1985_live.csv'),
                     parse_dates=['release_date', 'ic_week_ended', 'iu_week_ended'])
    note('F1', source='data/105.../cache/national_first_prints_1985_live.csv', what='DOL first-printed SA initial claims',
         known='release_date', use='from week ending 1975-08-02', vintage_class='first print')
    cut = pd.Timestamp('1975-08-02')
    a = ic_sa_cm[ic_sa_cm.index < cut]
    b = fp.dropna(subset=['icsa']).set_index('ic_week_ended')['icsa'].astype(float)
    b = b[b.index >= cut]
    ic = pd.concat([a, b]).sort_index()
    pub = pd.concat([pd.Series(a.index + pd.Timedelta(days=12), index=a.index),
                     fp.dropna(subset=['icsa']).set_index('ic_week_ended')['release_date'][lambda s: s.index >= cut]]).sort_index()

    def rise(v):
        m4 = v.rolling(4).mean()
        if m4.notna().sum() < 53: return np.nan
        return float(np.log(m4.iloc[-1]) - np.log(m4.iloc[-53:-1].min()))
    F1 = weekly_reading(ic, pub, rise)
    IC4 = weekly_reading(ic, pub, lambda v: float(v.rolling(4).mean().iloc[-1]))

    iu59 = pd.read_csv(os.path.join(DATA, '59_dol_weekly_state_claims_1945-1983_2026-09',
                                    'national_iur_realtime_sa_first_prints_1948_1983.csv'), index_col=0, parse_dates=True).iloc[:, 0]
    iu59 = iu59[iu59.index < cut]
    iub = fp.dropna(subset=['iur_sa']).set_index('iu_week_ended')['iur_sa'].astype(float)
    iub = iub[iub.index >= cut - pd.Timedelta(days=7)]
    iub = iub[~iub.index.duplicated(keep='first')]
    iur = pd.concat([iu59, iub]).sort_index()
    iur = iur[~iur.index.duplicated(keep='first')]
    pub2 = pd.concat([pd.Series(iu59.index + pd.Timedelta(days=12), index=iu59.index),
                      fp.dropna(subset=['iur_sa']).drop_duplicates('iu_week_ended').set_index('iu_week_ended')['release_date'][lambda s: s.index >= cut - pd.Timedelta(days=7)]])
    pub2 = pub2[~pub2.index.duplicated(keep='first')].sort_index()
    note('F2', source='data/59.../national_iur_realtime_sa_first_prints_1948_1983.csv', known='week end + 12 days',
         use='to week ending 1975-07-26', vintage_class='lab real-time SA of printed counts (collection 59)')
    note('F2', source='data/105.../cache/national_first_prints_1985_live.csv', known='release_date',
         use='from week ending 1975-07-26', vintage_class='first print (gaps where no print was found)')

    def gap(v):
        m4 = v.rolling(4, min_periods=3).mean()
        if m4.notna().sum() < 53: return np.nan
        return float(m4.iloc[-1] - m4.iloc[-53:-1].min())
    F2 = weekly_reading(iur, pub2, gap)
    return F1, F2, IC4


# ---------------------------------------------------------------------------------------------------------- F3, F4, F5
def alfred_long(sid):
    return rt.load_vintages(os.path.join(HERE, 'panel', 'vintages', '%s_vintages.csv' % sid))


def stitched_monthly(sid, inbox_sa, inbox_sa_prefix, inbox_nsa, inbox_nsa_prefix, log):
    """vintage table: ALFRED where it exists; before its first vintage, the as-printed SA vintages; before the first SA
    print, the real-time SA of the as-printed NSA first prints (one vintage per month, at its print day)"""
    A = alfred_long(sid)
    a0 = A['vintage'].min()
    S = wide_vintages_to_long(os.path.join(INBOX, inbox_sa), inbox_sa_prefix)
    S = S[S['vintage'] < a0]
    s0 = S['vintage'].min()
    N = wide_vintages_to_long(os.path.join(INBOX, inbox_nsa), inbox_nsa_prefix)
    nfp = N.sort_values('vintage').groupby('obs').first()
    sa = monthly_sa_realtime(nfp['value'], log=log)
    Nn = firstprint_vintages(sa, nfp['vintage'])
    Nn = Nn[Nn['vintage'] < s0]
    note(sid, alfred_from=str(a0.date()), asprinted_sa_from=str(s0.date()), lab_sa_of_nsa_from=str(Nn['vintage'].min().date()) if len(Nn) else None)
    return Nn, S, A


def monthly_reading(Nn, S, A, f, s_obs_from=None, nn_until=None):
    """three eras, never mixed inside one reading (a definitional or seasonal-basis break between eras would otherwise
    enter a gap as a fake rise):
      lab era      real-time SA of the as-printed NSA first prints, vintages before nn_until (or before the first SA print)
      printed era  the as-printed SA vintages, using only months from s_obs_from on (dark until the reading has its window)
      ALFRED era   every ALFRED vintage
    Between the lab era's end and the printed era's first full reading the family is dark (NaN)."""
    out = {}
    s0 = S['vintage'].min()
    nn_end = min(pd.Timestamp(nn_until), s0) if nn_until else s0
    for r, s in rt.asof_iter(Nn[Nn['vintage'] < nn_end]):
        out[r] = f(s)
    out[nn_end] = np.nan
    Sx = S if s_obs_from is None else S[S['obs'] >= pd.Timestamp(s_obs_from)]
    for r, s in rt.asof_iter(Sx):
        out[r] = f(s)
    for r, g in A.groupby('vintage', sort=True):
        s = pd.Series(g['value'].values, index=pd.DatetimeIndex(g['obs'].values)).sort_index()
        out[r] = f(s)
    return pd.Series(out, dtype=float).sort_index()


def f3_f4_f5():
    Nn, S, A = stitched_monthly('UNRATE', 'UNRATE_asprinted_vintages.csv', 'UNRATE', 'UNRATENSA_asprinted_vintages.csv', 'UNRATENSA', log=False)
    # the CPS 'new definitions' begin with January 1957 (printed from the February 1957 issue); the printed SA rate of
    # July 1957 carries 1956 months on the old definitions. No reading mixes the two (inbox FINDING; checked against
    # ALFRED's 1960 vintage, which restates 1956 on the new definitions 0.2-0.7 point higher).
    F3 = monthly_reading(Nn, S, A, rt.sahm_gap, s_obs_from='1957-01-01', nn_until='1957-02-28')
    note('F3', basis_break='CPS new definitions from 1957-01; lab-SA era ends 1957-02-28; printed-SA era uses months from 1957-01 only (dark until 15 months exist)')
    Nn, S, A = stitched_monthly('PAYEMS', 'PAYEMS_asprinted_vintages.csv', 'PAYEMS', 'PAYNSA_asprinted_vintages.csv', 'PAYNSA', log=True)
    F4 = monthly_reading(Nn, S, A, lambda s: rt.fall_from_high(rt.monthly(s), 12))
    note('F4', basis_rule='lab-SA era until the first printed SA total; printed-SA era on printed SA months only')
    A = alfred_long('INDPRO')
    F5 = pd.Series({r: rt.fall_from_high(pd.Series(g['value'].values, index=pd.DatetimeIndex(g['obs'].values)).sort_index(), 12)
                    for r, g in A.groupby('vintage', sort=True)}, dtype=float).sort_index()
    note('F5', source='panel/vintages/INDPRO_vintages.csv (ALFRED)', known='vintage date', vintage_class='full vintage history')
    return F3, F4, F5


# ---------------------------------------------------------------------------------------------------------- F6, F7, F8
def fred_csv(path):
    d = pd.read_csv(path, na_values=['.', ''])
    return pd.Series(pd.to_numeric(d.iloc[:, 1], errors='coerce').values, index=pd.to_datetime(d.iloc[:, 0])).dropna()


def f6_f7_f8():
    sp = pd.read_csv(os.path.join(PRIV, '24_bristow_rule_lab', 'workspace', 'lab', 'speed2', 'data', 'sp500_daily_yahoo.csv'),
                     index_col=0, parse_dates=True).iloc[:, 0].dropna()
    dd = np.log(sp.rolling(250, min_periods=120).max()) - np.log(sp)
    F6 = pd.Series(dd.values, index=dd.index + pd.Timedelta(days=1))
    note('F6', source='private: 24_bristow_rule_lab/workspace/lab/speed2/data/sp500_daily_yahoo.csv', known='next day',
         vintage_class='market close, never revised')
    pr = os.path.join(HERE, 'private', 'fred'); rw = os.path.join(HERE, 'raw', 'fred')
    baa, aaa = fred_csv(os.path.join(pr, 'BAA.csv')), fred_csv(os.path.join(pr, 'AAA.csv'))
    sm = (baa - aaa).dropna()
    sm = pd.Series(sm.values, index=sm.index + pd.offsets.MonthEnd(0) + pd.Timedelta(days=7))
    sdly = (fred_csv(os.path.join(pr, 'DBAA.csv')) - fred_csv(os.path.join(pr, 'DAAA.csv'))).dropna()
    sdly = pd.Series(sdly.values, index=sdly.index + pd.Timedelta(days=1))
    spread = pd.concat([sm[sm.index < pd.Timestamp('1986-01-03')], sdly]).sort_index()
    spread = spread[~spread.index.duplicated(keep='last')]
    sd = daily(spread)
    F7 = sd - sd.rolling(365, min_periods=300).min()
    note('F7', source='private/fred BAA, AAA (monthly, month end + 7 days to 1985) and DBAA, DAAA (daily from 1986, next day)',
         vintage_class='never revised')
    g10m, tbm = fred_csv(os.path.join(rw, 'GS10.csv')), fred_csv(os.path.join(rw, 'TB3MS.csv'))
    cm = (g10m - tbm).dropna()
    cm = pd.Series(cm.values, index=cm.index + pd.offsets.MonthEnd(0) + pd.Timedelta(days=7))
    cdl = (fred_csv(os.path.join(rw, 'DGS10.csv')) - fred_csv(os.path.join(rw, 'DTB3.csv'))).dropna()
    cdl = pd.Series(cdl.values, index=cdl.index + pd.Timedelta(days=1))
    curve = pd.concat([cm[cm.index < pd.Timestamp('1962-01-03')], cdl]).sort_index()
    curve = curve[~curve.index.duplicated(keep='last')]
    cd = daily(curve)
    F8 = (-cd.rolling(365, min_periods=300).min()).clip(lower=0)
    note('F8', source='raw/fred GS10 - TB3MS (monthly, month end + 7 days, to 1961) and DGS10 - DTB3 (daily from 1962, next day)',
         vintage_class='never revised')
    return daily(F6), F7, F8


def build():
    F1, F2, IC4 = f1_f2()
    F3, F4, F5 = f3_f4_f5()
    F6, F7, F8 = f6_f7_f8()
    P = pd.DataFrame({'F1': daily(F1), 'F2': daily(F2), 'F3': daily(F3), 'F4': daily(F4), 'F5': daily(F5),
                      'F6': F6, 'F7': F7.reindex(CAL), 'F8': F8.reindex(CAL), 'IC4': daily(IC4)})
    os.makedirs(os.path.join(HERE, 'private', 'panel'), exist_ok=True)
    P.to_parquet(os.path.join(HERE, 'private', 'panel', 'families_daily.parquet'))
    json.dump(SOURCES, open(os.path.join(HERE, 'panel', 'families_sources.json'), 'w'), indent=1, default=str)
    for c in P.columns:
        s = P[c].dropna()
        print('%s: %s .. %s, %d days; max %.3f on %s' % (c, s.index.min().date(), s.index.max().date(), len(s), s.max(), s.idxmax().date()))
    return P


if __name__ == '__main__':
    build()
