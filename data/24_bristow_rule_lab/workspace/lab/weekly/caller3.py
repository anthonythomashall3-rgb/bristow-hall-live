"""Final sweep: breadth gate for the peak, national claims maximum for the trough,
three readings of the crossing for the peak date, two censors."""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_log.csv',index_col=0,parse_dates=True)
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def build(sm,L,thsq,nsm):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    B=(S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0
    N=(np.log(W['initial claims'])*100.0).rolling(nsm).mean()
    G=N-N.rolling(52,min_periods=26).min()
    return pd.concat([B.rename('b'),N.rename('n'),G.rename('g')],axis=1,sort=True).dropna()
def pk_date(b,i,line,how):
    j=i
    while j>0 and b[j]>=line: j-=1        # j = last week below the line
    if how=='last_below': k=j
    elif how=='first_above': k=min(j+1,len(b)-1)
    else: k=j                              # 'centre' handled below
    if how=='centre':
        a=j
        while a>0 and abs(b[a-1]-line)<abs(b[j]-line): a-=1
        k=j
    return k
def run(df,thb,nth,r,rt,delta,mp_p,mp_t,how,line=50.,pub=7):
    b=df['b'].values; nn=df['n'].values; g=df['g'].values; idx=df.index; m=len(b)
    calls=[]; state='exp'; last=-10**9; nmax=-1e9; nmax_i=None; fall=0; prev=None
    for i in range(max(r,rt),m):
        if state=='exp':
            if i-last<mp_p: continue
            if np.all(b[i-r+1:i+1]>=thb) and g[i]>=nth:
                k=pk_date(b,i,line,how)
                calls.append(('peak',idx[i]+pd.Timedelta(days=pub),mo(idx[k])))
                state='con'; last=i; nmax=nn[i]; nmax_i=i; fall=0; prev=nn[i]
        else:
            if nn[i]>nmax: nmax=nn[i]; nmax_i=i; fall=0
            elif nn[i]<prev: fall+=1
            else: fall=0
            prev=nn[i]
            if i-last>=mp_t and fall>=rt and (nmax-nn[i])>=delta:
                calls.append(('trough',idx[i]+pd.Timedelta(days=pub),mo(idx[nmax_i])))
                state='exp'; last=i
    return calls
def score(calls):
    hp={}; ht={}; fa=0
    for kind,pub,dt in calls:
        tgt,store=(PK,hp) if kind=='peak' else (TR,ht)
        best=None
        for k in tgt:
            if k in store: continue
            lag=md(mo(pub),pd.Timestamp(k+'-01')); err=md(dt,pd.Timestamp(k+'-01'))
            if abs(lag)<=2 and abs(err)<=2 and (best is None or abs(lag)+abs(err)<best[3]):
                best=(k,lag,err,abs(lag)+abs(err))
        if best: store[best[0]]=(best[1],best[2])
        else: fa+=1
    return hp,ht,fa
rows=[]
for sm,L,thsq,nsm in itertools.product((13,26),(52,78,104),(10.,15.,20.,25.),(4,13)):
    df=build(sm,L,thsq,nsm)
    for thb,nth,r,rt,delta,mp_p,mp_t,how in itertools.product(
            (35.,40.,50.,60.),(0.,10.),(2,4,8),(4,6,8),(2.,5.),(52,78),(13,22),
            ('last_below','first_above')):
        hp,ht,fa=score(run(df,thb,nth,r,rt,delta,mp_p,mp_t,how))
        tot=len(hp)+len(ht)
        if tot<6: continue
        rows.append((tot,-fa,sm,L,thsq,nsm,thb,nth,r,rt,delta,mp_p,mp_t,how,fa,dict(hp),dict(ht)))
rows.sort(reverse=True)
print(f'{"hits":>5s} {"false":>5s} {"sm":>3s} {"L":>4s} {"thsq":>4s} {"nsm":>4s} {"thb":>4s} {"nth":>4s} {"r":>2s} {"rt":>2s} {"del":>4s} {"mpp":>4s} {"mpt":>4s} {"how":>12s}')
for b in rows[:8]:
    print(f'{b[0]:2d}/8 {b[14]:5d} {b[2]:3d} {b[3]:4d} {b[4]:4.0f} {b[5]:4d} {b[6]:4.0f} {b[7]:4.0f} {b[8]:2d} {b[9]:2d} {b[10]:4.0f} {b[11]:4d} {b[12]:4d} {b[13]:>12s}')
    print(f'      peaks   {b[15]}')
    print(f'      troughs {b[16]}')
