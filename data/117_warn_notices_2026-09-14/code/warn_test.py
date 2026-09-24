"""THE WARN NOTICES AGAINST THE RULE'S OWN CALL DATES.

A WARN notice is filed with the state SIXTY DAYS BEFORE the layoff takes effect, because the statute says it must
be.  It is the only labour datum in the country that leads the event by law rather than by correlation.

Oregon's file begins 28 November 1988 - the WARN Act took effect in February 1989, so Oregon is essentially the
complete record - and covers five recessions.  Texas begins January 1999 and Alabama July 1998, both covering four.

The datum is the notice date.  A notice is treated as public seven days later, which is conservative: most states
post their list weekly.  The object is the count of notices and the workers noticed over a trailing thirteen weeks
against the same thirteen weeks a year earlier, which cancels the season and the state's size.  The line is the
value the object never reached outside a recession window in that state's own history."""
import glob, re, os, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

D = '/home/claude/warn/out'
DATECOL = {'or':'Received Date','al':'Initial Report Date','tx':'NOTICE_DATE','ok':'notice_date','vt':'notice_date',
           'wa':'Received Date','ak':'Notice Date','de':'notice_date','sd':'Date Received','ca':'notice_date',
           'ri':'Date Received','ut':'Date of Notice','ne':'Date','az':'notice_date','sc':'date','mt':'Date of Notice',
           'dc':'Notice Date','tn':'Received Date'}
NCOL = {'or':'Laid Off','al':'Planned # of Affected Employees','tx':'TOTAL_LAYOFF_NUMBER','wa':'# of Workers',
        'ca':'num_employees'}
PEAKS  = ['1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS= ['1991-03','2001-11','2009-06','2020-04','2024-08']
QP = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
QT = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08']
CALLED = {'1990-07':'1990-07-26','2001-03':'2001-03-29','2007-12':'2007-12-24','2020-02':'2020-03-12','2024-04':'2024-05-03'}
M = lambda s: pd.Timestamp(s+'-01')

def weekly(st):
    f = f'{D}/{st}.csv'
    if not os.path.exists(f): return None
    d = pd.read_csv(f, dtype=str, on_bad_lines='skip')
    c = DATECOL.get(st)
    if c not in d.columns: return None
    dt = pd.to_datetime(d[c], errors='coerce', utc=True).dt.tz_localize(None)
    ok = dt.notna() & (dt > pd.Timestamp('1988-01-01')) & (dt < pd.Timestamp('2026-09-14'))
    d = d[ok]; dt = dt[ok]
    n = pd.to_numeric(d[NCOL[st]].str.replace(r'[^0-9.]', '', regex=True), errors='coerce').fillna(0) if st in NCOL and NCOL[st] in d.columns else pd.Series(1.0, index=d.index)
    pub = dt + pd.Timedelta(days=7)                    # treated as public a week after it is filed
    w = pd.DataFrame({'pub': pub, 'n': 1.0, 'w': n}).set_index('pub').resample('W-FRI').sum()
    return w

def score(name, s, lab):
    o = {}
    r13 = s.rolling(13).sum()
    o['yoy13w'] = (r13 / r13.shift(52) - 1) * 100
    r26 = s.rolling(26).sum()
    o['yoy26w'] = (r26 / r26.shift(52) - 1) * 100
    o['lvl13w'] = r13
    for on, z0 in o.items():
        z = z0.replace([np.inf, -np.inf], np.nan).dropna()
        if len(z) < 200: continue
        quiet = pd.Series(True, index=z.index)
        for pk, tr in zip(QP, QT):
            quiet[(z.index >= M(pk)-pd.DateOffset(months=9)) & (z.index <= M(tr)+pd.DateOffset(months=6))] = False
        q = z[quiet]
        if len(q) < 150: continue
        ceil = float(q.max()); sd = float(z.std())
        cov = []; miss = []
        for pk, tr in zip(PEAKS, TROUGHS):
            if z.index.min() > M(pk)-pd.DateOffset(months=6): continue
            seg = z[(z.index >= M(pk)-pd.DateOffset(months=6)) & (z.index <= M(tr))]
            if len(seg) < 3: continue
            h = seg[seg > ceil]
            if len(h): cov.append((pk, h.index[0].date(), (h.index[0]-pd.Timestamp(CALLED[pk])).days))
            else: miss.append(pk)
        tot = len(cov)+len(miss)
        if tot >= 2:
            flag = 'ALL' if not miss else f'miss {",".join(miss)}'
            print(f'  {name:10s} {lab:4s} {on:7s} line {ceil:9.1f}  {len(cov)}/{tot}  {flag}')
            for pk, d_, l in cov: print(f'        {pk}: crosses {d_}  ({l:+d} days vs the rule)')

for st in ['or','tx','al','wa','ca','ok','ne','az','ut','sc','vt','de','sd','ri','ak']:
    w = weekly(st)
    if w is None or len(w) < 200: continue
    print(f'\n== {st.upper()}  {w.index.min().date()} -> {w.index.max().date()}  {int(w.n.sum())} notices')
    score(st.upper(), w['n'], 'cnt')
    if st in NCOL: score(st.upper(), w['w'], 'wrk')
