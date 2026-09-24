"""Combine the two structural winners: the rate half's minimum window at 18 months (buys 1981 and 1990) and a three-month housing mean
(buys 2007). Joint grid, both vintages, zero other calls required; margins for the survivors."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep4.py').read().split('P("baseline")')[0].replace("out=open('sweep4.out','w')","out=open('sweep5.out','w')"))
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
QL=sorted({dd for p_,dd in leg_gapx(s_cur,0.25,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapx(spl,0.25,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)})
def wmax(ser,dd): seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]; return round(float(seg.max()),3) if len(seg) else float('nan')
def go2(nm,starts,k,minw,vac=0.35,look45=52):
    ok=go(nm,starts=starts,k=k,minw=minw,vac=vac,look45=look45)
    if ok:
        _,MX=mkpair2(starts,4,k,minw); mm=sorted([(wmax(MX,dd),dd.strftime('%Y-%m')) for dd in QL if not np.isnan(wmax(MX,dd))],reverse=True)[:3]
        P(f"      pair margin {1-mm[0][0]:.3f} (highest quiet-window reading {mm[0]}; next {mm[1:]})")
    return ok
P("--- rate-half minimum window 18, housing mean k and line swept ---")
for k in [2,3,4]:
    for st in [37,35,33,31,29,27]: go2(f'minw18 k={k} starts {st}',st,k,18)
P("\n--- rate-half minimum window 15 and 21 (is 18 a plateau?) ---")
for mw in [13,15,18,21,24]: go2(f'k=2 starts 33 minw {mw}',33,2,mw)
for mw in [13,15,18,21,24]: go2(f'k=3 starts 31 minw {mw}',31,3,mw)
out.close()
