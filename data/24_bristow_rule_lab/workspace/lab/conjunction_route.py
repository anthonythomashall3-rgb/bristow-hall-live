"""Route B on the record (3 September 2026, night): union_calls on the claims objects (legs A, B, C, M), then
conjunction_calls with the unemployment rate at Sahm's published line (0.5).  Lags in days from the end of the
committee's peak month; dates against the committee's month.  Output conjunction_route.log."""
import sys,warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B, union_peaks as U, legs_1948 as L48
u=pd.read_csv('/home/claude/archive/data/fred/UNRATE.csv'); u.columns=['date','v']; u['date']=pd.to_datetime(u['date']); u=u.set_index('date')['v'].astype(float)
eps=[e for e in B.union_calls({'A':U.leg_A(),'B':U.leg_B(0.20),'C':U.leg_C(),'M':L48.leg_M(0.20)},date_order=('A','C')) if e['published']>=pd.Timestamp('1948-06-01')]
calls=B.conjunction_calls(eps,u)
NBER=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
def near(d):
    for m in NBER:
        if abs((d-pd.Timestamp(m+'-01')).days)<=200: return m
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
print('published     committee   lag(d)  in-month   date     err')
L=[];E=[]
for c in calls:
    n=near(c['claims_call'])
    if n: e=pd.Timestamp(n+'-01')+pd.offsets.MonthEnd(0); lag=(c['published']-e).days; err=md(c['date'],pd.Timestamp(n+'-01')); L.append(lag); E.append(err)
    print(f"{c['published']:%Y-%m-%d}    {n or 'none':8s}   {lag if n else '':>5}   {('yes' if lag<=31 else 'no') if n else '-':4s}   {c['date']:%Y-%m}   {f'{err:+d}' if n else 'n/a'}")
print(f"\ncalled {len(calls)}: committee recessions {sum(1 for c in calls if near(c['claims_call']))}/12, other episodes {sum(1 for c in calls if not near(c['claims_call']))} ({[c['claims_call'].strftime('%Y-%m') for c in calls if not near(c['claims_call'])]}); episodes not called: {[e['published'].strftime('%Y-%m') for e in eps if not any(c['episode'] is e for c in calls)]}")
print(f"lag: median {np.median(L):.0f} d, in-month {sum(1 for x in L if x<=31)}/12, worst {max(L)}; dates exact {sum(1 for x in E if x==0)}/12, within one {sum(1 for x in E if abs(x)<=1)}, within three {sum(1 for x in E if abs(x)<=3)}, mae {np.mean(np.abs(E)):.2f}")
