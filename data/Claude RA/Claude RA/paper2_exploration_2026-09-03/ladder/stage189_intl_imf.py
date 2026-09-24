"""Stage 189: the international test rebuilt on Eurostat and the OECD.  The old test was limited
to the twelve to sixteen countries for which FRED still carries an OECD harmonised unemployment
rate.  Eurostat and the OECD's own service between them carry unemployment, industrial
production, retail sales, consumer confidence and construction for thirty to forty countries
each, with quarterly GDP for forty-two.  The rule is unchanged -- every line is that country's own
quiet record plus a quarter of that country's own robust standard deviation."""
import os, numpy as np, pandas as pd, glob
D=os.environ.get("INTL_DIR","/root/fetch/")
if not os.path.isdir(D+"eurostat"): D=os.path.expanduser("~/mnt/Onset Detector Data/28_intl_expansion_2026-09/")
I2TO3={"AT":"AUT","BE":"BEL","BG":"BGR","CH":"CHE","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK",
 "EE":"EST","EL":"GRC","ES":"ESP","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN","IE":"IRL",
 "IS":"ISL","IT":"ITA","LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT","NL":"NLD","NO":"NOR",
 "PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE","SI":"SVN","SK":"SVK","TR":"TUR","UK":"GBR",
 "RS":"SRB","ME":"MNE","MK":"MKD","AL":"ALB","BA":"BIH","XK":"XKX"}
def rd(p):
    s=pd.read_csv(p,parse_dates=["date"]).set_index("date")["value"]
    return pd.to_numeric(s,errors="coerce").dropna().sort_index()
def load_all():
    out={}
    for src,sub,name in [("eurostat","unemployment","unemployment"),("eurostat","production","production"),
                         ("eurostat","retail","retail"),("eurostat","consumer_confidence","consumer confidence"),
                         ("eurostat","construction","construction")]:
        for p in glob.glob(D+src+"/"+sub+"/*.csv"):
            g=os.path.basename(p)[:-4]
            iso=I2TO3.get(g)
            if iso is None: continue
            out.setdefault(iso,{}).setdefault(name,rd(p))
    I2={"US":"USA","JP":"JPN","GB":"GBR","DE":"DEU","FR":"FRA","IT":"ITA","ES":"ESP","CA":"CAN",
        "AU":"AUS","NZ":"NZL","KR":"KOR","MX":"MEX","TR":"TUR","ZA":"ZAF","BR":"BRA","IN":"IND",
        "ID":"IDN","RU":"RUS","CN":"CHN","AR":"ARG","CL":"CHL","CO":"COL","IL":"ISR","NO":"NOR",
        "CH":"CHE","SE":"SWE","DK":"DNK","FI":"FIN","NL":"NLD","BE":"BEL","AT":"AUT","PT":"PRT",
        "GR":"GRC","IE":"IRL","PL":"POL","HU":"HUN","CZ":"CZE","SK":"SVK","SI":"SVN","EE":"EST",
        "LV":"LVA","LT":"LTU","LU":"LUX","IS":"ISL","MY":"MYS","TH":"THA","PH":"PHL","SG":"SGP",
        "HK":"HKG","TW":"TWN","PK":"PAK","EG":"EGY","MA":"MAR","NG":"NGA","PE":"PER","UY":"URY"}
    for sub,name in [("production","imf production"),("retail","imf retail"),("unemployment","imf unemployment")]:
        for p in glob.glob(D.replace("/root/fetch/","/root/fetch/")+"imf/"+sub+"/*.csv"):
            iso=I2.get(os.path.basename(p)[:-4])
            if iso is None: continue
            out.setdefault(iso,{})
            if name not in out[iso]: out[iso][name]=rd(p)
    for sub,name in [("unemployment","unemployment"),("production","production"),("retail","retail")]:
        for p in glob.glob(D+"oecd/"+sub+"/*.csv"):
            iso=os.path.basename(p)[:-4]
            out.setdefault(iso,{})
            if name not in out[iso]: out[iso][name]=rd(p)
    G={}
    for p in glob.glob(D+"eurostat/gdp_q/*.csv"):
        iso=I2TO3.get(os.path.basename(p)[:-4])
        if iso: G[iso]=rd(p)
    return out,G
CH,GDP=load_all()
FR=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/intl/")
EU3={v:k for k,v in I2TO3.items()}
for iso in list(CH):
    if iso in GDP: continue
    for pat in ["NGDPRSAXDC%sQ.csv"%{"USA":"US","JPN":"JP","KOR":"KR","MEX":"MX","TUR":"TR","ZAF":"ZA","CAN":"CA","AUS":"AU","ITA":"IT","POL":"PL","CHL":"CL","ISR":"IL","NZL":"NZ","BRA":"BR","IND":"IN","RUS":"RU","COL":"CO","ISL":"IS","NOR":"NO","CHE":"CH"}.get(iso,"XX"),
                "NAEXKP01%sQ652S.csv"%{"USA":"US","JPN":"JP","KOR":"KR","MEX":"MX","TUR":"TR","ZAF":"ZA","CAN":"CA","AUS":"AU","NZL":"NZ","NOR":"NO","CHE":"CH","ISL":"IS","CHL":"CL","ISR":"IL"}.get(iso,"XX"),
                "GDPC1.csv" if iso=="USA" else "XX"]:
        p=FR+pat
        if os.path.exists(p):
            x=pd.read_csv(p); x.columns=["date","v"]
            s=pd.Series(pd.to_numeric(x["v"],errors="coerce").values,index=pd.to_datetime(x["date"])).dropna()
            if len(s)>=40: GDP[iso]=s; break
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
def build(iso,delta=0.25,floor=0.30,post=9):
    S={}; ch=CH[iso]
    if not ch: return None
    lo=min(s.index.min() for s in ch.values()); hi=max(s.index.max() for s in ch.values())
    idx=pd.DatetimeIndex(pd.date_range(lo,hi,freq="MS"))
    for un in ["unemployment","imf unemployment"]:
        if un in ch:
            u=ch[un].reindex(idx).interpolate(limit_area="inside")
            S[un]=u.rolling(3).mean()-u.rolling(12).min()
    for nm,k in [("production","production"),("retail","retail"),("construction","construction"),
                 ("imf production","imf production"),("imf retail","imf retail")]:
        if nm in ch:
            v=ch[nm].reindex(idx,method="ffill"); d1=-(v/v.shift(1)-1)*100
            S[k]=pd.concat([d1,d1.shift(1)],axis=1).min(axis=1)
            S[k+" 3m"]=-(v/v.shift(3)-1)*100
    if "consumer confidence" in ch:
        c=ch["consumer confidence"].reindex(idx,method="ffill"); S["confidence"]=-(c-c.shift(3))
    g=GDP.get(iso)
    if g is None or len(g)<40: return None
    glo=pd.Timestamp(g.index.min())+pd.DateOffset(months=6); ghi=pd.Timestamp(g.index.max())
    lo2=max(idx[0],glo); hi2=min(idx[-1],ghi)
    eps=[(P,T) for P,T in technical(g) if P>=lo2 and T<=hi2]
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=post)))
    ufl=pd.Series(True,index=idx); have=None
    if "unemployment" in S:
        f=(S["unemployment"]>=floor).reindex(idx).fillna(False); have=S["unemployment"].notna().reindex(idx).fillna(False)
        ufl=(f|(~have)).rolling(6,min_periods=1).max().fillna(0).astype(bool)
    hit=pd.Series(False,index=idx); nch=0
    for k,x in S.items():
        v=x[q].dropna()
        if len(v)<36: continue
        med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
        if not np.isfinite(mad) or mad<=0: continue
        z=(x-med)/mad; rec=float(z[q].dropna().max())
        hit=hit|((z>=rec+delta).reindex(idx).fillna(False)); nch+=1
    if nch==0: return None
    trig=(hit&ufl).reindex(idx).fillna(False)
    hits=[h for h in idx[trig.values] if lo2<=h<=hi2]
    rows=[]
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=post) for h in hits)
        rows.append((iso,str(P.date())[:7],depth(g,P,T),got))
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=post) for P,T in eps)]
    return rows,fa,float(q[(idx>=lo2)&(idx<=hi2)].sum())/12.0,nch
DELTA=float(os.environ.get("DELTA","0.25"))
ALL=[];FA=[];Y=0.0;NC={}
for iso in sorted(CH):
    r=build(iso,delta=DELTA)
    if r is None: continue
    rows,fa,qy,nch=r; ALL+=rows; FA+=[(iso,x) for x in fa]; Y+=qy; NC[iso]=(nch,len(rows),sum(1 for x in rows if x[3]),len(fa))
print("%-5s %-6s %-9s %s"%("iso","chans","detected","false"))
for iso,(nch,n,d,f) in sorted(NC.items()):
    if n or f: print("%-5s %-6d %-9s %d"%(iso,nch,"%d/%d"%(d,n),f))
df=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
print("\ncountries %d | episodes %d | quiet country-years %.0f"%(len(NC),len(df),Y))
for lo,lab in [(-1e9,"every two-quarter dip"),(-2.0,"output fell more than 2 per cent"),(-4.0,"output fell more than 4 per cent")]:
    s=df if lo<-1e8 else df[df.depth<=lo]
    print("%-38s %d of %d (%.0f%%)"%(lab,s.found.sum(),len(s),100*s.found.mean()))
print("false alarms: %d in %.0f quiet country-years"%(len(FA),Y))
if FA: print("  ",FA[:12])
