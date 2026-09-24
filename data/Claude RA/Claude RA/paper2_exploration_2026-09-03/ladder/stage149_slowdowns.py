"""Stage 149: the answer to 'why were some international episodes missed'.  The OECD's
chronology dates growth cycles, not recessions: it counts slowdowns in which output never fell.
Each OECD episode is therefore split by whether the country also had two consecutive negative
quarters of real GDP inside it, and detection is reported separately for the two groups."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def overlaps(P,T,eps2,slack=6):
    for p,t in eps2:
        if p<=T+pd.DateOffset(months=slack) and t>=P-pd.DateOffset(months=slack): return True
    return False
DEL,DEL2=0.25,2.0
print("%-4s %-16s %-22s %-22s"%("iso","country","with a fall in output","slowdown only"))
TA=TB=EA=EB=0
for iso in sorted(CC):
    ch=channels(iso)
    if ch is None: continue
    idx,S,gate=ch
    eps,src=oecd(iso)
    if eps is None: continue
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    if not eps: continue
    tech=technical(iso)[0]
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=9)))
    hit=pd.Series(False,index=idx)
    for k,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; hit=hit|((z>=rec+DEL)&gate)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; hit=hit|((z>=rec+DEL2)&~gate)
    hits=list(idx[hit.reindex(idx).fillna(False).values])
    a=b=na=nb=0
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3) for h in hits)
        if overlaps(P,T,tech):
            na+=1; a+=int(got)
        else:
            nb+=1; b+=int(got)
    TA+=a;EA+=na;TB+=b;EB+=nb
    print("%-4s %-16s %-22s %-22s"%(iso,NAME.get(iso,iso),"%d of %d"%(a,na),"%d of %d"%(b,nb)))
print("\nTOTAL   episodes in which output actually fell : %d of %d (%.0f%%)"%(TA,EA,100*TA/max(EA,1)))
print("TOTAL   growth slowdowns with no fall in output: %d of %d (%.0f%%)"%(TB,EB,100*TB/max(EB,1)))
print("\nA detector built to avoid firing on slowdowns should score high on the first line and low")
print("on the second.  The pooled figure of 54 per cent mixes the two.")
