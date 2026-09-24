"""v2.5 — the hub back on SAHM'S OWN PUBLISHED LINE, 0.50. Anthony's point: the Sahm indicator crosses 0.50 in 2024 anyway, on the July 2024
first print (0.5333, released 2 Aug 2024). So 0.43 was never needed for DETECTION — it bought 28 days and cost the date and half the safety.
At 0.50 the crossing month is July, dated July-3 = APRIL 2024 = Paper 1's peak month exactly; at 0.43 it is June, dated March, a month early.
Everything else as v2.4. Record, dates, hazard, and the causal replay with Sahm INHERITED (a published line is not a line we choose)."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast37.py').read().split("RES={}")[0].replace("out=open('fast37.out','w')","out=open('fast38.out','w')"))
P("Sahm first prints 2024: Jun 0.4333 (released 2024-07-05), Jul 0.5333 (2024-08-02), Aug 0.5667, Sep 0.5000 — the published 0.50 line crosses on the July print.")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    LP=leg_gapx(s,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month'); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[VJ36,Ppx],'month')
    for sl in [0.50,0.43]:
        X=hub_actual(sl,vr,0.36)
        r=run3(f"hub at Sahm {sl} (vacancy 0.36); U45{{V|hours}} + U25{{starts 35 x rate 4 tenths, real-time}}",{'U':U1,'L':L,'X':X})
        P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"| exact",sum(1 for e in r['errs_p'].values() if e==0),"| 2024 date error",r['errs_p'].get(12))
eps,eVb,hz=hub_haz(0.50,0.36); P(f"\nhub hazard at Sahm 0.50: quiet crossings {eps} x six-back vacancy 3.40% = {hz:.3f}%/yr, ONE IN {1/(hz/100):.0f}")
eps2,_,hz2=hub_haz(0.43,0.36); P(f"hub hazard at Sahm 0.43: quiet crossings {eps2} = {hz2:.3f}%/yr, one in {1/(hz2/100):.0f}")
P("\nwhat 0.43 buys and costs: 2024 +66 vs +94 (28 days); dated Mar 2024 vs APR 2024 (Paper 1's month); hazard one in 288 vs one in 575; and 0.43 is chosen after seeing 2024 while 0.50 is Sahm's published line (2019).")
out.close()
