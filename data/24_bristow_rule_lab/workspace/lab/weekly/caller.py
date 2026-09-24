"""The complete real-time caller on weekly data, both ends, with dates.

BREADTH  B(t) = share of the states whose 13-week mean of seasonally adjusted initial
         claims stands at least thsq log points above its own trailing L-week minimum.
         This is the rule's diffusion object built weekly across the states.
ALERT    from expansion: B >= thb for r weeks and the national gap >= nth.  From
         contraction: B <= thb_t for r weeks.
DATE     the diffusion clause, as ESRI states it: the peak is the last week B stood
         below the fifty-percent line before crossing it from below; the trough is the
         last week B stood above it before crossing from above.  Reported as the month.
CENSOR   mp weeks minimum between calls, and the machine alternates.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
NAT=(np.log(W['initial claims'])*100.0)
def build(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    B=(S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0
    G=NAT.rolling(13).mean(); G=(G-G.rolling(52,min_periods=26).min())
    df=pd.concat([B.rename('b'),G.rename('g')],axis=1,sort=True).dropna()
    return df
def cross_date(b,i,line,up):
    """last week on the other side of the line before the crossing at or before i"""
    j=i
    while j>0 and ((b[j]>=line) if up else (b[j]<=line)): j-=1
    return j
def run(df,thb,thb_t,nth,r,rt,mp,line=50.,pub=7):
    b=df['b'].values; g=df['g'].values; idx=df.index; n=len(b)
    calls=[]; state='exp'; last=-10**9
    for i in range(max(r,rt),n):
        if i-last<mp: continue
        if state=='exp':
            if np.all(b[i-r+1:i+1]>=thb) and g[i]>=nth:
                j=cross_date(b,i,line,True)
                calls.append(('peak',idx[i]+pd.Timedelta(days=pub),mo(idx[j])))
                state='con'; last=i
        else:
            if np.all(b[i-rt+1:i+1]<=thb_t):
                j=cross_date(b,i,line,False)
                calls.append(('trough',idx[i]+pd.Timedelta(days=pub),mo(idx[j])))
                state='exp'; last=i
    return calls
def score(calls):
    hp={}; ht={}; fa=0
    for kind,pub,dt in calls:
        tgt,store=(PK,hp) if kind=='peak' else (TR,ht)
        best=None
        for k in tgt:
            if k in store: continue
            e=md(mo(pub),pd.Timestamp(k+'-01'))
            if abs(e)<=2 and (best is None or abs(e)<abs(best[1])): best=(k,e)
        if best: store[best[0]]=(best[1],md(dt,pd.Timestamp(best[0]+'-01')))
        else: fa+=1
    return hp,ht,fa
rows=[]
for sm,L,thsq in itertools.product((13,26),(52,78,104),(10.,15.,20.,25.)):
    df=build(sm,L,thsq)
    for thb,thb_t,nth,r,rt,mp in itertools.product((40.,50.,60.,70.),(20.,30.,40.,50.),
                                                   (0.,10.),(4,8),(4,8),(39,52)):
        hp,ht,fa=score(run(df,thb,thb_t,nth,r,rt,mp))
        tot=len(hp)+len(ht)
        if tot<6: continue
        errs=[abs(v[1]) for v in list(hp.values())+list(ht.values())]
        rows.append((tot,-max(errs),-fa,sm,L,thsq,thb,thb_t,nth,r,rt,mp,fa,
                     max(errs),np.mean(errs),dict(hp),dict(ht)))
rows.sort(reverse=True)
print(f'{"hits":>5s} {"errmx":>5s} {"false":>5s} {"sm":>3s} {"L":>4s} {"thsq":>5s} {"thb":>4s} {"thbt":>5s} {"nth":>4s} {"r":>2s} {"rt":>2s} {"mp":>4s}')
for b in rows[:10]:
    print(f'{b[0]:2d}/8 {b[13]:5d} {b[12]:5d} {b[3]:3d} {b[4]:4d} {b[5]:5.0f} {b[6]:4.0f} {b[7]:5.0f} {b[8]:4.0f} {b[9]:2d} {b[10]:2d} {b[11]:4d}')
    print(f'        peaks {b[15]}')
    print(f'        troughs {b[16]}')
