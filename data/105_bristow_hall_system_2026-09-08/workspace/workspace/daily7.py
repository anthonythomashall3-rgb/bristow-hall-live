"""The one economically motivated survivor of the 15,128-file sweep — a large RISE in the short rate (monetary
tightening) as a demand-side confirmer — examined properly: margins, plateau, exposure, DATE ERRORS, and the turns it
buys. Plus the negatives worth recording (S&P 500, the ADS index, carloadings, the Philadelphia survey) and Anthony's
2024 dating question."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily7.out','w')"))
import glob,pickle
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
    return None
CS=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CS-CS.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
def wseg(G,dd,back=6,fwd=4):
    lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0); return G[(G.index>=lo)&(G.index<=hi)]
def go9e(nm,extra,pct=50,vk=4,vb=4,vl=0.20,starts=29,hubline=0.50):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(starts,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=vl]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline)
        I=confirm_w(leg_ic(ics,pct),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; ep=[res[0]['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:34s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} |err|>1 {sum(1 for e in ep if e is not None and abs(e)>1)} others {[o[1] for r in res for o in r['other']][:4]}")
    return ok,np.mean(av),ep
P("=== 1. baseline ==="); go9e('v3.1 (credit 1.25)',[CRED])
P("\n=== 2. the short-rate RISE object: what it is, and its margins ===")
for nm in ['DFF','RIFSPFFNB','FF']:
    s=L25(nm)
    if s is None: P(f"   {nm}: not held"); continue
    P(f"   {nm}: {s.index.min().date()} -> {s.index.max().date()}, {len(s)} obs, median step {float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))):.0f}d")
DFF=L25('DFF'); G6=(DFF-DFF.rolling(180).min()).dropna()
qs=sorted([(float(wseg(G6,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(G6,dd))],reverse=True)
P("   highest reading inside a QUIET proposal window:",[(round(a,2),b) for a,b in qs[:6]])
P("   recession-window maxima:",[(PK[i].strftime('%Y-%m'),round(float(wseg(G6,PK[i]).max()),2) if len(wseg(G6,PK[i])) else None) for i in range(13)])
P("   2025-26 maximum:",round(float(G6[G6.index>=pd.Timestamp('2025-01-01')].max()),3))
P("   share of ALL months at or above 6.2934:",round(float((G6.resample('MS').max()>=6.2934).mean())*100,2),"per cent")
P("\n=== 3. plateau and window ===")
for win,lines in [(90,[3.0,4.0,5.0,6.0]),(180,[5.0,5.5,6.0,6.2934,7.0,8.0]),(360,[6.0,7.0,8.0,9.0])]:
    Gw=(DFF-DFF.rolling(win).min()).dropna()
    qm_=max([float(wseg(Gw,dd).max()) for dd in QP if len(wseg(Gw,dd))]+[-9e9])
    P(f"   window {win} trading days: construction-grade line {qm_*1.02:.4f}")
    for ln in lines: go9e(f"  DFF rise{win} >= {ln}",[CRED,dict(name='dff',gap=Gw,line=ln,pub_lag_days=1)])
P("\n=== 4. Anthony's 2024 question: relax the dating, what does it buy ===")
for hl in [0.50,0.47,0.45,0.43]: go9e(f"  hub line {hl}",[CRED],hubline=hl)
P("\n=== 5. the negatives worth recording ===")
def diag(nm,s,wins=(90,180,360)):
    for win in wins:
        for kind in ['fall','rise']:
            G=((s.rolling(win).max()-s) if kind=='fall' else (s-s.rolling(win).min())).dropna()
            if len(G)<300: continue
            qq=sorted([(float(wseg(G,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(G,dd))],reverse=True)
            rr=[float(wseg(G,PK[i]).max()) for i in range(13) if len(wseg(G,PK[i]))]
            if not qq: continue
            n=sum(1 for r in rr if r>=qq[0][0]*1.02)
            P(f"   {nm} {kind} {win}: quiet max {qq[0][0]:.2f} ({qq[0][1]}); construction line {qq[0][0]*1.02:.2f} fires in {n}/13 recessions")
x=pd.read_csv(os.path.join(C25,'other_daily','sp500_daily_yahoo.csv')); x.columns=[c.strip().lower() for c in x.columns]
x[x.columns[0]]=pd.to_datetime(x[x.columns[0]],errors='coerce',utc=True).dt.tz_localize(None)
sp=np.log(pd.to_numeric(x.set_index(x.columns[0])['close'],errors='coerce').dropna())*100
P(f"   S&P 500 daily {sp.index.min().date()} -> {sp.index.max().date()}"); diag('SP500',sp)
ads=pd.read_csv(os.path.join(C25,'other_daily','ads_index_current.csv')); ads.columns=[c.strip().lower() for c in ads.columns]
ads[ads.columns[0]]=pd.to_datetime(ads[ads.columns[0]],errors='coerce'); a=pd.to_numeric(ads.set_index(ads.columns[0]).iloc[:,0],errors='coerce').dropna()
P(f"   ADS index daily {a.index.min().date()} -> {a.index.max().date()}"); diag('ADS',a)
out.close()
