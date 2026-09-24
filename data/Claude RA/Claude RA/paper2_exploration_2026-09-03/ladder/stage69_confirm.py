"""Stage 69: (5) confirmation with withdrawal.  A first channel opens a PROVISIONAL
call; a second channel on a DIFFERENT underlying series within X days makes it
CONFIRMED; otherwise the provisional call is withdrawn and logged.  Only confirmed
calls enter the chronology.  What does it cost, and what does it buy?"""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np, pandas as pd, json
P8=dict(sahm=0.36,iur=0.45,pay=0.003,hou=20,bill=1.45,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=19,baa=1.50)
KEEP=["sahm","iur","pay","hou","bill","sahmC","vix"]
fast,clause,ung,lane=pieces(P8)
SER={"sahm":fresh(fast["sahm"],120)&G, "iur":fresh(fast["iur"],120)&G,
     "pay":fresh(fast["pay"],120)&G,  "hou":fresh(fast["hou"],120)&G,
     "bill":fresh(fast["bill"],120)&G,"sahmX":fresh(clause["sahmC"]&NG,120),
     "vix":fresh(lane["vix"],120)}
GRP={"sahm":"U","sahmX":"U","iur":"IU","pay":"E","hou":"H","bill":"R","vix":"F"}
on=np.zeros(N,bool)
for a in SER.values(): on|=np.asarray(a,bool)
PK=[pd.Timestamp(p) for p,_ in T_P1]
print("days from the first channel to the first channel on a DIFFERENT series")
print("%-10s %-12s %-8s %-12s %-8s %s" % ("peak","provisional","series","confirmed","series","gap (days)"))
gaps=[]
i=0; seen=[]
while i<N:
    if on[i] and cal[i]>=pd.Timestamp("1968-06-01"):
        firsts=[k for k,a in SER.items() if np.asarray(a,bool)[i]]
        g0={GRP[k] for k in firsts}
        j=i; conf=None
        while j<N and j<i+900:
            hit=[k for k,a in SER.items() if np.asarray(a,bool)[j] and GRP[k] not in g0]
            if hit: conf=(j,hit[0]); break
            j+=1
        seen.append((i,firsts[0],conf))
        # skip to the end of this episode
        k2=i
        while k2<N and on[k2]: k2+=1
        i=k2
    else: i+=1
for i,f0,conf in seen:
    d0=cal[i]; nearest=min(PK,key=lambda p:abs((d0-p).days))
    lab=str(nearest.date())[:7] if abs((d0-nearest).days)<400 else "— none —"
    if conf:
        j,c=conf; print("%-10s %-12s %-8s %-12s %-8s %d" % (lab,str(d0.date()),GRP[f0],str(cal[j].date()),GRP[c],(cal[j]-d0).days))
        gaps.append((lab,(cal[j]-d0).days))
    else:
        print("%-10s %-12s %-8s %-12s %-8s %s" % (lab,str(d0.date()),GRP[f0],"NEVER","-","withdrawn"))
        gaps.append((lab,None))
print("\nconfirmation windows: how many of the nine survive, and the lag cost")
for X in [30,45,60,90,120,180,270,365]:
    ok=sum(1 for l,g in gaps if g is not None and g<=X and l!="— none —")
    print("   X=%3dd  confirmed episodes %d/%d  max gap used %s" %
          (X, ok, sum(1 for l,g in gaps if l!="— none —"),
           max([g for l,g in gaps if g is not None and g<=X and l!="— none —"], default=0)))
json.dump([[l,g] for l,g in gaps], open("stage69_gaps.json","w"))
