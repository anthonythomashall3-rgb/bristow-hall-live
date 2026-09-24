"""Stage 21b: conjunction search for a December-1973 trigger with zero false alarms. Every monthly first-print signal (ALFRED vintages
with data by 1973) and weekly claims/IUR signal that fires on a release in Oct-Dec 1973 is paired with every other; a pair is 'on'
when both are on (monthly signals stay on 40 days after release, weekly 12 days). Zero false-alarm pairs are listed with the
recessions they catch within +-1 month (release month vs NBER peak month)."""
exec(open("stage21a_1973.py").read().split("hits=[]")[0])
cal=pd.date_range("1962-01-01","2026-08-31",freq="D"); N=len(cal)
def wk(sig, lag): s=sig.copy(); s.index=s.index+pd.Timedelta(days=lag); return s
gate_d=gate.reindex(cal).ffill().fillna(False).values
def daily(s, hold):
    a=np.zeros(N,bool); idx=cal.searchsorted(s[s].index)
    for i in idx:
        if i<N: a[i:i+hold]=True
    return a
sigs={}
for sid in SER:
    try: t=fp(sid+"_all_vintages.csv")
    except Exception: continue
    rel=pd.to_datetime(t.rel.values)
    for stat in ["d1","d2","d3","d6","dd6","dd12","lvl1","lvl3","up12","up6"]:
        x=t[stat].astype(float)
        qs=[-0.002,-0.003,-0.005,-0.0075,-0.01,-0.015,-0.02,-0.03,-0.05,-0.08,-0.12] if stat in ("d1","d2","d3","d6","dd6","dd12") else [-0.2,-0.3,-0.5,-1,-2,0.2,0.3,0.5,1,2,5,10]
        for q in qs:
            cond=(x<=q) if q<0 else (x>=q)
            if cond.sum()<3 or cond.mean()>0.5: continue
            s=pd.Series(cond.values, index=rel).sort_index()
            w=s[(s.index>="1973-10-01")&(s.index<="1973-12-31")]
            if not w.any(): continue
            sigs[f"{sid} {stat} {'<=' if q<0 else '>='} {q}"]=daily(s,40)
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
for n in [4,6,8,13]:
    m=ic.rolling(n).mean()
    for p in [0.05,0.10,0.15,0.20,0.25]:
        s=wk(m/m.shift(1).rolling(52).min()-1>=p,5); 
        if s[(s.index>="1973-10-01")&(s.index<="1973-12-31")].any(): sigs[f"IC ma{n}>={p}"]=daily(s,12)
    m=cc.rolling(n).mean()
    for p in [0.05,0.10,0.15,0.20]:
        s=wk(m/m.shift(1).rolling(52).min()-1>=p,12)
        if s[(s.index>="1973-10-01")&(s.index<="1973-12-31")].any(): sigs[f"CC ma{n}>={p}"]=daily(s,12)
    m=iur.rolling(n).mean()
    for g in [0.05,0.10,0.15,0.20]:
        s=wk(m-m.shift(1).rolling(52).min()>=g-1e-12,12)
        if s[(s.index>="1973-10-01")&(s.index<="1973-12-31")].any(): sigs[f"IUR ma{n} gap>={g}"]=daily(s,12)
print("signals firing Oct-Dec 1973:", len(sigs))
# allowed mask: [peak-1 month, trough+12 months]; scoring from 1968-06
EPX=[(P(pk),P(tr)) for pk,tr in EP]
allowed=np.zeros(N,bool)
for pk,tr in EPX:
    lo=cal.searchsorted((pk-1).to_timestamp()); hi=cal.searchsorted((tr+12).to_timestamp(how="end"))
    allowed[lo:hi+1]=True
start=cal.searchsorted(pd.Timestamp("1968-06-01"))
names=list(sigs); arrs=[sigs[n]&gate_d for n in names]
def fa_and_catches(a):
    a=a.copy(); a[:start]=False
    d=np.diff(a.astype(np.int8)); starts=np.flatnonzero(d==1)+1
    if a[start]: starts=np.concatenate([[start],starts])
    fa=int((~allowed[starts]).sum())
    catches=[]
    for pk,tr in EPX:
        lo=cal.searchsorted((pk-1).to_timestamp()); hi=cal.searchsorted((pk+1).to_timestamp(how="end"))
        seg=a[lo:hi+1]
        catches.append(str(cal[lo+int(np.argmax(seg))].date()) if seg.any() else None)
    return fa, catches
single=[]
for n,a in zip(names,arrs):
    fa,c=fa_and_catches(a); single.append((n,fa,c))
print("singles with fa<=3:", [(n,fa) for n,fa,c in single if fa<=3])
res=[]
for i in range(len(names)):
    for j in range(i+1,len(names)):
        a=arrs[i]&arrs[j]
        if not a[cal.searchsorted(pd.Timestamp("1973-10-01")):cal.searchsorted(pd.Timestamp("1974-01-01"))].any(): continue
        fa,c=fa_and_catches(a)
        if fa==0: res.append((names[i],names[j],sum(x is not None for x in c),c))
print("zero-false-alarm pairs firing Oct-Dec 1973:", len(res))
res.sort(key=lambda r:-r[2])
for r in res[:40]: print("  ", r[0], "&", r[1], "| within-1 catches", r[2], "|", r[3])
