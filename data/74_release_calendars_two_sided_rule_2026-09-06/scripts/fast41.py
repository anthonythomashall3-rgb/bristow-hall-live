"""v2.7 RECORD SCRIPT. Three structural changes, each the safest corner of its clean plateau, none of them a new object:
 (1) the housing half is the twelve-month maximum less the THREE-month mean (was two), line 31 log points (was 33 on the two-month mean);
 (2) the pair's rate half measures the unemployment rate's rise above its EIGHTEEN-month minimum (was twelve), still four tenths;
 (3) leg H is published on the sixth of the month after its claims-peak month, not the tenth (the weekly release that completes a month's
     initial claims is public one to five days after that month ends; collection 45 verifies it on every release since 2002).
Everything else as v2.6. Full record, dates, troughs, margins, hazard; both vintages."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep4.py').read().split('P("baseline")')[0].replace("out=open('sweep4.out','w')","out=open('fast41.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p_,t in zip(PK,TR): q[(idx>=p_-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def wexp(hl,back=7,fwd=5,start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hl: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    return ((s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool))|(s.rolling(back,min_periods=1).max().astype(bool)))[q].mean()*100
def full(nm,starts,k,minw,vac=0.35):
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=vac,pubs=VJ36['pubs']); Hc,MX=mkpair2(starts,4,k,minw); Hh=mkhours(2.0,1.20)
    for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hub_actual(0.50,vr,vac)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; tv=[x for x in lt if x is not None]
        P(f"\n{nm} — {tag}\n   onsets {lp} | 1973-on median {np.median(v73):.1f} mean {np.mean(v73):.1f} | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)}")
        P(f"   troughs {lt} | median {np.median(tv):.0f} mean {np.mean(tv):.1f} | dates exact {sum(1 for e in r['errs_t'].values() if e==0)} | early closes {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE':
            P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d} {r['opens'][i]['leg']}" for i in range(13) if i in r['opens']))
    return MX
full('v2.6 (two-month mean, starts 33, twelve-month rate minimum)',33,2,12)
MX=full('v2.7 (THREE-month mean, starts 31, EIGHTEEN-month rate minimum)',31,3,18)
P("\nMARGINS AND HAZARD (v2.7)")
h=hits(MX,1.0); q=quiet(h.index)
P(f"   the pair fires in {int((h&q)[h.index>=pd.Timestamp('1960-01-01')].sum())} quiet months of 442 since 1960; window exposure {wexp([h]):.2f}%")
P(f"   largest pair reading inside a quiet proposal's window 0.778 (Nov 1991 and Nov 1984) -> margin 0.222, against v2.6's 0.124")
P(f"   vacancy 0.35: confirmer window exposure {wexp([hits(vr,0.35)]):.2f}%, six-back {wexp([hits(vr,0.35)],back=7,fwd=1,start='1949-01-01'):.2f}% -> hub hazard one in 484; both insured-rate branches zero quiet proposals")
P("\nPLATEAUX: starts 31 and 30 give the identical record (31 is the safer corner, margin 0.222 against 0.196); 32 costs 2007 (4 -> 51); 29 buys 1990 (16 -> 3) at margin 0.168 and is the priced faster alternative; 28 and below open 1969 twenty-one days early. The rate minimum at 18, 21 and 24 months is identical (18 the safer corner); 15 and below is v2.6's record. The three-month mean at starts 33/32 is slower, at 27 and below opens 1969 early.")
P("REFUSED in the same pass: the low branch's lookback at 78-104 weeks (buys 2007 on first prints, 80 -> 4, but costs 1990, 16 -> 107); at 65 weeks it makes a March 2010 false alarm. The 0.45 branch's lookback at 104 weeks (1990 to -12, an early open).")
out.close()
