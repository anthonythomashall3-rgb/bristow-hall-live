"""One American trough call from every object the record holds, 1969 to 2026: whichever fires
first says the contraction has ended; the object with the best dating record says when.

Legs, each causal, each with its own record in the memo:
  P  the Philadelphia Fed survey after the panel's D (twostage_us.py, general activity a=5
     r=1): published the third Thursday of the month it describes; six of eight troughs since
     1970, five inside the month, no other call since 1968; its own dates run 0 to 4 months
     early - it is the CALL, not the date
  K  weekly continued claims, real-time factors, Finding 2's detector (cc_trough_grid.py:
     four-week mean, arm 30, six falling weeks, drop 4), published five days after the week:
     eight of eight, four exact, six within one, no other call - it is the DATE
  I  national weekly initial claims, speed_final.py's level clause, on the Department's own
     national file 1969 on with the rule's real-time factors (see leg_I)
  D  the tool's own real-time trough rule on the panel's D, published one month after
     (twostage_us.py's first line)
  J  the national monthly continued claims of the Fieldhouse state field, December 1946 on,
     real-time factors, the tool's shipped monthly level clause at its defaults (legs_1948.py;
     published the 10th of the following month) - the object that reaches 1949-1961
  H  the same clause on the field's national monthly initial claims
Union: the call is the earliest publication among the legs; the date carried is K's once K has
fired, I's before that, and 'pending' when only P or D has fired.  Two readings are printed: the
per-leg table, which scores each leg's calls against the chronology (a call dated inside the
window is the trough's, the rest are other calls), and the tool's own grouping
(bristow_rule_v3.union_calls, 365-day episodes, no chronology), which is the shipped route's
record: there the initial-claims call of 18 July 1970, dated May, IS the 1970 trough's call -
four months early and wrong by six on the date until the continued-claims leg corrected it to
November on 14 January 1971 - and the 26 December call is a repeat inside the same episode.  A leg's call counts for a trough only if its date is within three months of the
committee's (six for the survey, whose date is known to run early); a later call dated inside the same window is a repeat; everything else is an
other call, distinct episodes once.  Lag in days from the last day of
the NBER trough month; 'in-month' = published by the end of the following month.
"""
import sys, re, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/speed')
import numpy as np, pandas as pd
import cc_trough_grid as C
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
NT=len(TR)
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def month_end(t): return (t+pd.DateOffset(months=1))-pd.Timedelta(days=1)
def leg_K():
    D=C.series(4); return [(p,d) for p,d in C.calls(D,6,4.,30.) if p>=pd.Timestamp('1969-06-01')]
def leg_I():
    """speed_final's initial-claims trough clause (eight-week mean, six falling weeks, drop 10,
    arm 40, re-arm 13 weeks) on the Department's own national weekly file with the rule's
    real-time factors, 1969 on - not the 1986 state-sum file speed_final read, which differs
    from the Department's file by a ratio of 0.08 to 2.7 across weeks (mean 0.97, sd 0.12) and
    on which the same clause fires every March from 1987 to 1990; on the Department's file it
    calls neither the 1991 nor the 2001 trough."""
    def mo(t): return pd.Timestamp(t.year,t.month,1)
    src=open('/home/claude/lab/weekly/final_caller.py').read()
    g={'pd':pd,'np':np,'mo':mo,'md':md}; exec("def trough_calls"+src.split("def trough_calls")[1].split("def sc(")[0],g)
    N=(np.log(C.W['ic_sa_rt'])*100.0).rolling(8).mean()
    D=pd.concat([N.rename('n'),(N-N.rolling(52,min_periods=26).min()).rename('g')],axis=1,sort=True).dropna()
    return g['trough_calls'](D,6,10.,40.,13)
def parse_line(text):
    """the dict printed by twostage_us.line(): {'1975-03': ('1974-12', -3, 'pub 1975-02', 'lag -1'), ...} -> [(pub, dated)]"""
    out=[]
    for m in re.finditer(r"'(\d{4}-\d{2})': \('(\d{4}-\d{2})', (-?\d+), 'pub (\d{4}-\d{2})'",text):
        out.append((pd.Timestamp(m[4]+'-01'),pd.Timestamp(m[2]+'-01')))
    return out
def leg_P():
    L=open('/home/claude/lab/speed/twostage_us.log').read().split('\n')
    for i,l in enumerate(L):
        if l.strip().startswith('Philly general activity a=5 r=1'):
            calls=parse_line(L[i+1]); break
    # the survey is published the third Thursday of its month: take the 18th
    return [(pd.Timestamp(p.year,p.month,18),d) for p,d in calls]
def leg_D():
    L=open('/home/claude/lab/speed/twostage_us.log').read().split('\n')
    for i,l in enumerate(L):
        if l.startswith("the tool's own clause on D"):
            calls=parse_line(L[i+1]); break
    return [(pd.Timestamp(p.year,p.month,15),d) for p,d in calls]   # production for the trigger month is out mid-month
if __name__=='__main__':
    import legs_1948 as L48
    legs={'P Philadelphia Fed after D':leg_P(),'K continued claims, Finding 2':leg_K(),'I initial claims level clause, 1969 on':leg_I(),'D the panel\'s own trough rule':leg_D(),
          'J monthly continued claims, the field, 1947 on':L48.leg_J(),'H monthly initial claims, the field, 1947 on':L48.leg_H()}
    for k,v in legs.items(): print(k,':',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in v])
    print('\ntrough    first call   leg  lag(d) in-month  date at the call   final date (leg)     K (pub)                 P (pub)               I (pub)               D (pub)               J (pub)               H (pub)')
    used={k:set() for k in legs}; n_in=0; lags=[]; ex=0; w1=0
    for pk,tr in zip(PK,TR):
        lo=pk-pd.DateOffset(months=3); hi=tr+pd.DateOffset(months=9)
        cells={}; best=None
        for k,calls in legs.items():
            tol=6 if k[0]=='P' else 3   # the survey is the call, its date runs early (memo: hits within six months); the claims legs must date within three
            c=[(i,p,d) for i,(p,d) in enumerate(calls) if abs(md(d,tr))<=tol and lo<=p<=hi+pd.DateOffset(months=6)]
            if c:
                i,p,d=min(c,key=lambda x:x[1]); used[k].add(i); cells[k[0]]=(p,d)
                if best is None or p<best[1]: best=(k[0],p,d)
        if best is None: print(f'{tr:%Y-%m}   none'); continue
        lag=(best[1]-month_end(tr)).days; inm=best[1]<=month_end(tr+pd.DateOffset(months=1)); n_in+=inm; lags.append(lag)
        # date carried at the call: K if fired by then, else I, else the monthly J then H, else pending
        at=None
        for L_ in ('K','I','J','H'):
            if L_ in cells and cells[L_][0]<=best[1]: at=cells[L_][1]; break
        final=None
        for L_ in ('K','I','J','H','D'):
            if L_ in cells: final=(cells[L_][1],L_); break
        if final: e=md(final[0],tr); ex+=(e==0); w1+=(abs(e)<=1)
        print(f"{tr:%Y-%m}   {best[1]:%Y-%m-%d}   {best[0]}   {lag:5d}  {'yes' if inm else 'no ':3s}      {at.strftime('%Y-%m') if at is not None else 'pending':8s}          {final[0].strftime('%Y-%m')+' ('+final[1]+')' if final else '-':14s}  "+'  '.join(f"{cells[x][0].strftime('%Y-%m-%d')+' '+cells[x][1].strftime('%Y-%m') if x in cells else '-':20s}" for x in 'KPIDJH'))
    print(f'\nunion: {len(lags)}/{NT} called, in-month {n_in}, median lag {np.median(lags):.0f} d, worst {max(lags)} d; final dates exact {ex}/{NT}, within one {w1}/{NT}')
    l8=lags[-8:]; print(f'   the eight since 1970 alone: in-month {sum(1 for pk,tr in zip(PK,TR) if tr>=pd.Timestamp("1970-01-01") and False)}(see table), lags {l8}')
    other={}
    for k,calls in legs.items():
        for i,(p,d) in enumerate(calls):
            if i in used[k]: continue
            if any(abs(md(d,tr))<=(6 if k[0]=='P' else 3) for tr in TR): continue   # a repeat inside the same episode
            if p<pd.Timestamp('1947-06-01'): continue
            other.setdefault(pd.Timestamp(p.year,p.month,1),[]).append((k[0],p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')))
    eps=[]
    for m in sorted(other):
        if eps and md(m,eps[-1][0])<=6: eps[-1][1]+=other[m]
        else: eps.append([m,list(other[m])])
    print('other calls (episodes, legs):',[(m.strftime('%Y-%m'),v) for m,v in eps])
    # ---- the tool's own grouping: the shipped route's record
    import bristow_rule_v3 as B
    E=B.union_calls({k[0]:v for k,v in legs.items()},date_order=('K','I','J','H','D'))
    print("\nthe tool's grouping (union_calls, 365-day episodes, no chronology):")
    print('opened       leg  date at call  final date (leg)  trough    lag(d)  in-month')
    n_in=0; lags=[]; ex=0; w1=0; oth=[]
    for e in E:
        fd=e['date']; dl=e['date_leg']
        if fd is None:   # only P or D fired: use the survey's own date
            pd_=[d for L_,p,d in e['members'] if d is not None]; fd=pd_[0] if pd_ else None; dl='P'
        tr=[t for t in TR if fd is not None and abs(md(fd,t))<=(6 if dl=='P' else 3)]
        if not tr: oth.append(e); print(f"{e['published']:%Y-%m-%d}   {e['leg']}    {e['date_at_call'].strftime('%Y-%m') if e['date_at_call'] is not None else 'pending':8s}      {fd.strftime('%Y-%m') if fd is not None else '-'} ({dl})        other call"); continue
        t=tr[0]; lag=(e['published']-month_end(t)).days; inm=e['published']<=month_end(t+pd.DateOffset(months=1)); n_in+=inm; lags.append(lag)
        err=md(fd,t); ex+=(err==0); w1+=(abs(err)<=1)
        print(f"{e['published']:%Y-%m-%d}   {e['leg']}    {e['date_at_call'].strftime('%Y-%m') if e['date_at_call'] is not None else 'pending':8s}      {fd:%Y-%m} ({dl})        {t:%Y-%m}   {lag:5d}   {'yes' if inm else 'no'}")
    print(f"route: {len(lags)}/{NT} called, in-month {n_in}, lags {sorted(lags)}, worst after the trough {max(lags)} d; final dates exact {ex}/{NT}, within one {w1}/{NT}; other episodes {len(oth)}: {[e['published'].strftime('%Y-%m-%d') for e in oth]}")
