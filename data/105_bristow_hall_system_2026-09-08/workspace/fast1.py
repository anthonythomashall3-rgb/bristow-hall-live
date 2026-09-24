"""Fast corner of the two-sided rule under the 'construction-grade' standard: the tightest lines with zero other calls on
the whole record 1948-2026.  Stage 1: leg U's line x the vacancy line x U's confirmer set (hub Sahm at 0.50)."""
from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur
import itertools, sys
KJHS={k:TLG[k] for k in 'KJHS'}
out=open('fast1.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
P("stage 1: U line x vacancy line x confirmers of U (hub: Sahm 0.50 & vacancy at the same line; closers K,J,H,S)")
P(f"{'U':>5}{'vac':>5}{'conf':>8} | called other  med  mean worst  <=0 <=31 | lags 1973..2024 | other calls")
for ul in [0.20,0.25,0.30,0.35,0.40,0.45,0.50]:
    for vl in [0.24,0.30,0.36]:
        SEC['V']=dict(name='vacancy',gap=vr,line=vl,pub_day=30)
        X=leg_X2(vac_line=vl); U=leg_U(s_cur,ul)
        for cf in [['V'],['V','H','P'],['S','V','H','P']]:
            r=score13(chron({'U':U,'X':X},KJHS,cf)); lp=[r['lags_p'].get(i) for i in range(13)]; v=[l for l in lp if l is not None]
            P(f"{ul:5.2f}{vl:5.2f}{'|'.join(cf):>8} | {len(v):6d} {len(r['other']):5d} {np.median(v):4.0f} {np.mean(v):5.1f} {max(v):5d} {sum(1 for l in v if l<=0):4d} {sum(1 for l in v if l<=31):4d} | {[('-' if l is None else l) for l in lp[5:]]} | {[(d,lg) for _,d,lg in r['other']]}")
out.close()
