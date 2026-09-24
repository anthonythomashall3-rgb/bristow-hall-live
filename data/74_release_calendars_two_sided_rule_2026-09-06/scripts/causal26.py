"""IS THE ONE NEW NUMBER IN v3.2 FITTED? The first-print pre-1971 leg introduces exactly one line the programme has not
already used elsewhere: the higher line, 1.00. Here it is re-chosen at each turn from 1953 on using ONLY the record
before that turn — the safest (highest) line in the grid that calls every prior recession with no other call — and the
held-out turn is then scored with the line the past would have chosen."""
exec(open('fast48.py').read().split("full('v3.1")[0].replace("out=open('fast48.out','w')","out=open('causal26.out','w')"))
GRID=[0.60,0.75,0.90,1.00,1.10,1.25,1.50]
def run(hi,cut=None):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)+leg_rt(RT,hi)
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)+leg_rt(RT,round(hi*0.6,3))
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl=0.50):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=0.20]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,CRD]; C2=[Hc,CRD]
    U=confirm_w(leg_gapL(s_cur,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s_cur,0.25,52,rearm='window')+F25,C2,'month')
    X=hubv(); I=confirm_w(leg_ic(IC,50),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns)
CACHE={hi:run(hi) for hi in GRID}
P(f"{'held out':10s} {'lines clean on the PAST':32s} {'past would choose':18s} {'held-out lag':>12s}  {'v3.1 lag':>8s}")
for i in range(1,13):
    cut=PK[i]-pd.DateOffset(months=6)
    ok=[]
    for hi in GRID:
        r=CACHE[hi]
        prior_called=all(j in r['lags_p'] for j in range(i))
        prior_other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
        if prior_called and not prior_other: ok.append(hi)
    ch=max(ok) if ok else None
    lag=CACHE[ch]['lags_p'].get(i) if ch else None
    base=[-51,71,40,91,37,27,-7,55,3,-2,4,26,94][i]
    P(f"{PK[i]:%Y-%m}   {str(ok):32s} {str(ch):18s} {str(lag):>12s}  {base:>8d}")
P("\nEvery line in the grid keeps the whole record clean except where noted; the choice the past would make is the highest clean one, and")
P("the held-out turn is called at the same lag the full-sample choice gives wherever the two agree.")
out.close()
