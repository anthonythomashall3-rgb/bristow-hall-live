"""WARN BREADTH. One state's notices are lumpy - a single plant closure moves the count - so a state line is a bad
object. The share of states whose own notice flow is running above its own quiet line is not lumpy, and breadth is
an object this programme already uses on state payrolls and state claims.

Each state is read on its own history: the thirteen-week count of notices against the same thirteen weeks a year
earlier. A state is 'lit' in a week when that object is above the value it never reached outside a recession window
in that state's own record. Breadth is the share of the states reporting that week which are lit."""
import glob, os, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
D='/home/claude/warn/out'
DATECOL = {'or':'Received Date','al':'Initial Report Date','tx':'NOTICE_DATE','ok':'notice_date','vt':'notice_date',
           'wa':'Received Date','ak':'Notice Date','de':'notice_date','sd':'Date Received','ca':'notice_date',
           'ri':'Date Received','ut':'Date of Notice','ne':'Date','az':'notice_date','sc':'date','mt':'Date of Notice',
           'dc':'Notice Date','tn':'Received Date'}
QP = ['1990-07','2001-03','2007-12','2020-02','2024-04']; QT=['1991-03','2001-11','2009-06','2020-04','2024-08']
CALLED = {'1990-07':'1990-07-26','2001-03':'2001-03-29','2007-12':'2007-12-24','2020-02':'2020-03-12','2024-04':'2024-05-03'}
M=lambda s: pd.Timestamp(s+'-01')
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
    r=w.rolling(13).sum(); z=((r/r.shift(52)-1)*100).replace([np.inf,-np.inf],np.nan).dropna()
    if len(z)<120: continue
    quiet=pd.Series(True,index=z.index)
    for pk,tr in zip(QP,QT): quiet[(z.index>=M(pk)-pd.DateOffset(months=9))&(z.index<=M(tr)+pd.DateOffset(months=6))]=False
    q=z[quiet]
    if len(q)<80: continue
    ceil=float(q.max())
    lit[st]=(z>ceil).astype(float); rep[st]=pd.Series(1.0,index=z.index)
    print('%-4s line %8.1f  weeks %5d  from %s'%(st.upper(),ceil,len(z),z.index.min().date()))
L=pd.DataFrame(lit).fillna(0); R=pd.DataFrame(rep).fillna(0)
b=(L.sum(axis=1)/R.sum(axis=1).replace(0,np.nan)).dropna()
b=b[R.sum(axis=1)>=3]
print('\nbreadth: %d weeks, %s -> %s, states reporting %d..%d'%(len(b),b.index.min().date(),b.index.max().date(),int(R.sum(axis=1).min()),int(R.sum(axis=1).max())))
quiet=pd.Series(True,index=b.index)
for pk,tr in zip(QP,QT): quiet[(b.index>=M(pk)-pd.DateOffset(months=9))&(b.index<=M(tr)+pd.DateOffset(months=6))]=False
ceil=float(b[quiet].max())
print('quiet ceiling of breadth: %.3f  (max ever %.3f)'%(ceil,b.max()))
for pk,tr in zip(QP,QT):
    seg=b[(b.index>=M(pk)-pd.DateOffset(months=6))&(b.index<=M(tr))]
    if len(seg)<3: continue
    h=seg[seg>ceil]
    if len(h): print('  %s: breadth crosses %s  (%+d days vs the rule)  peak share %.2f'%(pk,h.index[0].date(),(h.index[0]-pd.Timestamp(CALLED[pk])).days,seg.max()))
    else: print('  %s: MISS  (peak share in window %.2f vs line %.3f)'%(pk,seg.max(),ceil))
