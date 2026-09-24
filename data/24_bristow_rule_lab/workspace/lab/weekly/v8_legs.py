"""The earlier program's two-tier claims detector (the 'Onset Detector' artifact of 20 August
2026: AMBER never late, RED never wrong), rebuilt on the rule's own national weekly file so its
scorecard can be checked rather than quoted, and read as a peak CALL object beside the rule's
weekly state-breadth caller (speed_final.py).

Legs, each recomputed every week from data that existed at the time:
  conjunct  min( log IC_nsa(t) - log IC_nsa(t-52 weeks), the same for CC ), four-week mean;
            RED fires at `th` log points (the artifact: 0.20; it reports the lowest recession-
            window maximum +0.3517 and the highest quiet-week value +0.1716)
  gap       the insured unemployment rate (Department's adjusted series, 1971 on), four-week
            mean less its trailing 52-week minimum, in percentage points; AMBER at 0.20
  gap_rt    the same on the rule's real-time-adjusted continued claims (log points x100),
            which needs no covered-employment denominator and no Department factor
An episode begins at the first week at or above the line that follows at least 26 weeks below
it (the artifact's hysteresis rule).  Publication: seven days after the week's end (the rule's
convention; the artifact used five).  Scored against the NBER peaks since 1969: an episode
whose first week lies within six months before the peak month and eighteen after is that
peak's call (the earliest such); lag = publication date less the last day of the peak month,
in days, and in months against the memo's 'within the month' standard (publication month <=
peak month + 1); every other episode is an other call.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
W='/home/claude/lab/weekly'
D=pd.read_csv(f'{W}/DOL_national_weekly_claims_1967.csv',parse_dates=['week_ended']).set_index('week_ended')
RT=pd.read_csv(f'{W}/DOL_national_weekly_claims_sa_rt.csv',parse_dates=['week_ended']).set_index('week_ended')
PEAKS=[pd.Timestamp(x) for x in ['1969-12-01','1973-11-01','1980-01-01','1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01']]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def conjunct(sm=4):
    ic=np.log(D.ic_nsa); cc=np.log(D.cc_nsa)
    c=pd.concat([ic-ic.shift(52),cc-cc.shift(52)],axis=1).min(axis=1)
    return c.rolling(sm).mean().dropna()
def gap(sm=4,L=52):
    g=D.iur_sa.rolling(sm).mean(); return (g-g.rolling(L,min_periods=L//2).min()).dropna()
def gap_rt(sm=4,L=52):
    g=(np.log(RT.cc_sa_rt)*100.0).rolling(sm).mean(); return (g-g.rolling(L,min_periods=L//2).min()).dropna()
def episodes(x, line, quiet=26):
    out=[]; below=0
    for t,v in x.items():
        if v>=line:
            if below>=quiet: out.append(t)
            below=0
        else: below+=1
    return out
def score(starts, pub=7, lo=-6, hi=18):
    got={}; used=set()
    for i,pk in enumerate(PEAKS):
        cands=[(j,s) for j,s in enumerate(starts) if j not in used and lo<=md(s,pk)<=hi]
        if cands:
            j,s=min(cands,key=lambda x:x[1]); got[i]=s; used.add(j)
    other=[s for j,s in enumerate(starts) if j not in used]
    rows=[]
    for i,pk in enumerate(PEAKS):
        if i in got:
            s=got[i]; p=s+pd.Timedelta(days=pub); end=(pk+pd.DateOffset(months=1))-pd.Timedelta(days=1)
            rows.append((pk.strftime('%Y-%m'),p.strftime('%Y-%m-%d'),(p-end).days,md(pd.Timestamp(p.year,p.month,1),pk)))
        else: rows.append((pk.strftime('%Y-%m'),None,None,None))
    return rows,other
def show(tag,x,line):
    st=[s for s in episodes(x,line) if s>=pd.Timestamp('1969-01-01')]
    rows,other=score(st)
    lags=[r[2] for r in rows if r[2] is not None]; ml=[r[3] for r in rows if r[3] is not None]
    print(f'{tag:34s} line {line:5.2f}: hits {len(lags)}/8 other {len(other):2d} inMonth {sum(l<=1 for l in ml)} median {np.median(lags) if lags else float("nan"):6.0f} d  worst {max(lags) if lags else "-"} best {min(lags) if lags else "-"}')
    print('      ',[(r[0],r[1],r[2]) for r in rows])
    if other: print('       other:',[s.strftime('%Y-%m-%d') for s in other])
if __name__=='__main__':
    c=conjunct(); q=c[c.index>=pd.Timestamp('1968-01-01')]
    inrec=pd.Series(False,index=q.index)
    NBER=[('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
    for a,b in NBER: inrec[(q.index>=pd.Timestamp(a+'-01'))&(q.index<=pd.Timestamp(b+'-01')+pd.offsets.MonthEnd(0))]=True
    # the artifact's separation claim, recomputed: lowest recession-window maximum, highest quiet week
    # (quiet = outside a recession and more than six months after a trough)
    quiet=q[~inrec].copy()
    for a,b in NBER:
        t=pd.Timestamp(b+'-01'); quiet=quiet[(quiet.index<t)|(quiet.index>t+pd.DateOffset(months=6))]
    rec_max=[q[(q.index>=pd.Timestamp(a+'-01'))&(q.index<=pd.Timestamp(b+'-01')+pd.offsets.MonthEnd(0))].max() for a,b in NBER]
    print(f'conjunct, {len(q)} weeks since 1968: lowest recession-window maximum {min(rec_max):+.4f} ({[round(v,3) for v in rec_max]}); highest quiet week {quiet.max():+.4f} at {quiet.idxmax():%Y-%m-%d}; quiet weeks >= 0.20: {(quiet>=0.20).sum()}')
    print('\n=== the conjunct as the peak call (RED leg)')
    for th in (0.15,0.20,0.25,0.30,0.35): show('conjunct, 4-week mean',c,th)
    print('\n=== the insured-unemployment-rate gap (AMBER), Department factors, 1971 on')
    g=gap()
    for th in (0.15,0.20,0.30,0.40): show('IUR gap, pp',g,th)
    print('\n=== the same gap on real-time-adjusted continued claims (log points)')
    gr=gap_rt()
    for th in (3.,5.,8.,10.,15.): show('CC gap, real-time factors',gr,th)
