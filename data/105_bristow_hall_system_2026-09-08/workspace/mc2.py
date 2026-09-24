"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('mc2.out','w')"))
def build_v(p):
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
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
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
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
BASE39=dict(BASE); BASE39.update(deep=999,wline=0.30,wline2=0.60,bshare=0.50,hline=0.95,spr=1.1,sahm=0.3667,vl=0.20,hback=5)
def full(nm,p,TL):
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
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[x for x in turns if x['kind']=='peak' and x['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']] and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))]
    trow=[]; prem=0; badc=0
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days; trow.append(lag)
            if lag<0: prem+=1
    badc=len([x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))])
    v=[x for x in lp if x is not None]
    P(f"{nm:34s} peaks {len(v)}/13 within {sum(1 for x in v if x<=31)}/13 FA {len(fa)} | troughs {len(trow)}/13 median {np.median(trow) if trow else 0:.0f} premature {prem} outside {badc}")
    P(f"     onsets {lp}")
    return turns
CL=ICfp.dropna().rolling(4).mean().dropna(); LCL=np.log(CL); BELOW=(LCL.rolling(52,min_periods=26).max()-LCL).dropna()
sys.path.insert(0,W+'/lab/slack')
LHs=lh.dropna(); AWs=AWH.dropna()
def rel_low(ser,look=12): return ((ser/ser.rolling(look,min_periods=look).min()-1)*100).dropna()
RS=rel_low(LHs); RH=rel_low(AWs)
def confirm_close(calls,cdrop,rise,pubday_starts=18,pubday_hours=5,fwd=6,need=1):
    """S (and any other closer) proposes; a second object confirms that the labour market has actually turned:
    the claims four-week mean is `cdrop` log points below its own 52-week maximum, or housing starts / weekly hours
    stand `rise` per cent above their own twelve-month low. The confirmation carries its own publication date."""
    out_=[]
    for pp,dd in calls:
        hits=[]
        seg=BELOW[(BELOW.index>=dd)&(BELOW.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(h.index[0]+pd.Timedelta(days=5))
        for rl,pdy in [(RS,pubday_starts),(RH,pubday_hours)]:
            s2=rl[(rl.index>=dd)&(rl.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2): hits.append(pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1))
        if len(hits)>=need:
            hits.sort(); out_.append((max(pp,hits[need-1]),dd))
    return out_
def full4(nm,p,TL,nvac=1):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back,nv):
        """the vacancy must stand at or above its line in at least nv months of the window. A line touched in one
        month is not a confirmation - the same rule the spread needs, applied to the object the hub depends on."""
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit)>=nv:
                    kk=hit.index[nv-1]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'],nvac)],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[f"{x['published']:%Y-%m-%d}" for x in turns if x['kind']=='peak' and x['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']] and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))]
    late=[f"{x['published']:%Y-%m-%d}/{x['date']:%Y-%m}/{x['leg']}" for x in turns if x['kind']=='peak' and x['published']>=pd.Timestamp('2025-01-01')]
    v=[x for x in lp if x is not None]
    P(f"{nm:40s} peaks {len(v)}/13 within {sum(1 for x in v if x<=31)}/13 FA {len(fa)}{fa if fa else ''} | 2024 lag {lp[12]} | calls after 2025: {late}")
    P(f"     {lp}")
_CLx=ICfp.dropna().rolling(4).mean().dropna(); BELOWc=(np.log(_CLx).rolling(52,min_periods=26).max()-np.log(_CLx)).dropna()
_LHx=lh.dropna(); _AWx=AWH.dropna()
RSc=((_LHx/_LHx.rolling(12,min_periods=12).min()-1)*100).dropna(); RHc=((_AWx/_AWx.rolling(12,min_periods=12).min()-1)*100).dropna()
CLmin=max(BELOWc.index.min(),RSc.index.min(),RHc.index.min())
FH=pd.read_csv(W+'/lab/fh/FH_nat_sa_rt.csv',index_col=0,parse_dates=True)
icm=np.log(FH['initial claims'].dropna()); ccm=np.log(FH['continued weeks claimed'].dropna())
def pub10(p_): return pd.Timestamp(p_.year,p_.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
def mkH(h): return [(pub10(p_-pd.DateOffset(months=1)),d) for p_,d in B.level_trough_calls(icm,drop=h)]
def mkJ(j): return [(pub10(p_-pd.DateOffset(months=1)),d) for p_,d in B.level_trough_calls(ccm,drop=j)]
START_CONF=max(_BELOW.index.min() if False else CLmin, pd.Timestamp('1967-01-01'))
def confirm_close2(calls,cdrop,rise,need,fwd=6):
    """as confirm_close, but a call dated before the confirming objects exist passes through unconfirmed. Rule 23
    clause 3: an object may only be required from the date it existed."""
    out_=[]
    for pp,dd in calls:
        if dd<START_CONF: out_.append((pp,dd)); continue
        hits=[]
        seg=BELOWc[(BELOWc.index>=dd)&(BELOWc.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(h.index[0]+pd.Timedelta(days=5))
        for rl_,pdy in [(RSc,18),(RHc,5)]:
            s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2): hits.append(pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1))
        if len(hits)>=need:
            hits.sort(); out_.append((max(pp,hits[need-1]),dd))
    return out_
def trow(nm,TL):
    p=dict(BASE39); p['hback']=5
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
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
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[f"{x['published']:%Y-%m-%d}" for x in turns if x['kind']=='peak' and x['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']] and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))]
    rows=[]; prem=0
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c:
            lag=(c[0]['published']-me(TR[i])).days; rows.append((i,lag,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month))
            if lag<0: prem+=1
    outc=len([x for x in turns if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))])
    lg=[x[1] for x in rows]; er=[x[2] for x in rows]; v=[x for x in lp if x is not None]
    P(f"{nm:44s} troughs {len(rows):2d}/13 med {np.median(lg) if lg else 0:5.0f} mean {np.mean(lg) if lg else 0:5.0f} worst {max(lg) if lg else 0:4d} exact {sum(1 for e in er if e==0):2d} w31 {sum(1 for x in lg if 0<=x<=31):2d} prem {prem} outside {outc} | peaks {len(v)}/13 FA {len(fa)}")

import importlib.util
spec=importlib.util.spec_from_file_location('_bt',W+'/lab/_bt.py'); _bt=importlib.util.module_from_spec(spec)
try: spec.loader.exec_module(_bt); HAVE=True
except Exception as e: P('could not load the lab rule directly: %s'%e); HAVE=False
def ch_trough_local(level,w0,w1,band=0.02,n=3,L=12):
    """the Bristow rule's own trough dater, written out here so it can be run in an expanding window rather than a
    window that already knows where the episode ends"""
    lv=level.rolling(n).mean().dropna() if n>1 else level
    d=(lv-lv.rolling(L).mean()).dropna()
    d=d[(d.index>=w0)&(d.index<=w1)]
    if not len(d): return None
    d_peak=d.idxmax()
    m=lv[(lv.index>=w0)&(lv.index<=w1)]
    if len(m)<4: return d_peak
    lo=float(m.min()); i=m.idxmin()
    if i==m.index[-1]: return None            # still at its low: it has not turned
    hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
    amp=max(hi-lo,1e-9)
    on=m[m<=lo+band*amp]
    return max(d_peak,on.index[-1]) if len(on) else d_peak
sys.path.insert(0,W+'/lab/slack')
LVL={'the unemployment rate, inverted':-UR.dropna(),
     'aggregate weekly hours':AWH.dropna(),
     'housing starts':lh.dropna(),
     'the insured rate, inverted':-spl.dropna()}
REL={'the unemployment rate, inverted':(lambda m: rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))),
     'aggregate weekly hours':(lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)),
     'housing starts':(lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)),
     'the insured rate, inverted':(lambda m: pd.Timestamp(m.year,m.month,1)+pd.Timedelta(days=11))}
def bristow_closer(nm,band,n,L,stable,lead=9,back=36):
    """THE BRISTOW RULE RUN IN REAL TIME. At the end of every month the rule is applied to everything published so far,
    from nine months before the tool opened to the latest month on the file. When it returns the SAME trough date in
    `stable` consecutive months, the episode is closed at that date, published on the release day of the month that
    settled it."""
    lv=LVL[nm]; pub=REL[nm]
    out_=[]; hist={}
    months=[m for m in lv.index if m>=pd.Timestamp('1948-01-01')]
    run=None; runlen=0
    for k,m in enumerate(months):
        w1=m; w0=m-pd.DateOffset(months=back)
        dt=ch_trough_local(lv[lv.index<=m],w0,w1,band,n,L)
        if dt is not None and run is not None and dt==run: runlen+=1
        else: run=dt; runlen=1 if dt is not None else 0
        if dt is not None and runlen>=stable:
            out_.append((pub(m),pd.Timestamp(dt.year,dt.month,1))); run=None; runlen=0
    # keep the first call for each dated month
    seen=set(); res=[]
    for p_,d_ in out_:
        if d_ in seen: continue
        seen.add(d_); res.append((p_,d_))
    return res
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
def bristow_weekly(band=0.02,n=4,L=52,stable=3,back_w=156,pub=5):
    """THE SETTLING TEST ON THE WEEKLY SERIES. The insured rate is published weekly, five days after the week ends,
    so a settling test run on the weekly series can settle a month or more before the same test on the monthly one."""
    lv=(-IURW).rolling(n).mean().dropna()
    out_=[]; run=None; runlen=0; seen=set()
    idx=list(lv.index)
    for k,t in enumerate(idx):
        if k<back_w//4: continue
        w=lv[(lv.index>t-pd.Timedelta(weeks=back_w))&(lv.index<=t)]
        if len(w)<8: continue
        d=(w-w.rolling(L).mean()).dropna()
        if not len(d): continue
        dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
        if i==w.index[-1]: run=None; runlen=0; continue
        hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
        amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
        dt=max(dp,on.index[-1]) if len(on) else dp
        m=pd.Timestamp(dt.year,dt.month,1)
        if run==m: runlen+=1
        else: run=m; runlen=1
        if runlen>=stable and m not in seen:
            seen.add(m); out_.append((t+pd.Timedelta(days=pub),m))
    return out_
LVL['the survey-week insured rate, inverted']=-SI
REL['the survey-week insured rate, inverted']=(lambda m: SW[m]+pd.Timedelta(days=12) if m in SW.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=11))
def detail(nm,TL):
    p=dict(BASE39); p['hback']=5
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
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
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')],
          'W':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')],
          'V':[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')],
          'B':[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    P(f"\n{nm}")
    for i in range(13):
        c=[x for x in turns if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c: P(f"   {TR[i]:%Y-%m}  closed {c[0]['published']:%Y-%m-%d}  dated {c[0]['date']:%Y-%m}  lag {(c[0]['published']-me(TR[i])).days:+5d}  err {((c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month):+d}  by {c[0]['leg']}")

S2=confirm_close(TLG['S'],0.15,2.0,need=2)

# ------------------------------------------------------------------ THE REAL BRISTOW RULE: MANY CHANNELS, ONE MEDIAN
# Paper 1 does not date a turn on one series. It runs the rule on every channel and takes an order statistic of the
# channel dates - the median, or a higher quantile, which is what a committee does when it waits for the slower
# channels to confirm. Everything tried so far ran the rule on ONE channel and then bolted a confirmation onto it.
# The median across channels IS the confirmation, and it is the method the programme already owns.
_CLm=ICfp.dropna().resample('MS').mean()
_CCm=pd.read_csv(D+'/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna().resample('MS').mean()
_SPm=GSP.resample('MS').mean()
CH={'insured rate':(-spl.dropna(),11),'unemployment rate':(-UR.dropna(),5),'weekly hours':(AWH.dropna(),5),
    'housing starts':(lh.dropna(),17),'initial claims':(-_CLm,5),'continued claims':(-_CCm,5),
    'vacancy rate':((-_vload()['-vacancy rate']).dropna(),30),'paper spread':(-_SPm,1)}
def _pub(nm,m):
    d=CH[nm][1]
    return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=d-1)
def ch_date(lv,w0,w1,band,n,L):
    w=lv[(lv.index>=w0)&(lv.index<=w1)]
    if len(w)<8: return None
    d=(w-w.rolling(L).mean()).dropna()
    if not len(d): return None
    dp=d.idxmax(); lo=float(w.min()); i=w.idxmin()
    if i==w.index[-1]: return None
    hi=float(w[:i].max()) if len(w[:i]) else float(w.max())
    amp=max(hi-lo,1e-9); on=w[w<=lo+band*amp]
    return max(dp,on.index[-1]) if len(on) else dp
def med_q(ds,q):
    s=sorted(ds)
    if not s: return None
    import math
    k=max(0,min(len(s)-1,math.ceil(q*len(s))-1))
    return s[k]
def multichannel_closer(band=0.02,n=3,L=12,stable=3,back=48,q=0.5,minch=3):
    """at the end of every month the rule is run on every channel that has reported, the channel dates are collected
    and the q-th order statistic taken; when that date repeats for `stable` months the episode is closed at it,
    published on the latest release date the median needed"""
    SM={nm:(lv.rolling(n).mean().dropna(),d) for nm,(lv,d) in CH.items()}
    months=pd.date_range('1948-01-01','2026-08-01',freq='MS')
    out_=[]; run=None; runlen=0; seen=set(); runpub=None
    for m in months:
        ds=[]; pubs=[]
        for nm,(lv,d) in SM.items():
            avail=lv[lv.index<=m-pd.DateOffset(months=1)]      # month m-1 is what has been published by month m
            if not len(avail): continue
            dt=ch_date(avail,m-pd.DateOffset(months=back),avail.index[-1],band,n,L)
            if dt is not None: ds.append(dt); pubs.append(_pub(nm,avail.index[-1]))
        if len(ds)<minch: run=None; runlen=0; continue
        dt=med_q(ds,q); mm=pd.Timestamp(dt.year,dt.month,1)
        # the call is published when the channels the order statistic actually needs have reported, not when the
        # slowest channel in the panel has: the median of eight channels does not wait on the eighth
        import math
        need=max(1,min(len(ds),math.ceil(q*len(ds))))
        pub=sorted(pubs)[need-1]
        if run==mm: runlen+=1
        else: run=mm; runlen=1; runpub=pub
        if runlen>=stable and mm not in seen:
            seen.add(mm); out_.append((pub,mm))
    return out_
P("THE ORDER STATISTIC LOWERED, AND PUBLISHED WHEN THE CHANNELS IT NEEDS HAVE REPORTED")
P("The median waits for half the panel and for the slowest channel in it. Neither is necessary: a lower quantile")
P("dates the turn on the channels that have already turned, and the call can be published as soon as those have")
P("reported rather than when the vacancy rate arrives thirty days later.")
S2=confirm_close(TLG['S'],0.15,2.0,need=2)
trow('  shipped closers, S rebuilt',{**TLH,'S':S2})
trow('  the single-channel settling test, 48m/3m/2conf',{**TLH,'S':S2,'R':confirm_close2(bristow_closer('the insured rate, inverted',0.02,3,12,3,back=48),0.10,2.0,2)})
import itertools
for q,stable,back in itertools.product([0.25,0.3,0.4,0.5],[3,4,5,6],[36,48]):
    c=multichannel_closer(stable=stable,back=back,q=q)
    if not c: continue
    trow(f'  q={q}, settles {stable}m, window {back}m ({len(c)} calls)',{**TLH,'S':S2,'R':c})
out.close()
