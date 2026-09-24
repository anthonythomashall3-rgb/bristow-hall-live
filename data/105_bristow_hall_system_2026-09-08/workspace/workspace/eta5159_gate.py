"""Stage 5 of the second-condition hunt: the Department's own state file as a
confirming object, priced in the route's own harness rather than on a screen.

The object: the share of states whose State UI initial claims stand a fifth of
a log point or more above their level a year earlier.  Every fold of a
leave-one-recession-out over the seven recessions since 1971 chooses the same
line and the same share, and the object produces exactly seven episodes in the
file's six hundred and fifty-five months -- the seven recessions, with no
quiet-window exclusion applied at all.

Two things it is not.  It is not a dating leg: it opens nine months before the
1980 and 1990 peaks, which would be a nine-month dating error.  And it is not
a first-print object: the Department publishes one current-vintage file, so
this prices what the object WOULD buy if the file had been available in real
time, which before the web era it was not.
"""
exec(open('legU.py').read().split('U=leg_U()')[0])
U=leg_U(); PLU=dict(PL); PLU['U']=U
import numpy as np, csv, pandas as pd, os
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
def first_prints(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    dates=[pd.Timestamp(r[0]) for r in rows[1:]]; out={}
    for j in range(1,len(h)):
        col=[rows[1+i][j] for i in range(len(dates))]
        idx=[i for i,v in enumerate(col) if v not in ('','.')]
        if not idx: continue
        m=dates[idx[-1]]
        if m not in out: out[m]=float(col[idx[-1]])
    return pd.Series(out).sort_index()
P3=-(first_prints("PAYEMS")/first_prints("PAYEMS").shift(3)-1)*100

E=os.path.expanduser("~/mnt/")+"Onset Detector Data/37_dol_eta5159_2026-09/panel/panel_5159_monthly.csv"
P=pd.read_csv(E,parse_dates=['month'])
def breadth(field,line):
    w=P.pivot_table(index='month',columns='st',values=field,aggfunc='sum').where(lambda d:d>0)
    ly=np.log(w); y=ly-ly.shift(12); cov=y.notna().sum(axis=1)
    return (y.ge(line).sum(axis=1)/cov.where(cov>=30)).dropna()*100   # per cent, so line is in per cent
B5=breadth('ic_total',0.20)
BN=breadth('ic_new',0.15)

PEAKS=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-07']
TROUGHS=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08']
M=lambda s: pd.Timestamp(s+'-01')
def exposure(o,line):
    o=o.dropna(); idx=o.index
    q=pd.Series(True,index=idx)
    for p,t in zip(PEAKS,TROUGHS):
        q[(idx>=M(p)-pd.DateOffset(months=9))&(idx<=M(t)+pd.DateOffset(months=18))]=False
    hit=(o>=line)
    fwd=hit[::-1].rolling(1,min_periods=1).max()[::-1].astype(bool)
    back=hit.rolling(7,min_periods=1).max().astype(bool)
    return hit[q].mean()*100,(fwd|back)[q].mean()*100,int(q.sum())

for nm,o,l in [('5159 total claims breadth, 0.20 / 40%',B5,40.0),
               ('5159 new claims breadth, 0.15 / 60%',BN,60.0)]:
    a,b,n=exposure(o,l)
    print(f'{nm:44}  at line {a:5.2f}%   IN WINDOW {b:5.2f}%   quiet months {n}')

PK5=('A','B','C','M','U'); TR3=('K','J','H')
def rep(nm, second):
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        r=score(B.american_chronology({k:PLU[k] for k in PK5},{k:TLG[k] for k in TR3},sahm=g,second=second),'x','1948-06-01')
    lp,ep=r['lags_p'],r['errs_p']
    print(f"{nm}\n   peaks {len(lp)}/12  other {r['other']}  | median {np.median(lp):.0f} d  worst {max(lp)}  "
          f"in-month {sum(1 for l in lp if l<=0)}  <=31d {sum(1 for l in lp if l<=31)}  | dates exact {sum(1 for e in ep if e==0)} mae {np.mean(np.abs(ep)):.2f}\n   lags {lp}")
V=[dict(name='vacancy(2,6)',gap=vr,line=0.36,pub_day=30)]
BASE=V+[dict(name='payroll3',gap=P3,line=0.3,pub_day=5)]
print()
rep("SHIPPED  Sahm 0.50 OR vacancy 0.36 OR payrolls 0.3%", BASE)
for pub in (25,30,45):
    rep(f"+ 5159 total-claims breadth 40% (pub day {pub})", BASE+[dict(name='eta5159',gap=B5,line=40.0,pub_day=pub)])
rep("+ 5159 new-claims breadth 60% (pub day 30)", BASE+[dict(name='eta5159new',gap=BN,line=60.0,pub_day=30)])
