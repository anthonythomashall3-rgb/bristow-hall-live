"""STEP 1c, the margins: how close closer C came to firing at each mid-episode pause, and how far past its lines it was
at each trough, under a given configuration. Usage: python3 t1d.py <D> <n> <s>   (c 3.0, u 3, A 20, three-week mean)
For every week from two months before to three months after the pause month (or the trough month), the proposer's
drop, run and amplitude, the S&P per cent above its 26-week low on the release day, the continued-claims and
insured-rate drops, and whether C would have fired. Then, per event, the closest approach: over weeks with run >= n
and amplitude >= 20, the largest value of min(drop - D, S&P - s) — positive means C fired, negative the shortfall."""
import sys, io, contextlib
ZD=float(sys.argv[1]); ZN=int(sys.argv[2]); ZS=float(sys.argv[3])
sys.argv=['x','2011','2012','wt1d']
src=open('walk34.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import pandas as pd, numpy as np
OUT=open(f'out/t1d_D{ZD:g}_n{ZN}_s{ZS:g}.txt','w')
def P(*a):
    print(*a); print(*a,file=OUT); OUT.flush()
EV=[('pause','1970-08'),('pause','1974-07'),('pause','1982-05'),('pause','2001-06'),('pause','2008-05'),
    ('trough','1970-11'),('trough','1975-03'),('trough','1980-07'),('trough','1982-11'),('trough','1991-03'),
    ('trough','2001-11'),('trough','2009-06'),('trough','2020-04'),('trough','2024-08')]
# also the 1980 false start the run of two produced (walk28): show the weeks of January-February 1980
EV.insert(0,('false start','1980-01'))
P(f"closer C margins: D {ZD:g}, n {ZN}, s {ZS:g}, c 3.0, u 3, A 20, three-week mean. drop/amp in log points, S&P in per cent, CC in log points, IUR in tenths")
summary=[]
for kind,ym in EV:
    T=pd.Timestamp(ym+'-01'); w0=T-pd.DateOffset(months=2); w1=T+pd.DateOffset(months=3)+pd.offsets.MonthEnd(0)
    P(f"\n== {kind} {ym} ==  week-ending | released | drop run amp | S&P%>26wk-low | CCdrop IURdrop | fires?")
    best=None
    for i,t in enumerate(_CW):
        if t<w0 or t>w1: continue
        r=_FI.iloc[i]; sp=_Csp[i]; fc=_Cfc[i]; du=_Cdu[i]
        spv=-99 if np.isnan(sp) else sp; fcv=-99 if np.isnan(fc) else fc; duv=-99 if np.isnan(du) else du
        prop=(r['drop']>=ZD and r['amp']>=20 and r['run']>=ZN)
        conf=(spv>=ZS) or (fcv>=3.0) or (duv>=3)
        if r['run']>=ZN and r['amp']>=20:
            m=min(r['drop']-ZD, max(spv-ZS, 99 if (fcv>=3.0 or duv>=3) else -99))
            if best is None or m>best[0]: best=(m,t,r['drop'],r['run'],spv,fcv,duv)
        P(f"{'>>' if prop and conf else ('p ' if prop else '  ')} {t:%Y-%m-%d} | {_CpI[i]:%m-%d} | {r['drop']:5.1f} {int(r['run']):2d} {r['amp']:5.1f} | {spv:6.1f} | {fcv:5.1f} {duv:4.0f} | {'FIRES' if prop and conf else ''}")
    summary.append((kind,ym,best))
P("\nclosest approach per event (weeks with run >= n and amplitude >= 20): min(drop - D, S&P - s); positive = fired")
for kind,ym,b in summary:
    if b is None: P(f"   {kind:11s} {ym}: no week with run >= {ZN} and amplitude >= 20 in the window")
    else: P(f"   {kind:11s} {ym}: {b[0]:+6.1f}  at week {b[1]:%Y-%m-%d}: drop {b[2]:.1f} run {int(b[3])} S&P {b[4]:.1f} CC {b[5]:.1f} IUR {b[6]:.0f}")
OUT.close()
