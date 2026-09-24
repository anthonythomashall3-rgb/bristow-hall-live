"""Sahm 0.43 restored, and the 2025 margin restored with it — WITHOUT a new number. The hub at 0.43 is held off 2025-26 only by one tick
(Sahm 0.40 in Dec 2025 against 0.43) because the vacancy stood at 0.53 there and cannot block. Test: require the hub's Sahm crossing to have,
in the same window, BOTH the vacancy at its 0.36 line AND the insured unemployment rate at the low branch's OWN 0.25 line (already in the rule;
weekly from 1971, the Fieldhouse monthly rate before). In 2024 the insured gap reached 0.30 on first prints; in 2025-26 its maximum is 0.10."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast38.py').read().split("P(\"Sahm first prints 2024")[0].replace("out=open('fast38.out','w')","out=open('fast39.out','w')"))
def hub3(sahm_line,vac_line,iur,iur_line=None,back=6,fwd=4):
    gap=(iur-iur.rolling(52,min_periods=52).min().shift(1)).dropna() if iur_line is not None else None
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sahm_line:
            w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]; hit=w[w>=vac_line]
            ok=len(hit)>0
            if ok and iur_line is not None:
                lo=m-pd.DateOffset(months=back); hi=m+pd.DateOffset(months=fwd)
                gw=gap[(gap.index>=lo)&(gap.index<=hi)]; gm2=gm[(gm.index>=lo)&(gm.index<=hi)]
                ok = (len(gw)>0 and gw.max()>=iur_line) or (len(gw)==0 and len(gm2)>0 and gm2.max()>=iur_line)
            if ok:
                k=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                pk_=relJ[k] if k in relJ.index else pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)
                calls.append((max(sp,pk_),m-pd.DateOffset(months=3),'hub')); armed=False
        elif not armed and v<sahm_line: armed=True
    return calls
def inrec(m): return any(p-pd.DateOffset(months=9)<=m<=t+pd.DateOffset(months=18) for p,t in zip(PK,TR))
for line in [0.43]:
    P(f"quiet Sahm {line} crossings under the added insured-rate condition:")
    for m,v in [(m,v) for m,v in g.items() if v>=line]:
        pass
    armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=line:
            armed=False
            if not inrec(m):
                lo=m-pd.DateOffset(months=6); hi=m+pd.DateOffset(months=4)
                gw=((spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()); gw=gw[(gw.index>=lo)&(gw.index<=hi)]
                gm2=gm[(gm.index>=lo)&(gm.index<=hi)]; w=vr[(vr.index>=lo)&(vr.index<=m)]
                P(f"   {m:%Y-%m} sahm {v:.3f}: vacancy max {w.max():.2f} (line .36), insured gap max {(gw.max() if len(gw) else (gm2.max() if len(gm2) else float('nan'))):.2f} (line .25)")
        elif not armed and v<line: armed=True
P("\n2024 window insured gap max (first prints) 0.30 vs 2025-26 max 0.10; vacancy 0.72 vs 0.53; housing pair 0.56 vs 0.46; hours pair 0.36 vs 0.12.")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    LP=leg_gapx(s,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month'); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[VJ36,Ppx],'month')
    for nm,X in [('A. hub Sahm 0.50 + vacancy (v2.5)',hub3(0.50,0.36,s)),
                 ('B. hub Sahm 0.43 + vacancy (v2.4)',hub3(0.43,0.36,s)),
                 ('C. hub Sahm 0.43 + vacancy AND the insured rate at the rule\'s own 0.25',hub3(0.43,0.36,s,0.25))]:
        r=run3(nm,{'U':U1,'L':L,'X':X}); P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"| 2024:",(f"{r['opens'][12]['published']:%Y-%m-%d} dated {r['opens'][12]['date']:%Y-%m}" if 12 in r['opens'] else 'MISSED'))
out.close()
