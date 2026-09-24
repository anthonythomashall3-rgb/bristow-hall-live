"""The two-stage trough in the United States, with the two zero-lag American surveys.

Stage 1: the level route's D on the shipped American panel (bench.PANELS['United States'],
tool_check.py's skip set), each reading in hand one month after the month it describes
(payrolls arrive in the first week, production in the middle of the following month).
Stage 2: (a) the Philadelphia Fed's Manufacturing Business Outlook Survey, May 1968 on,
published on the third Thursday of the month it describes (lab/acq/ussurv/bos_history.csv,
fetched 2 September 2026; the unadjusted current diffusion indexes, adjusted here in real
time): general activity, new orders, shipments, and a breadth of the six activity questions
(general activity, new orders, shipments, unfilled orders, employment, workweek); (b) the
University of Michigan's Index of Consumer Sentiment, January 1978 on, preliminary reading
published in the middle of the month it describes (lab/acq/ussurv/umich_ics.csv).  The trough
is called in the first month the survey has stood `a` points above its minimum for `r`
months (breadth: share of the six rising over `k` months at or above q per cent), dated at
the minimum, published in the month of the call.  Scored against the NBER's eight troughs
since 1970 as twostage_ec scores: hits within six months, exact, within one and three,
published within the month (call month no later than the month after the trough), other
calls.  Beside it the tool's own clause on the same D, published one month after its
trigger.
"""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench
import ecbcs_speed as E, twostage_ec as T2
ACQ='/home/claude/lab/acq/ussurv'
NBER_T=[E.ts(x) for x in ['1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']]
SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
LAG=1
def us_panel():
    return [(nm,s) for nm,s in bench.channels('United States') if nm not in SKIP]
def d_available():
    D=B.composite_deviation(us_panel(),12,3,2).dropna(); D.index=D.index+pd.DateOffset(months=LAG); return D
def philly():
    d=pd.read_csv(f'{ACQ}/bos_history.csv'); d['t']=pd.to_datetime(d.DATE,format='%b-%y',errors='coerce')
    if d.t.isna().any(): d['t']=pd.to_datetime(d.DATE,errors='coerce')
    d=d.set_index('t')
    # two-digit years: 68-99 -> 1900s
    idx=[pd.Timestamp(y-100 if y>2030 else y,m,1) for y,m in zip(d.index.year,d.index.month)]
    d.index=pd.DatetimeIndex(idx)
    cols={'general activity':'gacdfna','new orders':'nocdfna','shipments':'shcdfna','unfilled orders':'uocdfna','employment':'necdfna','workweek':'awcdfna'}
    return {k:pd.to_numeric(d[v],errors='coerce').dropna().astype(float) for k,v in cols.items()}
def michigan():
    d=pd.read_csv(f'{ACQ}/umich_ics.csv',skiprows=1); d=d.rename(columns=lambda c:c.strip())
    d=d[pd.to_numeric(d['Index'],errors='coerce').notna()]
    t=pd.to_datetime(dict(year=d.Year.astype(int),month=d.Month.astype(int),day=1))
    return pd.Series(d['Index'].astype(float).values,index=t)
def breadth_calls(D,X,q,r,k,pre=3,min_cycle=12):
    ch=X.diff(k); Bd=(ch>0).sum(axis=1)/ch.notna().sum(axis=1)*100.0
    C=((X-X.rolling(120,min_periods=36).mean())/X.rolling(120,min_periods=36).std()).mean(axis=1)
    out=[]; state='quiet'; open_at=None; last=None
    for t in Bd.index:
        if t not in D.index or np.isnan(Bd[t]): continue
        d=float(D[t])
        if state=='quiet':
            if d>=2.0 and (last is None or T2.md(t,last)>=min_cycle): state='open'; open_at=t
        elif state=='open':
            seg=Bd[open_at:t]
            if len(seg)>=r and bool((seg.iloc[-r:]>=q).all()):
                cs=C[open_at-pd.DateOffset(months=pre):t].dropna(); m=cs.idxmin() if len(cs) else t
                out.append((t,m)); last=m; state='recover'
        else:
            if d<2.0: state='quiet'
    return out
if __name__=='__main__':
    bench.ABSTAIN=True
    D=d_available(); print('D in hand', D.index.min().strftime('%Y-%m'), '->', D.index.max().strftime('%Y-%m'))
    T=NBER_T
    tt=[(p,d) for p,d in B.real_time_trough_calls(us_panel(),publication_lag=LAG,fall_months=4,drop=0.5) if d>=pd.Timestamp('1969-01-01')]
    T2.line("the tool's own clause on D, published +1 month",tt,T)
    P=philly(); X=pd.DataFrame({k:E.sa_rt(v) for k,v in P.items()}).dropna(how='all')
    print('Philadelphia Fed', X.index.min().strftime('%Y-%m'), '->', X.index.max().strftime('%Y-%m'), list(X.columns))
    for which in ['general activity','new orders','shipments']:
        s=X[which].dropna(); rows=[]
        for a,r in itertools.product((5.,10.,15.,20.,30.),(1,2,3)):
            calls=T2.twostage(D,s,a,r); rows.append((T2.line(f'  Philly {which} a={a} r={r}',calls,T,show=False),a,r,calls))
        rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
        for res,a,r,calls in rows[:2]: T2.line(f'  Philly {which} a={a:.0f} r={r}',calls,T)
    rows=[]
    for k,q,r in itertools.product((1,2,3),(60.,70.,80.,90.,100.),(1,2)):
        calls=breadth_calls(D,X,q,r,k); rows.append((T2.line(f'  Philly breadth k={k} q={q:.0f} r={r}',calls,T,show=False),k,q,r,calls))
    rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
    for res,k,q,r,calls in rows[:3]: T2.line(f'  Philly breadth k={k} q={q:.0f} r={r}',calls,T)
    z=[x for x in rows if x[0][1]==0]
    if z: res,k,q,r,calls=z[0]; T2.line(f'  best with no other call k={k} q={q:.0f} r={r}',calls,T)
    M=michigan(); Ms=E.sa_rt(M).dropna(); T78=[t for t in T if t>=pd.Timestamp('1979-01-01')]
    print('Michigan', Ms.index.min().strftime('%Y-%m'), '->', Ms.index.max().strftime('%Y-%m'), '| troughs since 1979:', len(T78))
    rows=[]
    for a,r in itertools.product((3.,5.,8.,12.),(1,2,3)):
        calls=T2.twostage(D,Ms,a,r); rows.append((T2.line(f'  Michigan a={a} r={r}',calls,T78,show=False),a,r,calls))
    rows.sort(key=lambda x:(x[0][0],-x[0][1],x[0][5],x[0][4]),reverse=True)
    for res,a,r,calls in rows[:3]: T2.line(f'  Michigan a={a:.0f} r={r}',calls,T78)
