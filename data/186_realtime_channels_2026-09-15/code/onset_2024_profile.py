#!/usr/bin/env python3
"""What the April 2024 onset looked like in the high-frequency data, and what 2026 looks like beside it.

WHY THIS AND NOT ANOTHER SWEEP. 2024 is the only recession in this programme's chronology that happened
while weekly and daily measurement was dense enough to watch it arrive. It is therefore the only
template available for what the NEXT onset will look like in the series the rule will actually be
reading in real time -- ADP's weekly payrolls, Indeed's daily postings, the Chicago Fed's weekly retail
summary, weekly business applications. None of those existed in a usable form before 2010, and some
before 2020.

It is also the honest way to ask the question the tool is asked every day: is now like then? The answer
is given as numbers side by side rather than as a judgement. Each series is scored the same way: its
percentile rank, inside its own history to that date, over the three months ending at the comparison
point. 2024-04 is the peak. 2026-09 is now. A series that was extreme before 2024 and is ordinary now
says one thing; a series extreme in both says another.

Nothing here is a forecast. It is a description of two moments in the same units.
"""
import os, warnings, numpy as np, pandas as pd
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
ROOT = next((c for c in _C if os.path.isdir(os.path.join(c, '186_realtime_channels_2026-09-15'))), _C[0])
DATA = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data')
OUT = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'out')

def rd(sid):
    p = os.path.join(DATA, sid + '.csv')
    if not os.path.exists(p): return None
    q = pd.read_csv(p); c = list(q.columns)
    s = pd.Series(pd.to_numeric(q[c[1]], errors='coerce').values,
                  index=pd.to_datetime(q[c[0]], errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]

def steps(s, days):
    sp = float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))) if len(s) > 8 else 30.0
    return max(1, int(round(days / max(sp, 1))))

# Each entry: the series, and the direction that means DETERIORATION, so a high rank always means worse.
SPEC = [
 ('ADP weekly payrolls, 6-month change',        'ADPWNUSNERSA',  lambda s: -s.diff(steps(s, 182))),
 ('ADP weekly, small firms 1-19, 6-month',      'ADPWES1T19ENERSA', lambda s: -s.diff(steps(s, 182))),
 ('ADP weekly, construction, 6-month',          'ADPWINDCONNERSA', lambda s: -s.diff(steps(s, 182))),
 ('ADP weekly, information, 6-month',           'ADPWINDINFONERSA', lambda s: -s.diff(steps(s, 182))),
 ('Indeed total job postings, 6-month fall',    'INDEED_TOTAL_POSTINGS', lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('Indeed new job postings, 6-month fall',      'INDEED_NEW_POSTINGS', lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('initial claims, 4-week mean, year on year',  'IC4WSA',        lambda s: s.pct_change(steps(s, 365)) * 100),
 ('continued claims, year on year',             'CCSA',          lambda s: s.pct_change(steps(s, 365)) * 100),
 ('insured unemployment rate, 6-month change',  'IURSA',         lambda s: s.diff(steps(s, 182))),
 ('JOLTS openings, year-on-year fall',          'JTSJOL',        lambda s: -s.pct_change(steps(s, 365)) * 100),
 ('temporary help employment, y-o-y fall',      'TEMPHELPS',     lambda s: -s.pct_change(steps(s, 365)) * 100),
 ('factory hours, 6-month fall',                'AWHMAN',        lambda s: -s.diff(steps(s, 182))),
 ('Chicago Fed weekly retail, real, 6-month',   'CARTSR',        lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('business applications, weekly, y-o-y fall',  'BUSAPPWNSAUS',  lambda s: -s.pct_change(steps(s, 365)) * 100),
 ('high-propensity applications, y-o-y fall',   'HBUSAPPWNSAUS', lambda s: -s.pct_change(steps(s, 365)) * 100),
 ('housing permits, gap below 2-year high',     'PERMIT',        lambda s: (1 - s / s.rolling(steps(s, 730), min_periods=6).max()) * 100),
 ('housing starts, gap below 2-year high',      'HOUST',         lambda s: (1 - s / s.rolling(steps(s, 730), min_periods=6).max()) * 100),
 ('capital goods orders, 6-month fall',         'NEWORDER',      lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('inventory to sales ratio',                   'ISRATIO',       lambda s: s),
 ('capacity utilisation, 6-month fall',         'TCU',           lambda s: -s.diff(steps(s, 182))),
 ('industrial production, 6-month fall',        'INDPRO',        lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('retail sales, 6-month fall',                 'RSAFS',         lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('consumer sentiment, 6-month fall',           'UMCSENT',       lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('term spread inverted (10y minus 3m, neg)',   'T10Y3M',        lambda s: -s),
 ('high-yield spread',                          'BAMLH0A0HYM2',  lambda s: s),
 ('financial conditions index',                 'NFCI',          lambda s: s),
 ('mortgage rate, 6-month rise',                'MORTGAGE30US',  lambda s: s.diff(steps(s, 182))),
 ('volatility index',                           'VIXCLS',        lambda s: s),
 ('policy uncertainty, daily',                  'USEPUINDXD',    lambda s: s),
 ('supply chain pressure',                      'GSCPI',         lambda s: s),
 ('mortgage delinquency, single family',        'DRSFRMACBS',    lambda s: s),
 ('all-loan delinquency',                       'DRALACBS',      lambda s: s),
 ('truck tonnage, 6-month fall',                'TRUCKD11',      lambda s: -s.pct_change(steps(s, 182)) * 100),
 ('rail carloads, year-on-year fall',           'RAILFRTCARLOADSD11', lambda s: -s.pct_change(steps(s, 365)) * 100),
 ('oil price, year on year',                    'DCOILWTICO',    lambda s: s.pct_change(steps(s, 365)) * 100),
]
WHEN = [('2024-04 (the peak)', pd.Timestamp('2024-04-30')),
        ('2026-09 (now)',      pd.Timestamp('2026-09-15'))]

def rank(x, at):
    w = x[(x.index > at - pd.Timedelta(days=95)) & (x.index <= at)]
    if len(w) == 0: return np.nan, np.nan
    hist = x[x.index <= at]
    if len(hist) < 30: return np.nan, np.nan
    v = float(w.max())
    return v, float((hist <= v).mean() * 100)

rows = []
for label, sid, fn in SPEC:
    s = rd(sid)
    if s is None or len(s) < 40:
        rows.append(dict(object=label, series=sid, first=None, v_2024=np.nan, r_2024=np.nan,
                         v_2026=np.nan, r_2026=np.nan)); continue
    x = fn(s).replace([np.inf, -np.inf], np.nan).dropna()
    v24, r24 = rank(x, WHEN[0][1]); v26, r26 = rank(x, WHEN[1][1])
    rows.append(dict(object=label, series=sid, first=str(s.index.min().date()),
                     v_2024=v24, r_2024=r24, v_2026=v26, r_2026=r26))
D = pd.DataFrame(rows)
D['shift'] = D.r_2026 - D.r_2024
D.to_csv(os.path.join(OUT, 'onset_2024_profile.csv'), index=False)
pd.set_option('display.width', 200)
print('Percentile rank inside each object\'s own history, over the three months ending at each date.')
print('High rank = worse. A blank means the series does not reach that date, or has too little history.\n')
P = D[['object', 'first', 'r_2024', 'r_2026', 'shift']].copy()
P.columns = ['object', 'data from', 'rank at 2024-04', 'rank now', 'change']
print(P.round(0).to_string(index=False, na_rep='   .'))
a = D.dropna(subset=['r_2024', 'r_2026'])
print('\nobjects reaching both dates: %d' % len(a))
print('  at or above the 90th percentile before 2024-04: %d   %s'
      % (int((a.r_2024 >= 90).sum()), ', '.join(a[a.r_2024 >= 90].object.tolist())[:150]))
print('  at or above the 90th percentile now:            %d   %s'
      % (int((a.r_2026 >= 90).sum()), ', '.join(a[a.r_2026 >= 90].object.tolist())[:150]))
print('  median rank before 2024-04: %.0f     median rank now: %.0f' % (a.r_2024.median(), a.r_2026.median()))
