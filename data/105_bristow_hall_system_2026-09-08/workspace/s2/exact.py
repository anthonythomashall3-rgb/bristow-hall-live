# exact.py: the legs with EXACT ARITHMETIC AT THE LINE (a reading equal to its line fires; 2.3-2.1 is 0.2, not 0.19999999999999973)
EPS=1e-9
def _tenths(x): return (x*10).round(6)/10
def leg_gapL_x(s,line,look,pub=12,rearm='zero'):
    gap=_tenths(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line-EPS: c.append((rel_iu(t),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=EPS: armed=True
            elif rearm=='window' and v<line-EPS and t>=last+pd.DateOffset(months=4): armed=True
    return c
def leg_gapL_cx(s,line,look,band=U_BAND):
    gap=_tenths(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line-EPS:
            day=rel_iu(t)
            if v>=line+band-EPS or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=EPS: armed=True
    return c
def leg_sv_x(line,look=52,pub=12,rearm='zero'):
    gap=_tenths(SI-SI.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line-EPS: c.append((rel_iu(SW[t]),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=EPS: armed=True
            elif rearm=='window' and v<line-EPS and t>=last+pd.DateOffset(months=4): armed=True
    return c
def leg_rt_x(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=_tenths(s-m); c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct-EPS: c.append((rel_iu(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=EPS: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
def leg_br_x(share):
    c=[]; armed=True
    for t,v in BR.items():
        if armed and v>=share-EPS: c.append((rel_state(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<share*0.5: armed=True
    return c
def leg_ic_cx(s,pct,band=IC_BAND,look=52):
    m4=s.rolling(4).mean(); low=m4.rolling(look,min_periods=look).min().shift(1); med=m4.rolling(MED_W,min_periods=156).median().shift(1)
    base=np.maximum(low,ALPHA*med); rel_=(m4/base-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct-EPS:
            day=rel_ic(t)
            if v>=pct+band-EPS or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=EPS: armed=True
    return c
def confirm_wx(calls,confs,mode='month',back=6,fwd=4):
    outc=[]
    for p_,dd in calls:
        best=None
        for cf in confs:
            ser=cf['gap']; seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]
            hit=seg[seg>=cf['line']-EPS]
            if len(hit)==0: continue
            t=hit.index[0]; ps=pubof(cf,t)
            if best is None or ps<best[0]: best=(ps,cf['name'],t)
        if best: outc.append((max(p_,best[0]),dd,best[1]+'@'+best[2].strftime('%Y-%m')))
    return outc
def mkpair_svx(starts,vk,vb,vl,k=3):
    mm=lh.rolling(k).mean(); hh=((lh.rolling(12).max()-mm)/starts)
    G=vgap2(vk,vb); pubsV=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    vr_=(G/vl)
    ev=[(relH[m],'D',m) for m in hh.index if m in relH.index]+[(pubsV[m],'V',m) for m in vr_.index if m in pubsV.index]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastV=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastV=m if (lastV is None or m>lastV) else lastV
        if lastD is None or lastV is None: continue
        v=min(hh.get(lastD,np.nan),vr_.get(lastV,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastV); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0-EPS and key not in fires: fires[key]=d
    Gp=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name='pairSV',gap=Gp,line=1.0,pubs=PB)
# the single-week claims jump with a market crash (SPEED-FRONTIER s5), on the floored base
_SPXd=_SPX.copy(); _crash=(1-_SPXd/_SPXd.rolling(20,min_periods=10).max())*100
def crash_on(day):
    s=_crash[_crash.index<day]; return float(s.iloc[-1]) if len(s) else np.nan   # the last close BEFORE the 8:30 release
def leg_K_x(s,pct,cl,look=52):
    low4=s.rolling(4).mean().rolling(look,min_periods=look).min().shift(1); med=s.rolling(4).mean().rolling(MED_W,min_periods=156).median().shift(1)
    base=np.maximum(low4,ALPHA*med); rel_=(s/base-1)*100; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct-EPS:
            day=rel_ic(t)
            if crash_on(day)>=cl-EPS: c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=EPS: armed=True
    return c
def build_v3(p,sv=False,wide=False,kc=None,exact=True):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    LG=leg_gapL_x if exact else leg_gapL; LGC=leg_gapL_cx if exact else leg_gapL_c; LSV=leg_sv_x if exact else leg_sv; LRT=leg_rt_x if exact else leg_rt; LBR=leg_br_x if exact else leg_br; LIC=leg_ic_cx if exact else leg_ic_c; CW=confirm_wx if exact else confirm_w
    e=EPS if exact else 0.0
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+LRT(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+LRT(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    GS=GSPm if wide else GSP
    SP=dict(name='spread',gap=GS,line=p['spr'],pubs=pd.Series({t:rel_h15(t) for t in GS.index}))
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl-e:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']-e]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']-e
                if ok:
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl-e: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    if sv: C2=C2+[mkpair_svx(p['starts'],p['vk'],p['vb'],p['vl'])]
    legs={'U':[(a,b) for a,b,c in CW(LGC(spl,p['u45'],p['look'])+F45,C1,'month')],
          'L':[(a,b) for a,b,c in CW(LG(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in CW(LIC(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in CW(LSV(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in CW(LSV(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in CW(LBR(p['bshare']),C2,'month')]
    if kc: legs['K']=[(a,b) for a,b in leg_K_x(ICfp,kc[0],kc[1])]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
def report(nm,r,t):
    pk_=[(x['published'].date().isoformat(),x['leg']) for x in t if x['kind']=='peak']
    lags=[r['lags_p'].get(i) for i in range(13)]
    print(f"{nm}: detected {len(r['lags_p'])}/13 others {[(d,lg) for d,_,lg in r['other']]}")
    print('   peaks',pk_); print('   lags',lags,'| early',[x['published'].date().isoformat() for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')])
