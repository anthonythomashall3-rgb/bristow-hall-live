"""WARN BREADTH, DONE PROPERLY.

A year-on-year ratio on a small state's notice count explodes - a count going from one to six is plus five hundred
per cent - so the ratio is the wrong object.  The right one is scale-free: where does this week's thirteen-week
count sit in that state's own distribution?  A state is LIT when its thirteen-week count is above the highest value
it reached in any QUIET week of its own record.  Breadth is the share of reporting states that are lit."""
import os, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
D='/home/claude/warn/out'
DATECOL = {'or':'Received Date','al':'Initial Report Date','tx':'NOTICE_DATE','ok':'notice_date','vt':'notice_date',
           'wa':'Received Date','ak':'Notice Date','de':'notice_date','sd':'Date Received','ca':'notice_date',
           'ri':'Date Received','ut':'Date of Notice','ne':'Date','az':'notice_date','sc':'date','mt':'Date of Notice',
           'dc':'Notice Date','tn':'Received Date'}
QP=['1990-07','2001-03','2007-12','2020-02','2024-04']; QT=['1991-03','2001-11','2009-06','2020-04','2024-08']
CALLED={'1990-07':'1990-07-26','2001-03':'2001-03-29','2007-12':'2007-12-24','2020-02':'2020-03-12','2024-04':'2024-05-03'}
M=lambda s: pd.Timestamp(s+'-01')
def qmask(idx):
    q=pd.Series(True,index=idx)
    for pk,tr in zip(QP,QT): q[(idx>=M(pk)-pd.DateOffset(months=9))&(idx<=M(tr)+pd.DateOffset(months=6))]=False
    return q
lit={}; rep={}
for st,c in DATECOL.items():
    f=f'{D}/{st}.csv'
    if not os.path.exists(f): continue
    d=pd.read_csv(f,dtype=str,on_bad_lines='skip')
    if c not in d.columns: continue
    dt=pd.to_datetime(d[c],errors='coerce',utc=True).dt.tz_localize(None)
    dt=dt[dt.notna()&(dt>pd.Timestamp('1988-01-01'))&(dt<pd.Timestamp('2026-09-14'))]
    if len(dt)<80: continue
    w=pd.Series(1.0,index=dt+pd.Timedelta(days=7)).resample('W-FRI').sum()
    z=w.rolling(13).sum().dropna()
    z=z[z.index>=z.index.min()+pd.Timedelta(weeks=52)]
    if len(z)<150: continue
    q=z[qmask(z.index)]
    if len(q)<80: continue
    ceil=float(q.max())
    lit[st]=(z>ceil).astype(float); rep[st]=pd.Series(1.0,index=z.index)
    print('%-4s 13-week quiet high %5.0f notices | weeks %5d from %s | lit weeks %3d'%(st.upper(),ceil,len(z),z.index.min().date(),int((z>ceil).sum())))
L=pd.DataFrame(lit).fillna(0); R=pd.DataFrame(rep).fillna(0)
tot=R.sum(axis=1)
b=(L.sum(axis=1)/tot.replace(0,np.nan)).dropna(); b=b[tot>=4]
print('\nbreadth: %d weeks %s -> %s | states reporting %d..%d'%(len(b),b.index.min().date(),b.index.max().date(),int(tot[b.index].min()),int(tot[b.index].max())))
q=b[qmask(b.index)]; ceil=float(q.max())
print('quiet ceiling %.3f | max ever %.3f | quiet weeks %d'%(ceil,b.max(),len(q)))
for pk,tr in zip(QP,QT):
    seg=b[(b.index>=M(pk)-pd.DateOffset(months=6))&(b.index<=M(tr))]
    if len(seg)<3: continue
    h=seg[seg>ceil]
    if len(h): print('  %s: crosses %s (%+d days vs rule) peak %.2f'%(pk,h.index[0].date(),(h.index[0]-pd.Timestamp(CALLED[pk])).days,seg.max()))
    else: print('  %s: MISS (peak %.2f vs line %.3f)'%(pk,seg.max(),ceil))
print('\nthe quiet weeks at or near the line (the false-alarm risk):')
print(q.sort_values(ascending=False).head(8).to_string())
