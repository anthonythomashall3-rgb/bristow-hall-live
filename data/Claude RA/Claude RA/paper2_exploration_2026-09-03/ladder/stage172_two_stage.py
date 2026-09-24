"""Stage 172: an advance date and a final date.  The statistical agencies publish an advance
estimate and revise it; the dating step should do the same, because a short window gives an
answer sooner and a long one gives a better answer, and no single window does both.  This stage
reports what each of the two would have said, and when."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd
def date_at(anch,asof,back,fwd,kind,how):
    return med(anch,asof,back,fwd,kind,how)
print("PEAK")
print("%-9s %-12s %-22s %-22s %s"%("NBER","alarm","advance (2 months on)","final (9 months on)","final window date"))
adv=[];fin=[]
for i,a in enumerate(ALARM):
    p1=date_at(a,a+pd.DateOffset(months=2),180,30,"max","nearest")
    p2=date_at(a,a+pd.DateOffset(months=9),120,180,"max","earlier")
    e1=None if p1 is None else (p1-pd.Period(PKM[i],"M")).n
    e2=None if p2 is None else (p2-pd.Period(PKM[i],"M")).n
    adv.append(e1); fin.append(e2)
    print("%-9s %-12s %-22s %-22s %s"%(PKM[i],str(a.date()),
        "%s (%+d)"%(p1,e1) if p1 else "-", "%s (%+d)"%(p2,e2) if p2 else "-",
        str((a+pd.DateOffset(months=9)).date())))
print("  advance exact %d of 9, within one month %d | final exact %d of 9, within one month %d"%(
    sum(1 for x in adv if x==0),sum(1 for x in adv if x is not None and abs(x)<=1),
    sum(1 for x in fin if x==0),sum(1 for x in fin if x is not None and abs(x)<=1)))
print("\nTROUGH")
print("%-9s %-12s %-24s %s"%("NBER","end call","advance (1 month on)","date it is available"))
adt=[]
for i,a in enumerate(ENDC2):
    t1=date_at(a,a+pd.DateOffset(months=1),300,30,"min","nearest")
    e1=None if t1 is None else (t1-pd.Period(TRM[i],"M")).n
    adt.append(e1)
    print("%-9s %-12s %-24s %s"%(TRM[i],str(a.date()),"%s (%+d)"%(t1,e1) if t1 else "-",
        str((a+pd.DateOffset(months=1)).date())))
print("  advance exact %d of 9, within one month %d"%(
    sum(1 for x in adt if x==0),sum(1 for x in adt if x is not None and abs(x)<=1)))
print("\nhow long after the turning point itself the advance date is available")
for i in range(9):
    pk=pd.Period(PKM[i],"M").to_timestamp(how="end"); tr=pd.Period(TRM[i],"M").to_timestamp(how="end")
    ap=(ALARM[i]+pd.DateOffset(months=2)-pk).days; at=(ENDC2[i]+pd.DateOffset(months=1)-tr).days
    print("  %-9s peak dated %4d days after the peak month ends | trough dated %4d days after the trough month ends"%(PKM[i],ap,at))
