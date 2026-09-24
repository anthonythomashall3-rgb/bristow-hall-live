"""Anthony's condition: go back to Sahm 0.43 IF it adds no false alarms. Measured exactly — every quiet Sahm crossing the lower line admits,
what blocks it and by how much; the live margin; and whether any admissible co-condition removes the extra exposure."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast38.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast38.out','w')","out=open('hub43.out','w')"))
def crossings(line):
    out_=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=line: out_.append((m,v)); armed=False
        elif not armed and v<line: armed=True
    return out_
def inrec(m): return any(p-pd.DateOffset(months=9)<=m<=t+pd.DateOffset(months=18) for p,t in zip(PK,TR))
for line in [0.50,0.43]:
    cs=crossings(line); q=[(m,v) for m,v in cs if not inrec(m)]
    P(f"\nSAHM LINE {line}: {len(cs)} crossings, {len(q)} in quiet months")
    for m,v in q:
        w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
        P(f"   quiet crossing {m:%Y-%m} sahm {v:.3f} | vacancy in the six months back: max {w.max():.2f} at {w.idxmax():%Y-%m} (line 0.36) -> {'CONFIRMED = FALSE ALARM' if w.max()>=0.36 else f'blocked, margin {0.36-w.max():.2f}'}")
P("\nTHE LIVE MARGIN — the 2025-26 pause on the unemployment side:")
w=g['2025-06':]; P(f"   Sahm first prints max {w.max():.2f} at {w.idxmax():%Y-%m}; margin to 0.43 = {0.43-w.max():.2f} (one tick of the rate); margin to 0.50 = {0.50-w.max():.2f}")
wv=vr['2025-06':]; P(f"   vacancy gap max {wv.max():.2f} at {wv.idxmax():%Y-%m} — ABOVE its 0.36 line, so the vacancy would NOT block a Sahm crossing in 2025-26: the whole 2025 safety is the Sahm line itself")
P("\nEVERY SAHM READING WITHIN ONE TICK OF 0.43 IN A QUIET MONTH (the near-misses the line must survive):")
near=[(m,v) for m,v in g.items() if 0.36<=v<0.43 and not inrec(m)]
byep=[]; last=None
for m,v in near:
    if last is None or (m-last).days>200: byep.append([])
    byep[-1].append((m.strftime('%Y-%m'),round(v,3))); last=m
for e in byep:
    m0=pd.Timestamp(e[0][0]+'-01'); w=vr[(vr.index>=m0-pd.DateOffset(months=6))&(vr.index<=pd.Timestamp(e[-1][0]+'-01'))]
    P(f"   {e[0][0]}..{e[-1][0]} max sahm {max(x[1] for x in e):.3f} | vacancy max in window {w.max() if len(w) else float('nan'):.2f}")
out.close()
