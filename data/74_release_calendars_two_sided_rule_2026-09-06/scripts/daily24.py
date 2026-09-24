"""THE DEEP BRANCH — the right idea for the turns that are PROPOSAL-bound. 1953 (+62), 1957 (+40) and 1981 (+55) all
wait on their own proposal's crossing week, so the only lever is a LOWER proposal line, which crosses earlier. A lower
line is only affordable if the confirmer side is asked for more. So: a third insured-rate branch at 0.10-0.20 that
requires TWO of the five demand objects to stand at their lines inside the window, instead of one. No new series; a
new way of combining the ones already in the rule."""
exec(open('fast49.py').read().split("def full(")[0].replace("out=open('fast49.out','w')","out=open('daily24.out','w')"))
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
def confirm_n(calls,confs,n=2,back=6,fwd=4):
    """a proposal survives only if at least n of the confirmers stand at their line inside its window; the call date is
    the n-th confirmer's publication (or the proposal's, whichever is later)"""
    out_=[]
    for p_,dd in calls:
        lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0)
        pubs_=[]
        for c in confs:
            gp=c['gap']; w=gp[(gp.index>=lo)&(gp.index<=hi)]; hit=w[w>=c['line']]
            if not len(hit): continue
            k=hit.index[0]
            if 'pubs' in c and c['pubs'] is not None and k in c['pubs'].index: pubs_.append((c['pubs'][k],c['name']))
            elif 'pub_lag_days' in c: pubs_.append((k+pd.Timedelta(days=c['pub_lag_days']),c['name']))
            else: pubs_.append((k,c['name']))
        if len(pubs_)<n: continue
        pubs_.sort(); out_.append((max(p_,pubs_[n-1][0]),dd,'+'.join(x[1] for x in pubs_[:n])))
    return out_
def sc2(nm,deep_line=None,n=2,hubline=0.43,look45=91,deep_rearm='window',deep_pub=12):
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
    C1=[Vc,Hh,CRD,SPR]; C2=[Hc,CRD,SPR]; ALL=[Vc,Hh,Hc,CRD,SPR]; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,look45,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        if deep_line is not None:
            Dp=leg_gapL(s,deep_line,52,rearm=deep_rearm)+[x for x in leg_gap_mx2(gm,deep_line,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,deep_line)
            legs['D']=[(a,b) for a,b,c in confirm_n(Dp,ALL,n=n)]
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:42s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY' if early else ''}")
    return ok
P("=== v3.3r, and v3.3r with the 0.45 look-back at 91 weeks (the sweep of daily23) ===")
sc2('v3.3r (look-back 52w)',look45=52); sc2('v3.4 (look-back 91w) — 1990 to -12',look45=91)
P("\n=== the deep branch: a lower insured-rate line requiring TWO demand objects ===")
for dl in [0.10,0.15,0.20,0.25,0.30]:
    for n in [2,3]:
        sc2(f'  deep {dl} needing {n} confirmers',deep_line=dl,n=n)
P("\n=== the deep branch with the tighter re-arm ===")
for dl in [0.10,0.15,0.20]:
    sc2(f'  deep {dl} n=2 re-arm at zero',deep_line=dl,n=2,deep_rearm='zero')
    sc2(f'  deep {dl} n=3 re-arm at zero',deep_line=dl,n=3,deep_rearm='zero')
out.close()
