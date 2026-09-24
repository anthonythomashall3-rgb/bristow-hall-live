"""IS THE PAPER SPREAD'S LINE FITTED? The line is a RULE, not a number: 1.5 times the highest reading the object
reaches inside any quiet proposal window. Here that rule is applied causally — at each turn the highest quiet reading
is recomputed from the record BEFORE that turn only, multiplied by 1.5, and the held-out turn scored with the line the
past would have set. If the line the past sets gives the same call, the gain is not fitted."""
exec(open('fast49.py').read().split("def full(")[0].replace("out=open('fast49.out','w')","out=open('causal27.out','w')"))
def run(line,hubline=0.50):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
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
    SP=dict(name='sp',gap=GSP,line=line,pub_lag_days=1); C1=[Vc,Hh,CRD,SP]; C2=[Hc,CRD,SP]
    U=confirm_w(leg_gapL(s_cur,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s_cur,0.25,52,rearm='window')+F25,C2,'month')
    X=hubv(hubline); I=confirm_w(leg_ic(IC,50),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns)
FULL=run(LINE)
P(f"full-sample line {LINE} (1.5 x {QMAX:.3f}); record {[FULL['lags_p'].get(i) for i in range(13)]} others {[o[1] for o in FULL['other']]}")
P(f"\n{'held out':10s} {'quiet max known then':>20s} {'line the past sets':>19s} {'held-out lag':>12s} {'full-sample lag':>16s} {'other calls':>12s}")
for i in range(2,13):
    cut=PK[i]-pd.DateOffset(months=6)
    prior=[float(wseg(GSP,dd).max()) for dd in QP if dd<cut and len(wseg(GSP,dd))]
    if not prior: P(f"{PK[i]:%Y-%m}   (the object has no quiet window before this turn)"); continue
    ln=round(max(prior)*1.5,3); r=run(ln)
    P(f"{PK[i]:%Y-%m}   {max(prior):20.3f} {ln:19.3f} {str(r['lags_p'].get(i)):>12s} {str(FULL['lags_p'].get(i)):>16s} {str([o[1] for o in r['other']]):>12s}")
P("\nThe line is a rule applied to the past, not a number chosen from the whole record: where the past's line equals or")
P("exceeds the full-sample line, the call is identical and the gain is causal.")
out.close()
