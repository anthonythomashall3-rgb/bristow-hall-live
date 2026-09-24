"""WHERE THE SLOW CLOSES COME FROM. Every closer on the menu, its calls around each of the nine troughs, and for the
confirmed closers which of the two confirmations binds."""
import sys
sys.argv=['x','1962','2026']
src=open('walk24.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk24_%s.out'%sys.argv[1],'w')","out=open('mc12.out','w')")
exec(src)
TR9=[pd.Timestamp(x) for x in ['1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-08-01']]
def lag(p,tr): return (p-(tr+pd.DateOffset(months=1))).days
P("closers on the menu: "+", ".join(sorted(TLH)))
for tr in TR9:
    P(f"\n{tr:%Y-%m}")
    for k in sorted(TLH):
        c=sorted([(p_,d_) for p_,d_ in TLH[k] if tr-pd.DateOffset(months=6)<=d_<=tr+pd.DateOffset(months=12)])
        if not c: P(f"   {k}: -"); continue
        P(f"   {k}: "+" | ".join(f"{p_:%Y-%m-%d} dated {d_:%Y-%m} lag {lag(p_,tr):+d}" for p_,d_ in c[:3]))
P("\n\n==== what the confirmations cost. S and R are published at the later of the settle and the SECOND of three ====")
P("==== confirmations: claims 0.15 off their peak, housing starts 2 per cent off their low, hours 2 per cent off ====")
def _detail(calls,cdrop=0.15,rise=2.0,fwd=6):
    for pp,dd in calls:
        if not any(tr-pd.DateOffset(months=6)<=dd<=tr+pd.DateOffset(months=12) for tr in TR9): continue
        hits=[]
        seg=_BELOW[(_BELOW.index>=dd)&(_BELOW.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(('claims',h.index[0]+pd.Timedelta(days=5)))
        for nm2,rl_,pdy in [('starts',_RS,18),('hours',_RH,5)]:
            s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2): hits.append((nm2,pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1)))
        hits.sort(key=lambda z:z[1])
        P(f"   settle {pp:%Y-%m-%d} dated {dd:%Y-%m} -> "+", ".join(f"{n2} {t2:%Y-%m-%d}" for n2,t2 in hits)+(f"  BINDS {hits[1][0]} {hits[1][1]:%Y-%m-%d}" if len(hits)>1 else "  UNCONFIRMED"))
P("\nS, before confirmation:"); _detail(TLHS_RAW) if False else None
P("\nR, the insured-rate settle before confirmation:"); _detail(_settle_calls(stable=6))
P("\nT, the starts settle before the guard:"); 
for pp,dd in _settle_starts():
    if any(tr-pd.DateOffset(months=6)<=dd<=tr+pd.DateOffset(months=12) for tr in TR9): P(f"   settle {pp:%Y-%m-%d} dated {dd:%Y-%m}")
P("\nR at other stable values, raw settle only (no confirmation):")
for st in (3,4,5,6):
    cc=[(p_,d_) for p_,d_ in _settle_calls(stable=st) if any(tr-pd.DateOffset(months=6)<=d_<=tr+pd.DateOffset(months=12) for tr in TR9)]
    P(f"   stable={st}: "+" | ".join(f"{d_:%Y-%m}@{p_:%Y-%m-%d}" for p_,d_ in sorted(cc)))
out.close()
