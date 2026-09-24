"""The simulation Anthony's amendment asks for (3 September 2026, night: "we don't need the data to reach all the
way back to 1948, we just need what is best … test it on multiple chronologies and simulations and other ways"):
the WINDOW EXPOSURE of a second-condition object - the share of quiet observations on which a claims call made
that day would be confirmed by the object, because the object stands at its line somewhere in the route's own
window, six months before the call to thirty days after it.  Quiet = outside [peak - 9 months, trough + 18 months]
of the thirteen (the eighteen months remove the post-trough tails, where every labor object is still elevated
and the machine is closed anyway).  Read for the route's two objects and for the two partials the daily and
weekly sweep surfaced.  Output window_exposure.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude/lab/weekly')
import pandas as pd, numpy as np
import american_chronology as AC
PEAKS = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
TROUGHS = ['1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04', '2024-08']
M = lambda s: pd.Timestamp(s + '-01')
log = open('/home/claude/lab/data/window_exposure.log', 'w')
def P(*a): print(*a); print(*a, file=log)

def quiet(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS, TROUGHS): q[(idx >= M(p) - pd.DateOffset(months=9)) & (idx <= M(t) + pd.DateOffset(months=post))] = False
    return q

def exposure(o, line, label, per_month, since=None):
    """per_month: observations per month (1 monthly, 4 weekly, 21 daily); the forward window is 30 days, the backward six months"""
    o = o.dropna()
    if since: o = o[since:]
    q = quiet(o.index); hit = (o >= line)
    fwd = hit[::-1].rolling(max(1, per_month), min_periods=1).max()[::-1].astype(bool)
    back = hit.rolling(6 * per_month + 1, min_periods=1).max().astype(bool)
    at = hit[q].mean() * 100; win = (fwd | back)[q].mean() * 100
    P(f'  {label:58s} at the line {at:5.1f}%   confirmed inside the window {win:5.1f}%   ({int(q.sum())} quiet observations from {o.index[0]:%Y-%m})')
    return win

P('WINDOW EXPOSURE - the share of quiet observations (outside [peak-9m, trough+18m]) on which a claims call would be confirmed by the object')
P("the route's own objects:")
exposure(AC.vacancy_gap(2, 6), 0.36, 'vacancy rate, fast form (2,6) >= 0.36 (monthly, 1949-)', 1, '1949')
exposure(AC.vacancy_gap_rt(2, 6), 0.36, 'the same on first prints where they exist', 1, '1949')
exposure(AC.sahm_rt(), 0.5, "Sahm's gap >= 0.5 on the rate as first published (1960-)", 1, '1960')
P('the daily and weekly partials of the sweep (readable at 1967 only):')
s = pd.read_csv('/home/claude/lab/data/fred_daily/DGS5.csv', index_col=0, parse_dates=True)['value'].dropna()
exposure(-(s - s.shift(21)), 0.65, '5-year Treasury yield, 21-day fall >= 0.65 points (daily, 1962-)', 21)
exposure(-(np.log(s) - np.log(s.shift(21))) * 100, 11.7, 'the same in relative form, >= 11.7% (the 1967 window maximum)', 21)
w = pd.read_csv('/home/claude/lab/data/fred_weekly/WBAA.csv', index_col=0, parse_dates=True)['value'].dropna()
exposure(w - w.shift(4), 0.255, "Moody's Baa yield, 4-week rise >= 0.255 points (weekly, 1962-)", 4)
sp = pd.read_csv('/home/claude/lab/data/other_daily/sp500_daily_yahoo.csv', index_col=0, parse_dates=True)['close'].dropna()
exposure(-(sp / sp.rolling(252, min_periods=200).max() - 1) * 100, 8.0, 'S&P 500 drawdown from the trailing-year high >= 8% (daily, 1928-)', 21, '1949')
log.close()
