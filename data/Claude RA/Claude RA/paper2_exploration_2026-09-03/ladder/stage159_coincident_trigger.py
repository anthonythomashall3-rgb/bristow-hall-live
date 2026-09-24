"""Stage 159: which object crosses closest to the recession's own first day?  Every earlier
search maximised speed, which pushes the call earlier and earlier; four of v14's nine calls are
now more than a month EARLY.  'Within the week' is a different objective: the call should land on
the recession's first day, not before it.  That needs a COINCIDENT trigger, and this stage looks
for one -- sweeping weekly and daily objects and asking, for each, how many of the nine first
crossings inside the episode window land within seven days of the first day of the recession."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
def gapser(s,w,lag=5):
    m=s.rolling(w).mean(); r=m/m.shift(1).rolling(52).min()-1
    return sd(r,lag)
def levser(s,w,lag=5):
    m=s.rolling(w).mean(); r=m-m.shift(1).rolling(52).min()
    return sd(r,lag)
CANDS={}
for w in [4,6,8,10,13,17,26]:
    CANDS["initial claims %dwk above its year low"%w]=gapser(ic,w)
    CANDS["continued claims %dwk above its year low"%w]=gapser(cc,w)
for w in [4,8,13]:
    CANDS["insured rate %dwk above its year low"%w]=levser(iur,w,12)
CANDS["Sahm first print"]=Srel.reindex(cal).ffill().values.astype(float)
CANDS["payroll first print, one-month fall"]=-sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
CANDS["bill, 60-day fall"]=sd(-(tb6-tb6.shift(60)),1)
CANDS["VIX, 20-day change"]=sd(vix-vix.shift(20),1)
QUIET=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
WIN=[((pd.Period(p,"M")-6).to_timestamp(),(pd.Period(t,"M")+3).to_timestamp(how="end")) for p,t in T_P1]
def cross_days(v,th):
    out=[]
    for i,(a,b) in enumerate(WIN):
        sel=np.flatnonzero((cal>=a)&(cal<=b)&np.isfinite(v)&(v>=th))
        out.append(None if len(sel)==0 else (cal[sel[0]]-FIRST[i]).days)
    return out
rows=[]
for nm,v in CANDS.items():
    v=np.asarray(v,float)
    qv=v[QUIET]; qv=qv[np.isfinite(qv)]
    if len(qv)<500: continue
    qmax=float(np.max(qv))
    lo=float(np.nanpercentile(v[np.isfinite(v)],50))
    for th in np.unique(np.round(np.linspace(lo,max(qmax*2.5,lo+1e-6),60),5)):
        d=cross_days(v,th)
        if any(x is None for x in d): continue
        nfalse=int((QUIET&np.isfinite(v)&(v>=th)).sum())
        rows.append(dict(obj=nm,th=float(th),inwk=sum(1 for x in d if abs(x)<=7),
                         within31=sum(1 for x in d if abs(x)<=31),
                         mad=float(np.mean(np.abs(d))),quietdays=nfalse,
                         abovequiet=th>qmax,d=d))
df=pd.DataFrame(rows)
print("ALL NINE CROSSED, ranked by how many land within a week of the recession's first day")
print("(quiet days = days outside every episode window on which the object is already above the line)")
print("%-44s %-9s %-6s %-7s %-8s %-9s %s"%("object","threshold","in wk","<=1 mo","mean|d|","quiet days","days from the first day"))
for _,r in df.sort_values(["inwk","mad"],ascending=[False,True]).head(18).iterrows():
    print("%-44s %-9.4f %-6d %-7d %-8.0f %-9d %s"%(r.obj,r.th,r.inwk,r.within31,r.mad,r.quietdays,r.d))
print("\nsame, but only lines that no quiet day has ever reached")
d2=df[df.quietdays==0]
if len(d2):
    for _,r in d2.sort_values(["inwk","mad"],ascending=[False,True]).head(12).iterrows():
        print("%-44s %-9.4f %-6d %-7d %-8.0f %s"%(r.obj,r.th,r.inwk,r.within31,r.mad,r.d))
else: print("  none")
df.to_csv("/root/out/stage159.csv",index=False)
print("\nv14 for reference: days [-87, -37, -29, 17, 2, -58, -14, -2, 2], three within a week")
