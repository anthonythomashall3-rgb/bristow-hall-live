"""Stage 97: (a) how much lateness is actually left, (b) can the 1981 call reach the week
of the recession's first day, (c) a wider sweep of Sahm FORMS for margin."""
exec(open("stage96_speed.py").read().split("base=machine(")[0])
import numpy as np, pandas as pd, os, glob
FIRST={"1969-12":"1970-01-01","1973-11":"1973-12-01","1980-01":"1980-02-01","1981-07":"1981-08-01",
       "1990-07":"1990-08-01","2001-03":"2001-04-01","2007-12":"2008-01-01","2020-02":"2020-03-01","2024-04":"2024-05-01"}
print("v10: days from the recession's first day")
for k,v in FIRST.items():
    cur=pd.Timestamp(dict(zip([x[:7] for x in ["1969-12","1973-11","1980-01","1981-07","1990-07","2001-03","2007-12","2020-02","2024-04"]],REF))[k])
    print("   %s  call %s  %+d days" % (k,cur.date(),(cur-pd.Timestamp(v)).days))
print("\n(b) what could call July 1981 inside the week of 1 Aug 1981 (25 Jul - 8 Aug)?")
W=(cal>=pd.Timestamp("1981-07-25"))&(cal<=pd.Timestamp("1981-08-08"))&G
PKS=[(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]
def eval_stat(v,nm,rows):
    q=v[QC&CO&G]; q=q[np.isfinite(q)]
    w=v[W&CO]; w=w[np.isfinite(w)]
    if len(q)<400 or len(w)<3: return
    qm=float(np.max(q)); pk=float(np.max(w))
    if pk<=qm: return
    line=(qm+pk)/2; sdv=float(np.nanstd(q))
    if sdv<=0: return
    a=np.asarray(np.nan_to_num(v,nan=-9)>=line,bool)&CO&G
    if (a&QC).any(): return
    got=[]
    for (p,t) in PKS:
        m=a&(cal>=p-pd.DateOffset(months=6))&(cal<=t)
        if m.any():
            d=cal[m][0]; got.append((str(p.date())[:7],(d.year-p.year)*12+(d.month-p.month),str(d.date())))
    hit=[g for g in got if g[0]=="1981-07"]
    if not hit or hit[0][1] not in (0,1): return
    dd=(pd.Timestamp(hit[0][2])-pd.Timestamp("1981-08-01")).days
    if abs(dd)>7: return
    rows.append(((pk-qm)/sdv,nm,line,dd,got))
rows=[]
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched")
files=glob.glob(BASE+"/fred_daily/*.csv")+glob.glob(BASE+"/fred_weekly/*.csv")+glob.glob(BASE+"/extra/*.csv")
def load1(p):
    try:
        x=pd.read_csv(p); x.columns=["date","v"]; x["date"]=pd.to_datetime(x["date"])
        x=x[pd.to_numeric(x["v"],errors="coerce").notna()]
        s=pd.Series(x["v"].astype(float).values,index=pd.DatetimeIndex(x["date"].values)).sort_index()
        return s[~s.index.duplicated()]
    except Exception: return None
eval_stat(sd(iur4-iur4.rolling(52).min(),12),"IUR 4wk gap",rows)
eval_stat(sd(iur.rolling(2).mean()-iur.rolling(2).mean().rolling(52).min(),12),"IUR 2wk gap",rows)
eval_stat(sd(r8,5),"claims 8wk ratio",rows)
eval_stat(Srel.reindex(cal).ffill().values.astype(float),"Sahm",rows)
n=0
for p in files:
    s=load1(p)
    if s is None or len(s)<3000 or s.index[0]>pd.Timestamp("1980-06-01"): continue
    nm=os.path.basename(p)[:-4]; n+=1
    for lab,st in [("%s 20d fall"%nm,-(s-s.shift(20))),("%s 60d fall"%nm,-(s-s.shift(60))),
                   ("%s 20d rise"%nm,s-s.shift(20)),("%s 60d rise"%nm,s-s.shift(60))]:
        eval_stat(sd(st,1),lab,rows)
rows.sort(reverse=True)
print("   scanned %d saved series; candidates: %d" % (n,len(rows)))
for m,nm,line,dd,got in rows[:12]:
    print("   %-34s line %8.3f  1981 call %+d days from 1 Aug  margin %.2f sd  carries %s" %
          (nm,line,dd,m,[g[0] for g in got]))
if not rows: print("   nothing fires in that window with a clean quiet record")
