"""Stage 177: the one-per-cent end rule and the dates it yields.  Ten weeks at one per cent
splits the 2020 episode and raises a false alarm, so it is out.  Eight weeks at one per cent --
the current smoothing, a looser trigger -- keeps nine episodes and no false alarm while calling
the end one to seven weeks earlier.  This checks the trough dates that follow from it."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd
FASTP=[n for n in ["payrolls","industrial production","real income less transfers"] if n in M]
ALL4=list(FOUR)
OLD=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                               "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
NEW=[pd.Timestamp(x) for x in ["1970-11-26","1975-03-20","1980-07-17","1982-11-11","1991-04-25",
                               "2001-11-29","2009-04-30","2020-05-14","2024-09-12"]]
def med_p(names,anchor,asof,back,fwd,kind,how="nearest"):
    o=[]
    for nm in names:
        d=turn(nm,anchor,asof,back,fwd,kind)
        if d is not None: o.append(d.to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    return pd.Period(ordinal=(int(np.floor(x)) if how=="earlier" else int(round(x))),freq="M")
def report(lab,ends):
    adv=[];fin=[];days=[]
    for i,e in enumerate(ends):
        a=med_p(FASTP,e,e+pd.DateOffset(months=1),300,30,"min")
        f=med_p(ALL4,e,e+pd.DateOffset(months=9),300,30,"min")
        adv.append(None if a is None else (a-pd.Period(TRM[i],"M")).n)
        fin.append(None if f is None else (f-pd.Period(TRM[i],"M")).n)
        days.append((e+pd.DateOffset(months=1)-pd.Period(TRM[i],"M").to_timestamp(how="end")).days)
    okA=[x for x in adv if x is not None]; okF=[x for x in fin if x is not None]
    print("%-22s advance exact %d of 9 (<=1 mo %d) %s"%(lab,sum(1 for x in okA if x==0),sum(1 for x in okA if abs(x)<=1),adv))
    print("%-22s final   exact %d of 9 (<=1 mo %d) %s"%("",sum(1 for x in okF if x==0),sum(1 for x in okF if abs(x)<=1),fin))
    print("%-22s advance available %s days after the trough month ends, median %.0f"%("",days,float(np.median(days))))
report("end at 3 per cent",OLD)
print()
report("end at 1 per cent",NEW)
print("\nhow much earlier the end call itself arrives")
for i in range(9):
    print("  %-9s %s -> %s  (%d days earlier)"%(TRM[i],OLD[i].date(),NEW[i].date(),(OLD[i]-NEW[i]).days))
