"""Stage 182: can the advance date come a month sooner?  The advance panel waits on real income,
which prints thirty days after the month ends.  Payrolls print at seven days and industrial
production at seventeen, so a two-series panel is ready thirteen days earlier -- and possibly a
whole month earlier in horizon terms.  This asks what each panel can do at each horizon."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd
P17=[n for n in ["payrolls","industrial production"] if n in M]
P30=[n for n in ["payrolls","industrial production","real income less transfers"] if n in M]
P47=list(FOUR)
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def med_p(names,anchor,asof,back,fwd,kind,how):
    o=[]
    for nm in names:
        d=turn(nm,anchor,asof,back,fwd,kind)
        if d is not None: o.append(d.to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    return pd.Period(ordinal=(int(np.floor(x)) if how=="earlier" else int(round(x))),freq="M")
KS=[1,2,3,4,6]
for lab,anch,ref,kind,wins in [("PEAK",ALARM,PKM,"max",[(180,30),(180,60),(240,30)]),
                               ("TROUGH",ENDC2,TRM,"min",[(300,30),(300,60),(365,30)])]:
    print("\n%s — exact months, by panel and horizon"%lab)
    print("%-34s %-10s %-9s %s"%("panel","slowest","window"," ".join("%5d mo"%k for k in KS)))
    for pn,names,slow in [("payrolls + production",P17,17),("plus real income",P30,30),("all four",P47,47)]:
        for back,fwd in wins:
            for how in ["nearest"]:
                row=[]
                for k in KS:
                    n=0
                    for i,a in enumerate(anch):
                        d=med_p(names,a,a+pd.DateOffset(months=k),back,fwd,kind,how)
                        if d is not None and (d-pd.Period(ref[i],"M")).n==0: n+=1
                    row.append(n)
                print("%-34s %-10d %-9s %s"%(pn,slow,"%d/%d"%(back,fwd)," ".join("%5d  "%v for v in row)))
