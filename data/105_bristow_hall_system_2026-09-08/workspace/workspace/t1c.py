"""STEP 1b, detail: every C proposal (the flow's fall) week by week around the nine troughs, with what confirmed it and what
did not, for a given configuration. Usage: python3 t1c.py <m> <D> <n> <s> <c> <u>"""
import sys, io, contextlib
MA=sys.argv[1]; ARGS=[float(x) for x in sys.argv[2:7]]
HA='last'
sys.argv=['x','2011','2012','wt1c']
src=open('walk26.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import pandas as pd, numpy as np
exec(open('t1b.py').read().split("# ---------------- the screen")[0].split("# ---------------- the objects")[1])
DD,NN,SS,CCc,UU=ARGS; NN=int(NN)
OUT=open(f'out/t1c_m{MA}_D{DD:g}_n{NN}_s{SS:g}_c{CCc:g}_u{UU:g}.txt','w')
def P(*a):
    print(*a); print(*a,file=OUT); OUT.flush()
TRs=[pd.Timestamp(x) for x in ['1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
P(f"C detail: mean {MA} weeks, D {DD}, n {NN}, s {SS}, c {CCc}, u {UU}; hold {HA}")
for T in TRs:
    P(f"\n== trough {T:%Y-%m} ==  week | pubIC | IC{MA}k drop run amp | S&P%>lo | CCdrop(pub) | IURdrop(tenths) | proposer? confirmers | flow-peak-month | stock-peak-month")
    w0=T-pd.DateOffset(months=5); w1=T+pd.DateOffset(months=2)+pd.offsets.MonthEnd(0)
    for i,t in enumerate(_W):
        if t<w0 or t>w1: continue
        r=FI.iloc[i]; prop=(r['drop']>=DD and r['amp']>=20 and r['run']>=NN)
        sp=_sp[i]; fc=_fc[i]; du=_du[i]
        hs=[]
        if np.nan_to_num(sp,nan=-99)>=SS: hs.append('SP')
        if np.nan_to_num(fc,nan=-99)>=CCc: hs.append('CC')
        if np.nan_to_num(du,nan=-99)>=UU: hs.append('IUR')
        pm=_peak(t)
        seg=LCC[(LCC.index<=_tc[i])&(LCC.index>_tc[i]-pd.Timedelta(weeks=26))]
        cm=seg.idxmax() if len(seg) else pd.NaT
        flag='>>' if prop and hs else ('p ' if prop else '  ')
        P(f"{flag} {t:%Y-%m-%d} | {_pI[i]:%m-%d} | {np.exp(LIC.loc[t]/100)/1000:5.0f} {r['drop']:5.1f} {int(r['run']):2d} {r['amp']:5.1f} | {sp if not np.isnan(sp) else float('nan'):6.1f} | {fc if not np.isnan(fc) else float('nan'):5.1f}({(_tc[i]+pd.Timedelta(days=12)):%m-%d}) | {du if not np.isnan(du) else float('nan'):4.0f} | {'PROP' if prop else '    '} {','.join(hs):10s} | {pm:%Y-%m} | {cm:%Y-%m}")
OUT.close()
