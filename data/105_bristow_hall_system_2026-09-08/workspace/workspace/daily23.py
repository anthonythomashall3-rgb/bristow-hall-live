"""MORE DOORS. (a) the 0.45 branch's look-back window swept finely — 104 weeks buys 1990 by fifteen days and nobody
had swept it; (b) CORPORATE BOND SPREADS (Baa less Aaa), weekly from 1962 and monthly from 1919 — the oldest credit
object that exists; (c) REALISED VOLATILITY of the S&P 500, daily from December 1927, which reaches every turn in the
record; (d) the term spread and the TED spread for completeness."""
exec(open('fast49.py').read().split("def full(")[0].replace("out=open('fast49.out','w')","out=open('daily23.out','w')"))
exec(open('daily22.py').read().split('def sc(')[1].split('SPR=dict(')[0].join(['def sc(','']))
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
def inw_(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
P("=== (a) the 0.45 branch look-back, finely ===")
for l45 in [78,91,104,117,130,156,182,208]: sc(f'  0.45 look-back {l45}w',[CRD,SPR],look45=l45)
P("\n=== (b) corporate bond spreads ===")
def sp2(a,b):
    aa=L25(a); bb=L25(b)
    if aa is None or bb is None: return None
    idx=aa.index.union(bb.index); S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna()
    return S[S.index>=max(aa.index.min(),bb.index.min())]
CANDS={}
for nm,a,b in [('Baa-Aaa (weekly)','WBAA','WAAA'),('Baa-10y (weekly)','WBAA','WGS10YR'),('Aaa-10y (weekly)','WAAA','WGS10YR'),
               ('Baa-Aaa (daily)','DBAA','DAAA'),('10y-3m (weekly)','WGS10YR','WTB3MS'),('10y-funds','WGS10YR','FF')]:
    S=sp2(a,b)
    if S is None: P(f"   {nm}: one leg not held"); continue
    CANDS[nm]=S; P(f"   {nm}: {S.index.min().date()} -> {S.index.max().date()}, {len(S)} obs")
BAAf=W.replace('24_bristow_rule_lab/workspace','25_fred_daily_weekly/fred_monthly_select/BAA.csv')
AAAf=W.replace('24_bristow_rule_lab/workspace','25_fred_daily_weekly/fred_monthly_select/AAA.csv')
if os.path.exists(BAAf):
    b_=pd.read_csv(BAAf).iloc[:,:2]; b_.columns=['d','v']; b_['d']=pd.to_datetime(b_['d'])
    a_=pd.read_csv(AAAf).iloc[:,:2]; a_.columns=['d','v']; a_['d']=pd.to_datetime(a_['d'])
    S=(pd.to_numeric(b_.set_index('d')['v'],errors='coerce')-pd.to_numeric(a_.set_index('d')['v'],errors='coerce')).dropna()
    CANDS['Baa-Aaa (monthly, 1919-)']=S; P(f"   Baa-Aaa monthly: {S.index.min().date()} -> {S.index.max().date()}, {len(S)} months")
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw_(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw_(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw_(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw_(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw_(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw_(dd)})
def wseg2(Gx,dd):
    lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0); return Gx[(Gx.index>=lo)&(Gx.index<=hi)]
def screen(nm,S,pub=1):
    per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
    best=[]
    for smw in [1,4,8,13]:
        sm=max(1,int(round(smw*7/per))) if per<20 else 1
        Sm=S.rolling(sm).mean().dropna() if sm>1 else S
        for wmon in [3,6,9,12]:
            win=max(3,int(wmon*30/per)); Gx=(Sm-Sm.rolling(win).min()).dropna()
            segs=[float(wseg2(Gx,dd).max()) for dd in QP if len(wseg2(Gx,dd))]
            if len(segs)<15: continue
            qm=max(segs); rec=[float(wseg2(Gx,PK[i]).max()) for i in range(13) if len(wseg2(Gx,PK[i]))]
            n15=sum(1 for r in rec if r>=qm*1.5)
            if n15>=2: best.append((smw,wmon,round(qm,3),round(qm*1.5,3),n15,Gx))
    P(f"   {nm}: {len(best)} configurations fire in 2+ recessions at 1.5x the highest quiet reading")
    for smw,wmon,qm,ln,n15,Gx in best[:6]:
        sc(f'    {nm} sm{smw}w {wmon}m >= {ln} (1.5x {qm}, {n15}/13)',[CRD,SPR,dict(name='sp2',gap=Gx,line=ln,pub_lag_days=pub)])
for nm,S in CANDS.items(): screen(nm,S,pub=1 if 'monthly' not in nm else 20)
P("\n=== (c) realised volatility of the S&P 500, daily from December 1927 ===")
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
x=pd.read_csv(os.path.join(C25,'other_daily','sp500_daily_yahoo.csv')); x.columns=[c.strip().lower() for c in x.columns]
x[x.columns[0]]=pd.to_datetime(x[x.columns[0]],errors='coerce',utc=True).dt.tz_localize(None)
px=pd.to_numeric(x.set_index(x.columns[0])['close'],errors='coerce').dropna()
r=np.log(px).diff().dropna()
for nd in [21,42,63]:
    vol=(r.rolling(nd).std()*np.sqrt(252)*100).dropna()
    P(f"   realised vol {nd}d: {vol.index.min().date()} -> {vol.index.max().date()}")
    for wmon in [6,12]:
        win=int(wmon*21); Gx=(vol-vol.rolling(win).min()).dropna()
        segs=[float(wseg2(Gx,dd).max()) for dd in QP if len(wseg2(Gx,dd))]
        qm=max(segs); rec=[float(wseg2(Gx,PK[i]).max()) for i in range(13) if len(wseg2(Gx,PK[i]))]
        n15=sum(1 for v in rec if v>=qm*1.5); n12=sum(1 for v in rec if v>=qm*1.2)
        P(f"      {wmon}m rise: quiet max {qm:.1f}, fires {n12}/13 at 1.2x and {n15}/13 at 1.5x")
        if n12>=2: sc(f'    vol{nd}d {wmon}m >= {qm*1.2:.2f}',[CRD,SPR,dict(name='vol',gap=Gx,line=qm*1.2,pub_lag_days=1)])
out.close()
