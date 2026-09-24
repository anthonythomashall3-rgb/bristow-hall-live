"""One American onset call from three claims objects, 1947 to 2026: whichever fires first.

Legs, each causal and each with its own record already in the memo:
  A  the state diffusion index on the Fieldhouse monthly claims field, 1947 on, at the
     twelve-of-twelve setting of section 8d Finding 5 (amplitude 36, minimum phase 8,
     smoothing 2, real-time factors), published one month after its data month (the monthly
     state file's own lag; diffusion_peak_calls' convention) - this leg carries the DATE
  B  the national weekly claims conjunct (v8_legs.py: min of year-over-year log initial and
     continued claims, four-week mean) at 0.20 log points, 1968 on, hysteresis episodes,
     published seven days after the week
  C  the weekly state-breadth caller of speed_final.py, 1991 on, real-time factors
  M  the same conjunct at the same 0.20 line on the Fieldhouse field's national monthly
     unadjusted claims, 1948 on (legs_1948.py: weekly averages per month, the month for the
     four-week mean, six months for the twenty-six weeks; published the 10th of the month
     after) - the object that reaches the four peaks before the weekly file exists
The union calls a peak at the earliest of the publications; the date is leg A's when leg
A has fired, and 'pending' until then (the union says a recession has begun before it can say
when).  Other calls: any episode of any leg outside [peak-6, trough+3] months, distinct
episodes counted once.  Lags in days from the last day of the NBER peak month.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/fh'); sys.path.insert(0,'/home/claude/lab/weekly')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import v8_legs as V
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def month_end(t): return (t+pd.DateOffset(months=1))-pd.Timedelta(days=1)
def leg_A():
    import os; FIELD=os.environ.get('CLAIMS_FIELD','FH')   # 5 Sep 2026: HYB = Fieldhouse to 2024-01 continued by ETA 5159 (own_panel/build_hybrid_field.py)
    P=pd.read_csv(f'/home/claude/lab/fh/{FIELD}_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True)
    X=P.rolling(2).mean().dropna(how='all')
    D=B.claims_diffusion(X,36.,8)
    calls=B.diffusion_peak_calls(D,phase_min=5)
    # published: the monthly file for month m is in hand in m+1; take the 20th of that month (ETA 5159's release)
    return [(pd.Timestamp(p.year,p.month,20),d) for p,d in calls]
def leg_B(th=0.20):
    """the tool's own functions (claims_conjunct, conjunct_peak_calls) on the Department's file;
    identical to v8_legs.conjunct/episodes"""
    c=B.claims_conjunct(V.D.ic_nsa.dropna(),V.D.cc_nsa.dropna())
    return [(p,None) for p in B.conjunct_peak_calls(c,line=th,quiet_weeks=26,publication_days=7) if p>=pd.Timestamp('1969-01-08')]
def leg_C():
    rows=[]
    for l in open('/home/claude/lab/weekly/final_rt.out'):
        if l.strip().startswith('PEAK') and 'pub' in l:
            f=l.split(); pub=f[2]; dated=f[4]
            if pub<'1991': continue   # the weekly file's factors need five years of history; the record is 1991 on (speed_final.py)
            rows.append((pd.Timestamp(pub+'-01')+pd.Timedelta(days=27),pd.Timestamp(dated+'-01')))   # published inside the month: take the 28th
    return rows
if __name__=='__main__':
    import legs_1948 as L48
    legs={'A state diffusion index, monthly, 1947 on':leg_A(),'B national weekly conjunct 0.20, 1968 on':leg_B(0.20),'C weekly state breadth, 1991 on':leg_C(),
          'M national monthly conjunct 0.20, the field, 1948 on':L48.leg_M(0.20)}
    for k,v in legs.items(): print(k,':',[(p.strftime('%Y-%m-%d'),None if d is None else d.strftime('%Y-%m')) for p,d in v])
    print('\npeak      first call   leg  lag(d)  in-month  date carried at the call   A\'s date (pub)        B (pub)       C (pub)       M (pub)')
    used={k:set() for k in legs}; n_in=0; lags=[]
    for pk,tr in zip(PK,TR):
        lo=pk-pd.DateOffset(months=6); hi=tr+pd.DateOffset(months=3)
        best=None; cells={}
        for k,calls in legs.items():
            c=[(i,p,d) for i,(p,d) in enumerate(calls) if lo<=p<=hi+pd.Timedelta(days=31)]
            if c:
                i,p,d=min(c,key=lambda x:x[1]); used[k].add(i); cells[k[0]]=(p,d)
                if best is None or p<best[1]: best=(k[0],p,d)
        if best is None: print(f'{pk:%Y-%m}   none'); continue
        lag=(best[1]-month_end(pk)).days; inm=best[1]<=month_end(pk+pd.DateOffset(months=1)); n_in+=inm; lags.append(lag)
        a=cells.get('A'); datecar=(a[1].strftime('%Y-%m') if a and a[0]<=best[1] else 'pending')
        print(f"{pk:%Y-%m}   {best[1]:%Y-%m-%d}   {best[0]}   {lag:5d}   {'yes' if inm else 'no ':3s}      {datecar:8s}                {a[1].strftime('%Y-%m')+' ('+a[0].strftime('%Y-%m-%d')+')' if a else '-':22s} {cells['B'][0].strftime('%Y-%m-%d') if 'B' in cells else '-':12s} {cells['C'][0].strftime('%Y-%m-%d') if 'C' in cells else '-':12s} {cells['M'][0].strftime('%Y-%m-%d') if 'M' in cells else '-'}")
    print(f'\nunion: {len(lags)}/12 called, in-month {n_in}, median lag {np.median(lags):.0f} d, worst {max(lags)} d')
    # dates: leg A's (the shipped peak object, 1947 on); and the weekly object's where it exists
    A=legs['A state diffusion index, monthly, 1947 on']; Cc=legs['C weekly state breadth, 1991 on']
    def nearest(calls,pk):
        c=[d for p,d in calls if d is not None and abs(md(d,pk))<=6]
        return min(c,key=lambda d:abs(md(d,pk))) if c else None
    ea=[md(nearest(A,pk),pk) for pk in PK if nearest(A,pk) is not None]
    ec=[]
    for pk in PK:
        d=nearest(Cc,pk); d=d if d is not None else nearest(A,pk)
        if d is not None: ec.append(md(d,pk))
    print(f'dates, leg A alone: exact {sum(e==0 for e in ea)}/12, within one {sum(abs(e)<=1 for e in ea)}/12, errors {ea}')
    print(f'dates, the weekly object where it exists (1991 on), else A: exact {sum(e==0 for e in ec)}/12, within one {sum(abs(e)<=1 for e in ec)}/12, errors {ec}')
    other={}
    for k,calls in legs.items():
        for i,(p,d) in enumerate(calls):
            if i in used[k]: continue
            if any(pk-pd.DateOffset(months=6)<=p<=tr+pd.DateOffset(months=3)+pd.Timedelta(days=31) for pk,tr in zip(PK,TR)): continue
            other.setdefault(pd.Timestamp(p.year,p.month,1)+pd.DateOffset(months=0),[]).append((k[0],p.strftime('%Y-%m-%d')))
    # merge other calls within six months into one episode
    eps=[]
    for m in sorted(other):
        if eps and md(m,eps[-1][0])<=6: eps[-1][1]+=other[m]
        else: eps.append([m,list(other[m])])
    print('other calls (episodes, legs):',[(m.strftime('%Y-%m'),v) for m,v in eps])
    # ---- the tool's own grouping: the shipped route's record (no chronology in the grouping)
    import bristow_rule_v3 as B
    E=B.union_calls({k[0]:v for k,v in legs.items()},date_order=('C','A'))
    print("\nthe tool's grouping (union_calls, 365-day episodes, no chronology):")
    print('opened       leg  date at call  final date (leg)  peak      lag(d)  in-month')
    n_in=0; lags=[]; ex=0; w1=0; oth=[]
    for e in E:
        fd=e['date']; dl=e['date_leg']
        pk=[p_ for p_,t_ in zip(PK,TR) if p_-pd.DateOffset(months=6)<=e['published']<=t_+pd.DateOffset(months=3)+pd.Timedelta(days=31)]
        row=f"{e['published']:%Y-%m-%d}   {e['leg']}    {e['date_at_call'].strftime('%Y-%m') if e['date_at_call'] is not None else 'pending':8s}      {fd.strftime('%Y-%m') if fd is not None else '-':7s} ({dl})"
        if not pk: oth.append(e); print(row+'        other call'); continue
        t=pk[0]; lag=(e['published']-month_end(t)).days; inm=e['published']<=month_end(t+pd.DateOffset(months=1)); n_in+=inm; lags.append(lag)
        if fd is not None: err=md(fd,t); ex+=(err==0); w1+=(abs(err)<=1)
        print(row+f"        {t:%Y-%m}   {lag:5d}   {'yes' if inm else 'no'}")
    print(f"route: {len(lags)}/12 called, in-month {n_in}, median {np.median(lags):.0f} d, worst {max(lags)} d; final dates exact {ex}/12, within one {w1}/12; other episodes {len(oth)}: {[e['published'].strftime('%Y-%m-%d') for e in oth]}")
