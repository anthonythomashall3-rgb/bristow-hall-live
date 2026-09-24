"""Stage 192: the same engine abroad.  Identical code to the American runs of stage 190 -- the
same five steps, the same margin -- on each country's own Eurostat, OECD and IMF series, scored
against two consecutive negative quarters of its own real GDP inside its own GDP record."""
import os, sys, glob
import numpy as np, pandas as pd
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import recession_engine as E
FE="/root/fetch/"
I2TO3={"AT":"AUT","BE":"BEL","BG":"BGR","CH":"CHE","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK","EE":"EST",
"EL":"GRC","ES":"ESP","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN","IE":"IRL","IS":"ISL","IT":"ITA",
"LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT","NL":"NLD","NO":"NOR","PL":"POL","PT":"PRT","RO":"ROU",
"SE":"SWE","SI":"SVN","SK":"SVK","TR":"TUR","UK":"GBR","RS":"SRB","ME":"MNE","MK":"MKD","AL":"ALB",
"BA":"BIH","XK":"XKX","US":"USA","JP":"JPN","GB":"GBR","CA":"CAN","AU":"AUS","NZ":"NZL","KR":"KOR",
"MX":"MEX","ZA":"ZAF","BR":"BRA","IN":"IND","ID":"IDN","RU":"RUS","CN":"CHN","AR":"ARG","CL":"CHL",
"CO":"COL","IL":"ISR","MY":"MYS","TH":"THA","PH":"PHL","SG":"SGP","HK":"HKG","TW":"TWN","PK":"PAK",
"EG":"EGY","MA":"MAR","NG":"NGA","PE":"PER","UY":"URY"}
def rd(p):
    d=pd.read_csv(p); d.columns=[c.lower() for c in d.columns]
    s=pd.Series(pd.to_numeric(d[d.columns[1]],errors="coerce").values,index=pd.to_datetime(d[d.columns[0]],errors="coerce"))
    return s[s.index.notna()].dropna().sort_index()
SER={}; GDP={}
def add(iso,name,s,kind):
    if s is None or len(s)<60: return
    SER.setdefault(iso,{})
    if name not in SER[iso]: SER[iso][name]=(s,kind)
for sub,nm,kind in [("unemployment","unemployment","level"),("production","production","activity"),
                    ("retail","retail","activity"),("consumer_confidence","confidence","level"),
                    ("construction","construction","activity")]:
    for p in glob.glob(FE+"eurostat/"+sub+"/*.csv"):
        iso=I2TO3.get(os.path.basename(p)[:-4])
        if iso: add(iso,"eurostat "+nm,rd(p),kind)
for sub,nm,kind in [("unemployment","unemployment","level"),("production","production","activity"),("retail","retail","activity")]:
    for p in glob.glob(FE+"oecd/"+sub+"/*.csv"):
        add(os.path.basename(p)[:-4],"oecd "+nm,rd(p),kind)
for sub,nm,kind in [("production","production","activity"),("production_nsa","production nsa","activity"),
                    ("retail","retail","activity"),("unemployment","unemployment","level"),("employment","employment","activity")]:
    for p in glob.glob(FE+"imf/"+sub+"/*.csv"):
        iso=I2TO3.get(os.path.basename(p)[:-4])
        if iso: add(iso,"imf "+nm,rd(p),kind)
LEVELKEY=("confidence_BS-","unemployment")
for d in glob.glob(FE+"eurostat_deep/*"):
    iso=I2TO3.get(os.path.basename(d))
    if iso is None: continue
    for p in glob.glob(d+"/*.csv"):
        nm="deep "+os.path.basename(p)[:-4]
        add(iso,nm,rd(p),"level" if any(k in nm for k in LEVELKEY) else "activity")
for p in glob.glob(FE+"eurostat/gdp_q/*.csv"):
    iso=I2TO3.get(os.path.basename(p)[:-4])
    if iso: GDP[iso]=rd(p)
FR=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl/")
I3TO2={v:k for k,v in I2TO3.items() if len(k)==2}
for iso in list(SER):
    if iso in GDP: continue
    for pat in ["NGDPRSAXDC%sQ.csv","NAEXKP01%sQ652S.csv","CLVMNACSCAB1GQ%s.csv"]:
        cc=I3TO2.get(iso,"XX"); p=FR+pat%cc
        if os.path.exists(p):
            s=rd(p)
            if len(s)>=40: GDP[iso]=s; break
    if iso=="USA" and os.path.exists(FR+"GDPC1.csv"): GDP[iso]=rd(FR+"GDPC1.csv")
def technical(g):
    r=(g.pct_change()*100).dropna(); neg=(r<0).values; d=list(r.index); eps=[];i=0
    while i<len(neg):
        if neg[i]:
            j=i
            while j+1<len(neg) and neg[j+1]: j+=1
            if j-i+1>=2 and i>=1:
                eps.append(((pd.Timestamp(d[i-1])+pd.DateOffset(months=2)).replace(day=1),
                            (pd.Timestamp(d[j])+pd.DateOffset(months=2)).replace(day=1)))
            i=j+1
        else: i+=1
    return eps
def depth(g,P,T):
    w=g[(g.index>=P-pd.DateOffset(months=6))&(g.index<=T+pd.DateOffset(months=3))]
    return None if len(w)<3 else float((w.min()/w.max()-1)*100)
DELTA=float(os.environ.get("DELTA","0.10"))
rows=[];FA=0;Y=0.0;NC={}
for iso in sorted(SER):
    g=GDP.get(iso)
    if g is None or len(g)<40: continue
    lo=max(min(s.index.min() for s,_ in SER[iso].values()),pd.Timestamp(g.index.min())+pd.DateOffset(months=6))
    hi=min(max(s.index.max() for s,_ in SER[iso].values()),pd.Timestamp(g.index.max()))
    if (hi-lo).days<2500: continue
    idx=pd.DatetimeIndex(pd.date_range(lo,hi,freq="MS"))
    eps=[(P,T) for P,T in technical(g) if P>=lo and T<=hi]
    if not eps: continue
    lab=[k for k in SER[iso] if "unemployment" in k]
    r=E.run(SER[iso],eps,idx,delta=DELTA,labour_names=lab)
    FA+=len(r["false"]); Y+=r["quiet_years"]; NC[iso]=(r["channels"],len(eps),sum(r["detected"]),len(r["false"]))
    for (P,T),d in zip(eps,r["detected"]): rows.append((iso,str(P.date())[:7],depth(g,P,T),d))
df=pd.DataFrame(rows,columns=["iso","peak","depth","found"]).dropna()
print("margin %.2f | countries %d | episodes %d | quiet country-years %.0f"%(DELTA,len(NC),len(df),Y))
for lo_,lab in [(-1e9,"every two-quarter dip"),(-2.0,"output fell over 2 per cent"),(-4.0,"output fell over 4 per cent")]:
    s=df if lo_<-1e8 else df[df.depth<=lo_]
    print("  %-34s %d of %d (%.0f%%)"%(lab,s.found.sum(),len(s),100*s.found.mean()))
print("  false alarms: %d in %.0f quiet country-years"%(FA,Y))
print("\n%-5s %-7s %-9s %s"%("iso","chans","detected","false"))
for iso,(nc,n,d,f) in sorted(NC.items(),key=lambda kv:-kv[1][1])[:18]:
    print("%-5s %-7d %-9s %d"%(iso,nc,"%d/%d"%(d,n),f))
