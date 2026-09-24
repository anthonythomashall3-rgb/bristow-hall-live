"""The claims objects before the weekly files exist: the American record 1948-1969 read from the
Fieldhouse-Munro-Koch-Howard monthly state claims field (CBUR Data.dta, December 1946 to
January 2024), summed to a national monthly series.

Three legs, each the weekly object's clause carried to monthly frequency with NOTHING chosen
here - every number is the one already shipped for the weekly or monthly object, so the
1948-1968 record is held out from every choice:
  M  the claims conjunct (min of the year-over-year log changes of unadjusted initial and
     continued claims; claims_conjunct) at the 0.20 line chosen on the weekly file 1969 on
     (memo section 8f), the weekly 4-week mean replaced by the month (weeks=12 on monthly
     data; hysteresis 6 months for the 26 weeks).  A peak call; carries no date.
  J  weekly continued claims' clause at monthly frequency: the tool's shipped monthly level
     clause (level_trough_calls at its defaults: two-month mean, lookback 30, one falling
     month, drop 1.0, arm 50, re-arm 5 for 3 months - the setting chosen on the Department's
     1971-on monthly file, memo section 8) on the real-time-adjusted national continued
     claims (lab/fh/FH_nat_sa_rt.csv, the rule's own routine, no look-ahead).  Dated at the
     month claims peaked.
  H  the same clause on the real-time-adjusted national initial claims.
Monthly totals are turned into weekly averages with the file's own weeks-per-month weight
(MonthtoWeekWeight: weekdays/5) before the year-over-year change, so a five-week month is not
read as a rise; the adjusted series were built from the totals (build_rt.py) and are used as
built.  Publication: a month's claims were public within days of its end (the Bureau of
Employment Security's weekly release, 1940s on), so a call on month T is dated public on the
10th of T+1 - later than the weekly reader had it, earlier than the state index's 20th.
Every leg is scored on all twelve NBER peaks or troughs 1948-2020 so the two eras can be read
side by side; the union scripts read the legs from here.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude')
import numpy as np, pandas as pd
import bristow_rule_v3 as B
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
TR=[pd.Timestamp(x) for x in ('1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def month_end(t): return (t+pd.DateOffset(months=1))-pd.Timedelta(days=1)
def pub10(m): return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
import os; FIELD=os.environ.get('CLAIMS_FIELD','FH')   # 5 Sep 2026: HYB = Fieldhouse to 2024-01 continued by ETA 5159 (own_panel/build_hybrid_field.py)
def national_nsa():
    if FIELD!='FH':
        n=pd.read_csv(f'/home/claude/lab/fh/{FIELD}_national_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
        n.index=[pd.Timestamp(t.year,t.month,1) for t in n.index]; return n['initial claims'], n['continued weeks claimed']
    d=pd.read_stata('/home/claude/lab/fh/src/CBUR Data.dta')
    g=d.groupby('Date')[['IC_NSA','CC_NSA']].sum(); g['w']=d.groupby('Date')['MonthtoWeekWeight'].first()
    g.index=pd.to_datetime(g.index); g.index=[pd.Timestamp(t.year,t.month,1) for t in g.index]
    return (g['IC_NSA']/g['w']), (g['CC_NSA']/g['w'])
def leg_M(line=0.20):
    ic,cc=national_nsa()
    c=B.claims_conjunct(ic,cc,weeks=12,smooth=1)
    return [(pub10(p-pd.Timedelta(days=7)),None) for p in B.conjunct_peak_calls(c,line=line,quiet_weeks=6,publication_days=7)]
def _nat_rt():
    return pd.read_csv(f'/home/claude/lab/fh/{FIELD}_nat_sa_rt.csv',index_col=0,parse_dates=True)
RECORD_START=pd.Timestamp('1949-01-01')   # 3 September 2026: the field's real-time factors need 24 months of history
# (build_rt.py adjusts nothing before 1949), so a level clause's record on the field begins with its first adjusted
# year, exactly as the weekly state file's record begins with its first factor year (1991).  Calls made on the
# unadjusted 1947-48 data are warm-up calls, listed and left out of the record (the July 1948 initial-claims call).
def leg_J(record=True):
    s=np.log(_nat_rt()['continued weeks claimed'].dropna())
    out=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(s)]
    return [x for x in out if x[0]>=RECORD_START] if record else out
def leg_H(record=True):
    s=np.log(_nat_rt()['initial claims'].dropna())
    out=[(pub10(p-pd.DateOffset(months=1)),d) for p,d in B.level_trough_calls(s)]
    return [x for x in out if x[0]>=RECORD_START] if record else out
def score_peaks(calls, label):
    hits={}; used=set()
    for i,(pk,tr) in enumerate(zip(PK,TR)):
        c=[(j,p) for j,(p,d) in enumerate(calls) if pk-pd.DateOffset(months=6)<=p<=tr+pd.DateOffset(months=3)+pd.Timedelta(days=31)]
        if c: j,p=min(c,key=lambda x:x[1]); hits[i]=(p-month_end(pk)).days; used|={j for j,_ in c}
    other=[p.strftime('%Y-%m-%d') for j,(p,d) in enumerate(calls) if j not in used]
    pre=[i for i in hits if PK[i]<pd.Timestamp('1969-01-01')]
    print(f'{label}: peaks {len(hits)}/12 (1948-60: {len(pre)}/4), in-month {sum(v<=31 for v in hits.values())}, lags {[(PK[i].strftime("%Y-%m"),hits[i]) for i in sorted(hits)]}, other {other}')
def score_troughs(calls, label, tol=3):
    hits={}; used=set()
    for i,tr in enumerate(TR):
        c=[(j,p,d) for j,(p,d) in enumerate(calls) if abs(md(d,tr))<=tol]
        if c: j,p,d=min(c,key=lambda x:x[1]); hits[i]=((p-month_end(tr)).days,md(d,tr)); used|={j for j,_,_ in c}
    other=[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for j,(p,d) in enumerate(calls) if j not in used]
    pre=[i for i in hits if TR[i]<pd.Timestamp('1969-01-01')]
    print(f'{label}: troughs {len(hits)}/12 (1949-61: {len(pre)}/4), in-month {sum(v[0]<=31 for v in hits.values())}, exact {sum(v[1]==0 for v in hits.values())}, within one {sum(abs(v[1])<=1 for v in hits.values())}, (lag d, date err) {[(TR[i].strftime("%Y-%m"),hits[i]) for i in sorted(hits)]}, other {other}')
if __name__=='__main__':
    ic,cc=national_nsa(); print('national weekly-average claims from the field:',ic.index.min().strftime('%Y-%m'),'->',ic.index.max().strftime('%Y-%m'))
    c=B.claims_conjunct(ic,cc,weeks=12,smooth=1)
    rec=pd.Series(False,index=c.index)
    for pk,tr in zip(PK,TR): rec[(c.index>=pk)&(c.index<=tr)]=True
    quiet=c[~rec]
    # quiet = outside a recession and more than a year past a trough
    q=[]
    for t,v in c.items():
        if rec[t]: continue
        last=[tr for tr in TR if tr<t]
        if last and md(t,last[-1])<=12: continue
        q.append(v)
    print(f'monthly conjunct: quiet-month maximum {max(q):+.3f} (n={len(q)}); recession-window maxima {[(pk.strftime("%Y-%m"),round(float(c[(c.index>=pk)&(c.index<=tr)].max()),3)) for pk,tr in zip(PK,TR)]}')
    for line in (0.20,0.15,0.25,0.30): score_peaks(leg_M(line),f'M conjunct monthly, line {line:.2f}')
    for f,l in ((leg_J,'J continued claims monthly, shipped clause'),(leg_H,'H initial claims monthly, shipped clause')):
        calls=f(); print('   calls:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in calls]); score_troughs(calls,l)
