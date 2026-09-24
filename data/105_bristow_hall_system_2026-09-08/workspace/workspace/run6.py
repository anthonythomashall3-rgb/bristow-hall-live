from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur
import itertools
KJHS={k:TLG[k] for k in 'KJHS'}
UL=[0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.70]; VL=[0.20,0.24,0.30,0.36,0.42,0.50]
print("SAFETY MAP of the two-sided rule: cell = (peaks called of 13, other calls, median lag d)")
print(f"{'U line':>7}"+''.join(f"{'vac '+str(vl):>16}" for vl in VL))
for ul in UL:
    row=f"{ul:>7.2f}"
    for vl in VL:
        SEC['V']=dict(name='vacancy',gap=vr,line=vl,pub_day=30)
        r=score13(chron({'U':leg_U(s_cur,ul),'X':leg_X2(vac_line=vl)},KJHS,['V','H','P'])); lp=list(r['lags_p'].values())
        row+=f"   {len(lp):2d} o{len(r['other'])} m{np.median(lp):4.0f}"
    print(row)
