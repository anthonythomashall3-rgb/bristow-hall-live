"""THE LAST TWO DOORS. 1960 (+91) waits on the vacancy for June 1960, published 30 July — so the only thing that can
move it is the vacancy object's own SHAPE reaching its line a month or two earlier. 1981 (+55) waits on the low
branch's own crossing week — so the only thing that can move it is a faster proposal in 1981, and the Department's
first-print weekly rate runs to April 1983. Both swept here against the current object set."""
exec(open('daily19.py').read().split('P("=== what the 30 per cent leg does to 1948 ===")')[0].replace("out=open('daily19.out','w')","out=open('daily21.out','w')"))
G=obj(CPB,13,6); SPR=dict(name='cpb',gap=G,line=1.20,pub_lag_days=1)
def go9v(nm,extra,x45=None,x25=None,vk=4,vb=4,vl=0.20,hubline=0.50,rt45=0.45,rt25=0.25,rtstop='1971-01-01'):
    G_=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G_.index})
    Vc=dict(name='vac',gap=G_,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,rt45,stop=rtstop)+(x45 or [])
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,rt25,stop=rtstop)+(x25 or [])
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G_[(G_.index>=m-pd.DateOffset(months=6))&(G_.index<=m)]; hit=w[w>=vl]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:38s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY '+str(len(early)) if early else ''}")
    return ok
P("=== baseline ==="); go9v('v3.2 + paper spread',[CRED,SPR])
P("\n=== 1960: the vacancy object's shape re-swept against the current object set ===")
for vk in [1,2,3,4,6]:
    for vb in [2,3,4,6,9]:
        for vl in [0.15,0.20,0.25,0.30,0.36]:
            go9v(f'  vacancy ({vk},{vb}) @ {vl}',[CRED,SPR],vk=vk,vb=vb,vl=vl)
P("\n=== 1981: the first-print weekly rate carried to April 1983, at higher lines ===")
for a,c in [(0.45,0.25),(0.60,0.35),(0.75,0.45),(1.00,0.60),(1.25,0.75),(1.50,0.90)]:
    go9v(f'  rt to 1983 at {a}/{c}',[CRED,SPR],rt45=a,rt25=c,rtstop='1984-01-01')
out.close()
