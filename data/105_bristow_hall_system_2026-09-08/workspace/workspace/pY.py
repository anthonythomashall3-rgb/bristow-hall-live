"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('pY.out','w')"))
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
FH=pd.read_csv(W+'/lab/fh/FH_nat_sa_rt.csv',index_col=0,parse_dates=True)
icm=np.log(FH['initial claims'].dropna()); ccm=np.log(FH['continued weeks claimed'].dropna())
def pub10(p_): return pd.Timestamp(p_.year,p_.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
def mkH(h): return [(pub10(p_-pd.DateOffset(months=1)),d) for p_,d in B.level_trough_calls(icm,drop=h)]
def mkJ(j): return [(pub10(p_-pd.DateOffset(months=1)),d) for p_,d in B.level_trough_calls(ccm,drop=j)]
P("THE CLOSERS REBUILT THE WAY S WAS: each proposes the close, two objects confirm the labour market has turned.")
P("H and K are the workhorses - H closes seven of the thirteen - and their drops have never been loosened because")
P("loosening them alone closes early. With the confirmation in place the drop can come down.")
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
S2=confirm_close(TLG['S'],0.15,2.0,need=2)
trow('  the shipped closers with S rebuilt',{**TLH,'S':S2})
import itertools
for h,j,need in itertools.product([8.0,6.0,5.0,4.0,3.0],[5.0,4.0,3.0],[2,3]):
    TL={'K':TLH['K'],'S':S2,'H':confirm_close(mkH(h),0.15,2.0,need=need),'J':confirm_close(mkJ(j),0.15,2.0,need=need)}
    trow(f'  H drop {h}, J drop {j}, {need} confirmations',TL)
out.close()
