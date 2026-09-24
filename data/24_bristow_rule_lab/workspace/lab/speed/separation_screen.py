"""Does any labor-market object outside the United States separate the way the American
claims conjunct does?  A screen, not a search: for each object one statistic is computed
with no fitted parameter - the twelve-month change of the three-month mean (log change for
counts, points for rates; the sign turned so that a rise means contraction) - and two numbers
are read off it: the LOWEST maximum the statistic reaches inside any committee-dated
contraction, and the HIGHEST value it takes in a quiet month (outside a contraction and more
than twelve months past a trough).  If the first exceeds the second the object separates,
and a line anywhere between them calls every contraction with no other call; the speed of
that call is then measured at the midpoint line (data month of the first crossing less the
peak month; the source's own publication lag is stated beside it).  If it does not separate
the margin is reported as it is.  Pairs are the conjunct form: the smaller of two turned
statistics, so both must have moved.

Objects: Germany - registered unemployed (Bundesagentur, unadjusted, 1950 on), vacancies
(unadjusted), short-time workers, the unemployed/vacancies conjunct, and the Council's
chronology; Canada - the LFS unemployment rate (OECD, adjusted, 1955 on), EI claims received
(Statistics Canada 14-10-0005, unadjusted, national, 1943 on), and the Council's monthly
peaks; Japan - the unemployment rate and the effective job-offer rate (ESRI's channel), the
ESRI's chronology; Korea - the unemployment rate (1990 on), Statistics Korea's chronology;
United States - the unemployment rate on the same footing, for comparison with the weekly
conjunct of section 8f.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bench
from bench import load, ts
KEI='/home/claude/lab/kei'; NAT='/home/claude/lab/nat'
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def chron(cn):
    return [(ts(bench.ep3(e,'M')[0]),ts(bench.ep3(e,'M')[1])) for e in bench.PANELS[cn]['chrono'] if bench.ep3(e,'M')[2]=='M']
DE=[(ts(a),ts(b)) for a,b in [('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')]]
def stat(s, kind):
    m=s.rolling(3).mean()
    if kind=='count': return (np.log(m)-np.log(m.shift(12))).dropna()          # a rise = contraction (unemployed, claims)
    if kind=='count_down': return (np.log(m.shift(12))-np.log(m)).dropna()     # a fall = contraction (vacancies, job offers)
    if kind=='rate': return (m-m.shift(12)).dropna()                             # points; a rise = contraction
    if kind=='rate_down': return (m.shift(12)-m).dropna()
    raise ValueError(kind)
def ei_claims():
    """initial and renewal claims received, Canada, unadjusted, 1943 on; Statistics Canada
    suppressed the series from March 2020 while the CERB ran, so the 2020 contraction is a wall
    for this object and is left out of its windows"""
    d=pd.read_csv('/home/claude/lab/acq/statcan/14100005/14100005.csv',usecols=['REF_DATE','GEO','Type of claim','Claim detail','VALUE'],low_memory=False)
    d=d[(d.GEO=='Canada')&(d['Claim detail']=='Received')&(d['Type of claim']=='Initial and renewal claims')]
    s=pd.Series(pd.to_numeric(d.VALUE,errors='coerce').values,index=pd.to_datetime(d.REF_DATE)).dropna().sort_index()
    return s[~s.index.duplicated()], 'initial and renewal claims received'
def screen_reach(name,S,C,pub_lag):
    """windows the object can see: skip contractions with no readings inside them"""
    C2=[(a,b) for a,b in C if b in S.index and len(S[(S.index>=a)&(S.index<=b)])>=2]
    return screen(name,S,C2,pub_lag)
def screen(name, S, C, pub_lag):
    inrec=pd.Series(False,index=S.index)
    for a,b in C: inrec[(S.index>=a)&(S.index<=b)]=True
    quiet=S[~inrec].copy()
    for a,b in C: quiet=quiet[(quiet.index<a)|(quiet.index>b+pd.DateOffset(months=12))]
    win=[(a,S[(S.index>=a)&(S.index<=b)]) for a,b in C if len(S[(S.index>=a)&(S.index<=b)])]
    reach=[a for a,w in win]
    if not win or not len(quiet): print(f'  {name:52s} no overlap'); return
    rec_max=[float(w.max()) for a,w in win]; lo=min(rec_max); hi=float(quiet.max()); hi_at=quiet.idxmax()
    sep=lo>hi
    line=(lo+hi)/2
    out=f'  {name:52s} contractions {len(win)}  lowest recession max {lo:+.3f}  highest quiet {hi:+.3f} ({hi_at:%Y-%m})  margin {lo-hi:+.3f}  {"SEPARATES" if sep else "does not separate"}'
    if sep:
        # episodes at the midpoint line: first month at/above the line after >= 12 months below
        starts=[]; below=0
        for t,v in S.items():
            if v>=line:
                if below>=12: starts.append(t)
                below=0
            else: below+=1
        lags=[]; other=[]
        for st in starts:
            m=[a for a,b in C if -3<=md(st,a)<=md(b,a)+3]
            if m: lags.append(md(st,m[0]))
            else: other.append(st.strftime('%Y-%m'))
        out+=f'\n      at the midpoint line {line:+.3f}: crossings {len(lags)}/{len(win)} in the data month peak{["%+d"%l for l in lags]}, publication lag +{pub_lag} month(s); other crossings {other}'
    else:
        # how many quiet months exceed the lowest recession maximum, and which
        bad=quiet[quiet>=lo]
        out+=f'\n      quiet months at or above the lowest recession maximum: {len(bad)} ({", ".join(sorted(set(t.strftime("%Y") for t in bad.index))[:12])}); recession maxima {[round(x,3) for x in rec_max]}'
        q2=quiet[quiet.index>=pd.Timestamp('1948-01-01')]
        if len(q2) and q2.idxmax()!=hi_at: out+=f'\n      (from 1948: highest quiet {float(q2.max()):+.3f} at {q2.idxmax():%Y-%m}, margin {lo-float(q2.max()):+.3f})'
    print(out)
if __name__=='__main__':
    print('=== Germany (the Council, seven contractions 1966-2020)')
    u=load(f'{NAT}/deu/DEU_unemployed_nsa.csv'); v=load(f'{NAT}/deu/DEU_vacancies_nsa.csv'); k=load(f'{NAT}/deu/DEU_short_time_workers_nsa.csv')
    screen('registered unemployed, unadjusted, yoy',stat(u,'count'),DE,0)
    screen('vacancies, unadjusted, yoy (fall)',stat(v,'count_down'),DE,0)
    screen('short-time workers, unadjusted, yoy',stat(k,'count'),DE,0)
    cj=pd.concat([stat(u,'count'),stat(v,'count_down')],axis=1).dropna().min(axis=1)
    screen('conjunct: unemployed up AND vacancies down',cj,DE,0)
    screen('unemployment rate, adjusted, spliced, yoy points',stat(load(f'{NAT}/deu/DEU_unemployment_rate_sa_spliced.csv'),'rate'),DE,0)
    print('=== Canada (the Council, monthly peaks)')
    CA=chron('Canada')
    screen('LFS unemployment rate, adjusted (OECD), yoy points',stat(load(f'{KEI}/CAN_UNEMP__T.csv'),'rate'),CA,0)
    try:
        s,lab=ei_claims(); screen_reach(f'EI {lab}, unadjusted, yoy (2020 a wall)',stat(s,'count'),CA,2)
    except Exception as e: print('  EI claims: ',e)
    print('=== Japan (ESRI)')
    JP=chron('Japan')
    screen('unemployment rate, adjusted (OECD), yoy points',stat(load(f'{KEI}/JPN_UNEMP__T.csv'),'rate'),JP,1)
    jo=[p for nm,p,kd in bench.PANELS['Japan']['ch'] if nm=='effective job offer rate']
    if jo: screen('effective job-offer rate (ESRI channel), yoy (fall)',stat(load(jo[0]),'rate_down'),JP,1)
    print('=== Korea (Statistics Korea)')
    KR=chron('Korea')
    screen('unemployment rate, adjusted (OECD), yoy points, 1990 on',stat(load(f'{KEI}/KOR_UNEMP__T.csv'),'rate'),KR,1)
    print('=== United States (NBER), the same statistic for comparison')
    US=chron('United States')
    screen('unemployment rate, adjusted, yoy points',stat(load(f'{KEI}/USA_UNEMP__T.csv'),'rate'),US,0)
