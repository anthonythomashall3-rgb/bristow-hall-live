"""Rule 17's speed question outside the United States, first try: Germany's registered
unemployment as the American claims file's analogue.

The Bundesagentur publishes the count of registered unemployed for month T at the end of
month T — no publication lag at all — and the Bundesbank carries the West German series
monthly from December 1949 (a rate, one decimal; BUBA/BBDL1 via DBnomics, lab/nat/deu) and
the all-German count from September 1990.  This script (1) adjusts each series in real
time — month-of-year median factors on a moving seven-year window of years strictly before
the year being adjusted, no look-ahead — and (2) runs the tool's own claims detector
(level_trough_calls, on the log level for troughs and on its negative for peaks) over a grid,
scoring every call against the Council of Economic Experts' dates (West Germany before 1991,
Germany after) and listing every other call.  'Within the month' = the call's data month is
no later than the month after the turning-point month (the figure is public by the end of
that month).
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
NAT='/home/claude/lab/nat/deu'
def load(f): return pd.read_csv(f'{NAT}/DEU_{f}.csv',index_col=0,parse_dates=True).iloc[:,0].dropna().astype(float)
def sa_rt(s, win=7):
    """real-time month-of-year adjustment of log(s): for each year, factors are medians of the
    detrended log series over the previous `win` years, the detrending (13-month centred mean)
    computed on data through December of the previous year only."""
    x=np.log(s)*100.0; out=pd.Series(np.nan,index=x.index)
    for yr in sorted(set(x.index.year)):
        past=x[x.index.year<yr]
        if len(past)<24: out[x.index.year==yr]=x[x.index.year==yr]; continue
        tr=past.rolling(13,center=True,min_periods=7).mean().bfill().ffill(); r=past-tr
        hist=r[r.index.year>=yr-win]
        f=hist.groupby(hist.index.month).median(); f=f-f.mean()
        for t in x.index[x.index.year==yr]: out[t]=x[t]-float(f.get(t.month,0.0))
    return out/100.0   # log level, adjusted
COUNCIL=[('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]
ECRI=[('1966-03','1967-05'),('1973-08','1975-07'),('1980-01','1982-10'),('1991-01','1994-04'),('2001-01','2003-08'),('2008-04','2009-01'),('2019-05','2020-04')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def ts(s): return pd.Timestamp(s+'-01')
def score(calls, refs, tol=6):
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,(pub,dt) in enumerate(calls):
            if j in used: continue
            e=md(dt,ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=(calls[best[0]][0],calls[best[0]][1],best[1]); used.add(best[0])
    other=[c for j,c in enumerate(calls) if j not in used]
    return got,other
def run(series_log, kind, refs, **kw):
    """kind 'T': troughs from the log level; 'P': peaks from its negative"""
    x=series_log if kind=='T' else -series_log
    calls=B.level_trough_calls(x, publication_lag=0, **kw)
    return score(calls, refs)
if __name__=='__main__':
    west=sa_rt(load('west_unemployment_rate_nsa')); ger=sa_rt(load('unemployed_nsa'))
    # one spliced log series: West to 1990-12, Germany from 1991-01 (level shift removed at the splice)
    j=pd.Timestamp('1991-01-01'); shift=float(ger[j]-west[j])
    spl=pd.concat([west[:'1990-12'], ger['1991-01':]-shift])
    print('series: West Germany rate 1949-12.., Germany count 1990-09.. spliced 1991-01; real-time adjusted, log level')
    for label,refs in (('the Council',COUNCIL),('ECRI',ECRI)):
        P=[ts(p) for p,t in refs]; T=[ts(t) for p,t in refs]
        for kind,R in (('T',T),('P',P)):
            print(f'\n=== {kind} against {label}: grid (smooth, lookback, run, drop, arm_gap); hits / exact / within 1 / within the month / other calls')
            rows=[]
            for sm,lb,run_,drop,gap in itertools.product((1,2,3),(24,36),(1,2,3),(1.0,2.0,4.0),(10.0,20.0,30.0,50.0)):
                got,other=run(spl,kind,R,smooth=sm,lookback=lb,run=run_,drop=drop,arm_gap=gap,rearm_gap=gap/4,min_phase=3)
                e=[v[2] for v in got.values()]; lag=[md(v[0],R[i]) for i,v in got.items()]
                rows.append((len(got),-len(other),sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(l<=1 for l in lag),(sm,lb,run_,drop,gap),got,other))
            rows.sort(key=lambda r:(r[0],r[1],r[4],r[2]),reverse=True)
            for r in rows[:6]:
                print(f'  hits {r[0]}/{len(R)} other {-r[1]} exact {r[2]} w1 {r[3]} inMonth {r[4]} | {r[5]}')
                print('     ', {R[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
                if r[7]: print('      other:',[(p.strftime('%Y-%m'),d.strftime('%Y-%m')) for p,d in r[7]])
            # zero-false-alarm best
            z=[r for r in rows if r[1]==0]
            if z:
                z.sort(key=lambda r:(r[0],r[4],r[2]),reverse=True); r=z[0]
                print(f'  best with no other call: hits {r[0]}/{len(R)} exact {r[2]} w1 {r[3]} inMonth {r[4]} | {r[5]}')
                print('     ', {R[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m')) for i,v in r[6].items()})
