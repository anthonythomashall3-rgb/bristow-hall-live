"""v2.8 RECORD SCRIPT — the housing line at 29, the fastest value that keeps every call inside or after its peak month and makes no other call
on either vintage. Everything else as v2.7."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('fast42.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p_,t in zip(PK,TR): q[(idx>=p_-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
QL=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)})
def wmax(ser,dd): seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]; return round(float(seg.max()),3) if len(seg) else float('nan')
def full(nm,starts):
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=0.35,pubs=VJ36['pubs']); Hc,MX=mkpair2(starts,4,3,18); Hh=mkhours(2.0,1.20)
    for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hub_actual(0.50,vr,0.35)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; tv=[x for x in lt if x is not None]
        P(f"\n{nm} — {tag}\n   onsets {lp} | 1973-on median {np.median(v73):.1f} mean {np.mean(v73):.1f} | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} mean {np.mean(tv):.1f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE': P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}" for i in range(13) if i in r['opens']))
    mm=sorted([(wmax(MX,dd),dd.strftime('%Y-%m')) for dd in QL if not np.isnan(wmax(MX,dd))],reverse=True)[:3]
    h=(MX>=1.0).reindex(pd.date_range('1960-01-01','2026-07-01',freq='MS')).fillna(False); q=quiet(h.index)
    P(f"   margin {1-mm[0][0]:.3f} (highest quiet-window pair reading {mm[0]}, then {mm[1:]}); quiet months at the line {int((h&q).sum())} of 442")
full('v2.7 (starts 31)',31); full('v2.8 (starts 29)',29)
P("\n2024 CANNOT BE MADE FASTER: the housing half reaches only 0.62 in the whole 2024 window (starts fell too little), so the low branch's own 2024 proposal can never be confirmed; the hub on Sahm's published line is the only route to 2024 and it is bound by the 2 August 2024 employment report.")
P("REFUSED this pass: the hours pair as a second confirmer of the low branch (April 2003, both vintages); the vacancy in the same role (July 1989, and it loses 1948, 1990 and 2001); the confirmation window's back reach at seven months or more (January 1976 and November 1991, and it loses 2001) — six is the maximum. The vacancy object's own shape could not be swept honestly: rebuilding the (2,6) gap from the raw Petrosky-Nadeau-Zhang/JOLTS file does not reproduce the lab's series (largest difference 1.70 points), and every variant of the rebuild was slower (1960 at 183 to 244 days, 2020 at 66).")
out.close()
