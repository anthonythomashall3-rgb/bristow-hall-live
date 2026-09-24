"""THE TROUGH SIDE, BROUGHT TO THE ONSET SIDE'S STANDARD. The closers were inherited whole: K (weekly continued claims,
a 4.0 log-point drop from the episode's peak), J (monthly continued claims, 5.0), H (monthly initial claims, 8.0), S
(Paper 1's Bristow rule) — and their drops have never been swept in this line, nor their publication clocks audited.
Both are done here against v3.5 read real-time."""
exec(open('fast51.py').read().split("full('v3.4")[0].replace("out=open('fast51.out','w')","out=open('trough1.out','w')"))
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
nat=pd.read_csv(W+'/lab/weekly/DOL_national_weekly_claims_sa_rt.csv',index_col=0,parse_dates=True) if os.path.exists(W+'/lab/weekly/DOL_national_weekly_claims_sa_rt.csv') else None
P("PUBLICATION CLOCK AUDIT of the closers as shipped")
for k in ['K','J','H','S']:
    v=TLH[k]; P(f"   {k}: {len(v)} calls — " + ", ".join(f"{p:%Y-%m-%d} dated {d:%Y-%m} (published {(p-(d+pd.offsets.MonthEnd(0))).days:+d} d after the dated month ends)" for p,d in v[:4]))
def score_only(TL,look45=91,hubline=0.43):
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
    C1=[Vc,Hh,SPR]; C2=[Hc,SPR]
    U=confirm_w(leg_gapL(spl,0.45,look45,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(spl,0.25,52,rearm='window')+F25,C2,'month')
    X=hubv(hubline); I=confirm_w(leg_ic(ICfp,50),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns)
def rep(nm,TL):
    r=score_only(TL); lt=[r['lags_t'].get(i) for i in range(13)]; tv=[x for x in lt if x is not None]
    et=[r['errs_t'].get(i) for i in range(13)]
    lp=[r['lags_p'].get(i) for i in range(13)]; av=[x for x in lp if x is not None]
    P(f"{'OK ' if len(r['other'])==0 and len(r['lags_p'])==13 else 'BAD'} {nm:44s} troughs {lt} n {len(tv)} median {np.median(tv):.0f} mean {np.mean(tv):.0f} worst {max(tv)} exact {sum(1 for e in et if e==0)} within1 {sum(1 for e in et if e is not None and abs(e)<=1)} EARLY {sum(1 for x in tv if x<0)} | onsets mean {np.mean(av):.1f} others {[o[1] for o in r['other']][:2]}")
P("\n=== the shipped closers ==="); rep('v3.5 closers as shipped',TLH)
P("\n=== the drops swept (K weekly continued claims, J monthly continued, H monthly initial) ===")
nat_m=None
try:
    natm=pd.read_csv(W+'/lab/weekly/DOL_national_monthly_claims_sa_rt.csv',index_col=0,parse_dates=True)
except Exception:
    natm=None
P(f"   monthly Department file held: {natm is not None}")
import itertools
FH=None
try:
    FH=pd.read_csv(W+'/lab/fh/FH_nat_sa_rt.csv',index_col=0,parse_dates=True); P(f"   Fieldhouse field: {FH.shape} {FH.index.min().date()} -> {FH.index.max().date()} cols {list(FH.columns)[:6]}")
except Exception as e: P("   Fieldhouse field not read: "+str(e))
out.close()
