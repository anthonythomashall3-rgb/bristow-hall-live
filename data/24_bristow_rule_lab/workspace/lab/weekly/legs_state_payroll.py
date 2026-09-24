"""A new American peak object: the breadth of states whose payroll employment is falling, 1947 on.

Anthony (3 September 2026): find and use more data; take what the old creations hold; make the onset
faster with no false alarm.  The Fieldhouse-Munro-Koch-Howard field carries state nonfarm payrolls
beside the claims (CBUR Data.dta, nonfarm_NSA, December 1946 to January 2024; lab/fh/
FH_state_payrolls_nsa.csv).  The claims objects of the route (A, B, C, M) read the labor market
through claims; this leg reads it through the states' payrolls themselves - the series the committee
weighs most - as a diffusion index built exactly as leg A builds its claims index: each state's log
level seasonally adjusted in real time (build_rt.py's routine: month-of-year medians, moving
seven-year window, refitted each December, no look-ahead), negated so that falling employment is a
deteriorating phase, put through the tool's causal phase monitor (channel_phase: a state turns down
after it has fallen `amplitude` log points from its running maximum and `min_phase` months have
passed since its last turn), and the share of states deteriorating read with ESRI's clause
(diffusion_peak_calls: the peak is the last month the share stood below fifty per cent, minimum
phase five, cycle fifteen, two-year warm-up).  Publication: the state payroll figures for month T
are public in the third week of T+1 (BLS state employment release; historically Employment and
Earnings) - the call is dated the 20th of T+1, the same day leg A uses.

The amplitude and minimum phase are the two numbers this object needs; claims use 36 log points and
8 months (memo section 8d Finding 5).  Payrolls move a few per cent in a recession, so those numbers
cannot be carried over and are chosen the way Rule 18 allows: a grid, with the setting chosen on
eleven peaks (most called, fewest other calls, most inside the month, shortest lags) and applied to
the twelfth.  Scored exactly as legs_1948.score_peaks scores the other legs (a call inside
[peak-6, trough+3] is the peak's; in-month = published within 31 days of the peak month's end; every
other call is an other call).  Record from 1949 (RECORD_START: the real-time factors need 24 months).
Output legs_state_payroll.log.  Nothing adopted on its score.
"""
import sys, itertools, warnings, collections; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import legs_1948 as L
src=open('/home/claude/lab/fh/build_rt.py').read()
g={'pd':pd,'np':np,'WIN':7,'OWN_YEARS':5}; exec(src.split('L=pd.read_csv')[0].split("import sys, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')")[1].replace("sys.path.insert(0,'/home/claude/lab/dol')",''),g)
sa_realtime=g['sa_realtime']
P=pd.read_csv('/home/claude/lab/fh/FH_state_payrolls_nsa.csv',index_col=0,parse_dates=True)
P=P.loc[:,P.notna().mean()>0.9]
SA=sa_realtime(P)                      # log level, real-time factors
X=-SA                                  # negated: a falling payroll is a rising 'claims-like' phase
def calls(amp, mp, sm=1, line=50.0, phase_min=5):
    Z=X.rolling(sm).mean().dropna(how='all') if sm>1 else X
    D=B.claims_diffusion(Z,amp,mp)
    c=B.diffusion_peak_calls(D,line=line,phase_min=phase_min)
    out=[(pd.Timestamp(p.year,p.month,20),d) for p,d in c]
    return [x for x in out if x[0]>=L.RECORD_START], D
def score(cl):
    """(hits dict i->(lag days, date err), other calls list)"""
    hits={}; used=set()
    for i,(pk,tr) in enumerate(zip(L.PK,L.TR)):
        c=[(j,p,d) for j,(p,d) in enumerate(cl) if pk-pd.DateOffset(months=6)<=p<=tr+pd.DateOffset(months=3)+pd.Timedelta(days=31)]
        if c: j,p,d=min(c,key=lambda x:x[1]); hits[i]=((p-L.month_end(pk)).days, L.md(d,pk)); used|={j for j,_,_ in c}
    other=[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for j,(p,d) in enumerate(cl) if j not in used]
    return hits,other
def key(hits,other,idx):
    h={i:v for i,v in hits.items() if i in idx}
    return (len(h), -len(other), sum(1 for v in h.values() if v[0]<=31), sum(1 for v in h.values() if v[1]==0), -np.mean([v[0] for v in h.values()]) if h else -999)
if __name__=='__main__':
    print(f'states {SA.shape[1]}, months {SA.index.min():%Y-%m} to {SA.index.max():%Y-%m}')
    GRID=list(itertools.product((0.3,0.5,0.75,1.0,1.5,2.0,3.0),(3,6,8,13),(1,2,3)))
    res={}
    for amp,mp,sm in GRID:
        cl,D=calls(amp,mp,sm); res[(amp,mp,sm)]=score(cl)
    z=sorted(res,key=lambda s:key(*res[s],range(12)),reverse=True)
    print('\nin-sample best ten (hits, -other, in-month, exact, -mean lag):')
    for s in z[:10]:
        h,o=res[s]; k=key(h,o,range(12))
        print(f'  amp {s[0]:4.2f} min_phase {s[1]:2d} smooth {s[2]}: hits {k[0]:2d}/12 other {-k[1]:2d} in-month {k[2]:2d} exact {k[3]:2d} mean lag {-k[4]:.0f} d; lags {[(L.PK[i].strftime("%Y-%m"),v[0]) for i,v in sorted(h.items())]}')
    print('\nleave one peak out (chosen on the other eleven):')
    oos={}; picks=collections.Counter()
    for i in range(12):
        others=[j for j in range(12) if j!=i]
        best=max(res,key=lambda s:key(*res[s],others)); picks[best]+=1
        h,o=res[best]; oos[i]=h.get(i)
        print(f"  held out {L.PK[i]:%Y-%m}: picks amp {best[0]} mp {best[1]} sm {best[2]} -> {'not called' if i not in h else f'lag {h[i][0]} d, date err {h[i][1]:+d}, in-month {h[i][0]<=31}'}; that setting's other calls {len(o)} {o[:4]}")
    v=[x for x in oos.values() if x is not None]
    print(f'  out of sample: called {len(v)}/12, in-month {sum(1 for x in v if x[0]<=31)}, exact {sum(1 for x in v if x[1]==0)}, within one {sum(1 for x in v if abs(x[1])<=1)}; picked {dict(picks)}')
    s=max(picks,key=picks.get); cl,D=calls(*s)
    print(f'\nthe setting picked most often, amp {s[0]} mp {s[1]} sm {s[2]}: calls {[(p.strftime("%Y-%m-%d"),d.strftime("%Y-%m")) for p,d in cl]}')
    print('share of states deteriorating, 2022 on (that setting):'); print(D['2022-01':].round(0).to_string())
