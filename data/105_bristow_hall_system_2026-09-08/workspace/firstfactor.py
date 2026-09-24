"""The first factor is the bigger lever and nobody has pulled it.

The route's hazard is P(a claims leg opens in a quiet month) x P(the second
condition is met inside the window). Everything the programme has done for a
month has attacked the SECOND factor. The first is three quiet episodes -- July
1951, March 1952, February 1967 -- in 38.5 quiet years, and it is 7.79 per cent
a year. Which legs open them, and is any leg carrying all three?"""
exec(open('eta5159_gate.py').read().split("PK5=('A','B','C','M','U')")[0])
import numpy as np, pandas as pd, io, contextlib
def leg_U2(line=0.50,smooth=1,look=52,pub=5):
    x=s.rolling(smooth).mean(); gap=x-x.rolling(look,min_periods=look).min().shift(1)
    c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
PLU=dict(PL); PLU['U']=leg_U2()
M=lambda x: pd.Timestamp(x+'-01')
def is_quiet(d):
    return not any((d>=M(p)-pd.DateOffset(months=9)) and (d<=M(t)+pd.DateOffset(months=18))
                   for p,t in zip(PEAKS,TROUGHS))
print("every claims leg's calls, and which of them land in a QUIET month")
print(f"{'leg':5}{'calls':>7}{'quiet calls':>13}   the quiet ones")
for k in ('A','B','C','M','U'):
    v=PLU[k]; q=[(p,d) for p,d in v if is_quiet(d)]
    print(f"{k:5}{len(v):7d}{len(q):13d}   " + (', '.join(f'{d:%Y-%m}' for _,d in q) or '-'))
UR=first_prints("UNRATE"); HO=first_prints("HOUST"); lh=np.log(HO)*100
PAIR=pd.concat([(lh.rolling(12).max()-lh.rolling(2).mean())/35.0,
                (UR-UR.rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
SEC=[dict(name='vacancy',gap=vr,line=0.36,pub_day=30),
     dict(name='payroll3',gap=P3,line=0.3,pub_day=5),
     dict(name='housing35',gap=PAIR,line=1.0,pub_day=18)]
PK5=('A','B','C','M','U'); TR3=('K','J','H')
import itertools
print("\ndropping each leg: what it costs in speed, what it buys in quiet exposure")
print(f"{'legs':10}{'peaks':>7}{'other':>7}{'median':>8}{'mean':>7}{'worst':>7}{'exact':>7}{'quiet leg-calls':>17}")
for r in range(5,2,-1):
    for sub in itertools.combinations(PK5,r):
        qc=sum(1 for k in sub for p,d in PLU[k] if is_quiet(d))
        with contextlib.redirect_stdout(io.StringIO()):
            res=score(B.american_chronology({k:PLU[k] for k in sub},{k:TLG[k] for k in TR3},
                      sahm=g,second=SEC,horizon_months=6),'x','1948-06-01')
        lp,ep=res['lags_p'],res['errs_p']
        if len(lp)<12: continue
        print(f"{''.join(sub):10}{len(lp):7d}{res['other']:7d}{np.median(lp):8.0f}{np.mean(lp):7.1f}"
              f"{max(lp):7d}{sum(1 for e in ep if e==0):7d}{qc:17d}")
