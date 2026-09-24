"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('pU.out','w')"))
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
P("is there any 1981 call at all in the causal diary other than the December 1980 one? and can the low branch avoid it?")
P("")
P("the low branch's proposals around the 1980-81 double dip, by line and by re-arm rule")
for low_ in [0.30,0.25,0.20,0.15]:
    for rearm,gapm in [('window',4),('window',6),('window',9),('window',12),('zero',0)]:
        def leg_gapL2(s,line,look,pub=12,rearm='zero',gapm=4):
            gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
            for t,v in gap.items():
                if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
                elif not armed:
                    if rearm=='zero' and v<=0: armed=True
                    elif rearm=='window' and v<line and last is not None and t>=last+pd.DateOffset(months=gapm): armed=True
            return c
        c=leg_gapL2(spl,low_,52,rearm=rearm,gapm=gapm)
        w=[(a,b) for a,b in c if pd.Timestamp('1979-06-01')<=b<=pd.Timestamp('1982-06-01')]
        P(f"   low {low_:4.2f} re-arm {rearm}{gapm if rearm=='window' else ''}: "+", ".join(f"{a:%Y-%m-%d}/{b:%Y-%m}" for a,b in w))
P("")
P("the paper spread through the double dip, and how much smoothing would remove the December 1980 reading of 1.118")
raw=GSP
for m in pd.date_range('1980-09-01','1981-04-01',freq='MS'):
    seg=raw[(raw.index>=m)&(raw.index<m+pd.DateOffset(months=1))]
    P(f"   {m:%Y-%m}  smoothed spread max {seg.max():.3f}  days at or above 1.100: {int((seg>=1.1).sum())} of {len(seg)}")
out.close()
