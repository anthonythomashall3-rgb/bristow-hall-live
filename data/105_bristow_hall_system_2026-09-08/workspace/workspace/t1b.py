"""STEP 1b — CLOSER C: the flow proposes, the stock or the market confirms.
Read off the pause-and-trough table (t1a): at every trough of the main sample initial claims' four-week mean had fallen
from the episode's peak for three or more weeks running, and so it had at four of the five mid-episode pauses. What the
pauses never had, and every trough did, was a CONFIRMATION of a different kind: the stock of insured unemployment
(continued claims, or the insured rate) had turned down, or the equity market stood well above its own six-month low.
C fires when the flow's fall is confirmed the same week by either. It dates the trough at the month the flow peaked
plus a declared offset (the flow leads the trough by a month at the median), and it may not announce a month before
that month has ended. Everything here is frozen; the walk comes after the screen."""
import sys, io, contextlib, itertools
MA=sys.argv[1] if len(sys.argv)>1 else '4'
HA=sys.argv[2] if len(sys.argv)>2 else 'next'
sys.argv=['x','2011','2012','wt1b']
src=open('walk26.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import pandas as pd, numpy as np
OUT=open(f'out/t1b_m{MA}_{HA}.txt','w')
def P(*a):
    print(*a); print(*a,file=OUT); OUT.flush()
# ---------------- the objects
IC4=ICfp.dropna().rolling(int(MA)).mean().dropna()      # the flow's m-week mean
LIC=np.log(IC4)*100
LIC4=np.log(ICfp.dropna().rolling(4).mean().dropna())*100   # the four-week mean, for dating
CC=pd.read_csv(W+'/lab/data/fred_weekly/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
LCC=np.log(CC.rolling(4).mean().dropna())*100
IUR=frd.dropna()                                                 # IURSA, weekly, 1971 on (current file: no vintage exists)
SPX=pd.read_csv(W+'/lab/speed2/data/sp500_daily_yahoo.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
SP26=(SPX/SPX.rolling(130,min_periods=60).min()-1)*100           # daily: per cent above the lowest close of the previous 26 weeks
def spike_drop(L,back=26,look=52):
    """drop from the maximum of the previous `back` weeks (the current hump's top), the hump's amplitude above the trailing
    `look`-week minimum, and the run of falling weeks"""
    mx=L.rolling(back,min_periods=8).max(); mn=L.rolling(look,min_periods=look//2).min()
    df=pd.concat([L.rename('n'),mx.rename('x'),mn.rename('m')],axis=1).dropna()
    n=df['n'].values; run=np.zeros(len(n),int); fall=0
    for i in range(1,len(n)):
        fall=fall+1 if n[i]<n[i-1] else 0; run[i]=fall
    return pd.DataFrame({'drop':df['x'].values-n,'amp':df['x'].values-df['m'].values,'run':run},index=df.index)
FI=spike_drop(LIC); FC=spike_drop(LCC)
# insured-rate drop in exact tenths from its own spike maximum (same restart rule)
def iur_drop(s,back=26):
    """the insured rate's four-week mean, in tenths, below the maximum of the previous `back` weeks"""
    t=(s.rolling(4).mean()*10).round(); mx=t.rolling(back,min_periods=8).max(); return (mx-t).dropna()
DU=iur_drop(IUR)
def ic_peak_month(t,back=26):
    """the flow's peak month as of week t: the later of the months in which the m-week and the four-week means peaked
    over the previous `back` weeks (a peak robust to the smoothing length)"""
    seg=LIC[(LIC.index<=t)&(LIC.index>t-pd.Timedelta(weeks=back))]; a=seg.idxmax()
    seg4=LIC4[(LIC4.index<=t)&(LIC4.index>t-pd.Timedelta(weeks=back))]; b=seg4.idxmax() if len(seg4) else a
    return max(a,b)
# precomputed per week, so a configuration is a mask
_W=FI.index
_pI=_W+pd.Timedelta(days=5)
_sp=SP26.reindex(_pI,method='ffill').values
_tc=_W-pd.Timedelta(days=7)
_fc=FC['drop'].reindex(_tc).values; _du=DU.reindex(_tc).values.astype(float)
_pk={}
def _peak(t):
    if t not in _pk: _pk[t]=ic_peak_month(t)
    return _pk[t]
def closer_C(D=6.0,n=4,A=20.0,s=20.0,c=1.5,u=2,need=1,k=1,pub_ic=5,pub_cc=12,cool=26):
    """calls (published, dated). Proposer: IC4 drop>=D log points from the spike's maximum with amplitude>=A, falling n
    weeks running. Confirmers, counted the same week: S&P >= s per cent above its 26-week low on the day of the claims
    release; continued claims' four-week mean >= c below its own spike maximum (public 12 days after its week);
    the insured rate >= u tenths below its own spike maximum (12 days). `need` of the three. Dated the flow's peak month
    plus k; published at the later of the proposer's and the confirmers' dates and never before the dated month ends."""
    prop=(FI['drop'].values>=D)&(FI['amp'].values>=A)&(FI['run'].values>=n)
    hs=(np.nan_to_num(_sp,nan=-99)>=s).astype(int)+(np.nan_to_num(_fc,nan=-99)>=c).astype(int)+(np.nan_to_num(_du,nan=-99)>=u).astype(int)
    ok=np.where(prop&(hs>=need))[0]
    calls=[]; last=None
    for i in ok:
        t=_W[i]
        if last is not None and t<last+pd.Timedelta(weeks=cool): continue
        pI=_pI[i]; hits=[]
        if np.nan_to_num(_sp[i],nan=-99)>=s: hits.append(pI)
        if np.nan_to_num(_fc[i],nan=-99)>=c: hits.append(_tc[i]+pd.Timedelta(days=pub_cc))
        if np.nan_to_num(_du[i],nan=-99)>=u: hits.append(_tc[i]+pd.Timedelta(days=pub_cc))
        hits.sort(); pub=max(pI,hits[need-1])
        pm=_peak(t); dated=pd.Timestamp(pm.year,pm.month,1)+pd.DateOffset(months=k)
        # the stock's own peak dates the trough where the stock has already turned: the trough is the later of the
        # flow's peak plus the offset and the month continued claims peaked
        if np.nan_to_num(_fc[i],nan=-99)>=c:
            seg=LCC[(LCC.index<=_tc[i])&(LCC.index>_tc[i]-pd.Timedelta(weeks=26))]
            if len(seg):
                cm=seg.idxmax(); cmm=pd.Timestamp(cm.year,cm.month,1)
                if cmm>dated: dated=cmm
        hold=dated+pd.offsets.MonthEnd(0)+(pd.Timedelta(days=1) if HA=='next' else pd.Timedelta(days=0))
        pub=max(pub,hold)
        calls.append((pub,dated)); last=t
    return calls
# ---------------- the screen: C on the menu beside v3.20's closers, frozen at the configuration the walk ended on
import pickle
CFG=pickle.load(open('cache/w26_carry.pkl','rb'))   # the configuration the v3.20 walk ended on: the fast opens
def run_with(C):
    TL=dict(TLH); TL['R']=RC[CFG['rst']]; TL['T']=TC[CFG['tst']]; TL['Q']=QC[CFG['qst']]; TL['C']=C
    p=dict(CFG)
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit)>=2:
                    kk=hit.index[1]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return turns
def score_troughs(turns,start=pd.Timestamp('1961-11-03')):
    """the diary scorer's trough rule, applied to the frozen chronology: each close matched to the trough whose window
    [T-6m, T+12m] holds its date; premature if published before the trough month ended; the episode's own close is the
    first trough call after the peak call that opened it"""
    pk=[t for t in turns if t['kind']=='peak' and t['published']>=start]
    res={}; bad=[]
    for j,x in enumerate(turns):
        if x['kind']!='peak' or x['published']<start: continue
        nxt=next((y for y in turns[j+1:] if y['kind']=='trough'),None)
        if nxt is None: continue
        hit=[i for i in range(13) if abs((x['date'].year-PK[i].year)*12+(x['date'].month-PK[i].month))<=9]
        if not hit: continue
        i=hit[0]; lag=(nxt['published']-me(TR[i])).days; err=(nxt['date'].year-TR[i].year)*12+nxt['date'].month-TR[i].month
        res[i]=(nxt['published'],nxt['date'],nxt['leg'],lag,err)
        if lag<-31: bad.append((TR[i].strftime('%Y-%m'),'PREMATURE',lag,nxt['leg']))
        if abs(err)>1 and nxt['leg']=='C': bad.append((TR[i].strftime('%Y-%m'),'DATE',err))
    fa=[(t['published'].strftime('%Y-%m-%d'),t['date'].strftime('%Y-%m')) for t in pk
        if not any(PK[i]-pd.DateOffset(months=6)<=t['date']<=TR[i] for i in range(13))]
    return res,bad,fa,len(pk)
base=run_with([])
r0,b0,fa0,npk0=score_troughs(base)
P("walk-end configuration",{k:v for k,v in CFG.items()})
P("frozen at the walk-end configuration, v3.20 closers only: peaks called",npk0,"false",fa0)
P("   troughs:",{TR[i].strftime('%Y-%m'):(v[2],v[3],v[4]) for i,v in r0.items()},"bad",b0)
GRID=dict(D=[8,6,5,4,3],n=[4,3,2],A=[20],s=[30,25,20,15,12],c=[3.0,2.0,1.5],u=[3],need=[1],k=[1])
P(f"\nmean length {MA} weeks, hold convention {HA}\nconfig | closes | lags | within31 | exact | within1 | premature/date-bad | C used at")
rows=[]
for D,n,A,s,c,u,need,k in itertools.product(GRID['D'],GRID['n'],GRID['A'],GRID['s'],GRID['c'],GRID['u'],GRID['need'],GRID['k']):
    C=closer_C(D=D,n=n,A=A,s=s,c=c,u=u,need=need,k=k)
    turns=run_with(C); r,bad,fa,npk=score_troughs(turns)
    lags=[v[3] for i,v in sorted(r.items()) if i>=4]; errs=[v[4] for i,v in sorted(r.items()) if i>=4]
    used=[TR[i].strftime('%Y-%m') for i,v in r.items() if v[2]=='C']
    rows.append((D,n,A,s,c,u,need,k,len(lags),sorted(lags),sum(1 for l in lags if l<=31),sum(1 for e in errs if e==0),sum(1 for e in errs if abs(e)<=1),bad,fa,npk,used))
clean=[x for x in rows if not x[13] and not x[14] and x[15]==npk0 and x[8]==9]
clean.sort(key=lambda x:(sum(1 for l in x[9] if l>31 or l<-31),-x[10],-x[11],np.median([abs(l) for l in x[9]])))
P(f"configurations {len(rows)}; clean on the main sample (nine closes, none premature, none dated more than a month out, peak side unchanged) {len(clean)}")
for x in clean[:60]:
    P(f"D{x[0]} n{x[1]} A{x[2]} s{x[3]} c{x[4]} u{x[5]} need{x[6]} k{x[7]} | {x[8]} | {x[9]} | in+-31 {sum(1 for l in x[9] if -31<=l<=31)} in[0,31] {x[10]} | exact {x[11]} within1 {x[12]} | C at {x[16]}")
P("\nper-trough detail of the top ten:")
for x in clean[:10]:
    C=closer_C(D=x[0],n=x[1],A=x[2],s=x[3],c=x[4],u=x[5],need=x[6],k=x[7]); r,bad,fa,npk=score_troughs(run_with(C))
    P(f"D{x[0]} n{x[1]} s{x[3]} c{x[4]} u{x[5]}: "+"  ".join(f"{TR[i]:%Y-%m}:{v[2]} {v[0]:%Y-%m-%d} d{v[1]:%Y-%m} {v[3]:+d}/{v[4]:+d}" for i,v in sorted(r.items()) if i>=4))
P("\nthe fastest UNCLEAN ones, with the reason:")
dirty=[x for x in rows if x[13] or x[14] or x[15]!=npk0 or x[8]!=9]
dirty.sort(key=lambda x:(-x[10],np.median(x[9]) if x[9] else 999))
for x in dirty[:25]:
    P(f"D{x[0]} n{x[1]} A{x[2]} s{x[3]} c{x[4]} u{x[5]} need{x[6]} k{x[7]} | {x[8]} | {x[9]} | w31 {x[10]} | {x[13]} {x[14]} peaks {x[15]}")
import pickle; pickle.dump(rows,open(f'out/t1b_rows_m{MA}_{HA}.pkl','wb'))
OUT.close()
