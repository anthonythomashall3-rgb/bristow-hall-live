"""Stage 27: margin scan. For every candidate statistic (economically signed: larger = worse), and every recession r, compute
R_r = worst reading on releases inside [peak-1, peak+1] months, and Q = worst reading in gated quiet periods (outside [peak-2, trough+12]
of every episode, 1968-2026, 2024 = Apr-Aug). A threshold t with Q < t <= R_r calls r inside +-1 month with zero false alarms.
Margin_r = (R_r - Q) / sd(quiet readings). Rank statistics by recessions covered and worst margin. Purpose: wide channels."""
exec(open("stage21a_1973.py").read().split("hits=[]")[0])
cal=pd.date_range("1962-01-01","2026-08-31",freq="D"); N=len(cal)
def wk(sig, lag): s=sig.copy(); s.index=s.index+pd.Timedelta(days=lag); return s
gate_d=gate.reindex(cal).ffill().fillna(False).values
EPX=[(P(pk),P(tr)) for pk,tr in EP]
allowed=np.zeros(N,bool)
for pk,tr in EPX:
    lo=cal.searchsorted((pk-2).to_timestamp()); hi=cal.searchsorted((tr+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
quiet=(~allowed)&gate_d&(cal>=pd.Timestamp("1968-06-01"))
wins=[]
for pk,tr in EPX:
    lo=cal.searchsorted((pk-1).to_timestamp()); hi=cal.searchsorted((pk+1).to_timestamp(how="end")); wins.append((lo,hi))
def evaluate(name, s, hold):
    """s: Series indexed by release date, larger = worse. hold: days a release stays current."""
    v=np.full(N,np.nan); idx=cal.searchsorted(s.index); 
    for i,x in zip(idx,s.values):
        if i<N: v[i:i+hold]=x
    q=v[quiet]; q=q[~np.isnan(q)]
    if len(q)<100: return None
    Q=q.max(); sd=q.std()+1e-12
    R=[]
    for lo,hi in wins:
        w=v[lo:hi+1]; w=w[~np.isnan(w)]
        R.append(w.max() if len(w) else np.nan)
    marg=[(r-Q)/sd if not np.isnan(r) else np.nan for r in R]
    cov=[i for i,m in enumerate(marg) if not np.isnan(m) and m>0]
    return dict(stat=name, Q=round(Q,3), sd=round(sd,3), covered=len(cov), which=[EP[i][0][:4] for i in cov], min_margin=round(min(marg[i] for i in cov),2) if cov else None, margins=[round(m,2) if not np.isnan(m) else None for m in marg])
rows=[]
# ---- monthly first prints (ALFRED), economically signed ----
BAD_UP={"UNRATE","UEMPMEAN","UNEMPLOY","LNS13023705","LNS13023621","LNS13026511","LNS13023653","LNS13025699","UEMP15OV","UEMP27OV","UEMPLT5","U6RATE"}
import glob
files=sorted(glob.glob(A+"*_all_vintages.csv"))
for f in files:
    sid=os.path.basename(f).replace("_all_vintages.csv","")
    try: t=fp(sid+"_all_vintages.csv")
    except Exception: continue
    if len(t)<60: continue
    rel=pd.to_datetime(t.rel.values)
    for stat in ["d1","d2","d3","d6","dd6","dd12","lvl1","lvl3","up12","up6"]:
        x=t[stat].astype(float).values
        sign = 1 if sid in BAD_UP else -1
        if stat in ("up12","up6") and sid not in BAD_UP: continue   # rises of a good series are not deterioration
        if stat in ("dd6","dd12","d1","d2","d3","d6") and sid in BAD_UP: sign=1
        s=pd.Series(sign*x, index=rel).sort_index()
        r=evaluate(f"{sid} {stat}{'(+)' if sign>0 else '(-)'}", s, 40)
        if r: rows.append(r)
# ---- weekly claims / IUR family ----
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
icn=load(ODD+"01_labor_unemployment/weekly/ICNSA.csv"); ccn=load(ODD+"01_labor_unemployment/weekly/CCNSA.csv")
for n in [4,8,13]:
    m=ic.rolling(n).mean(); rows.append(evaluate(f"IC ma{n} vs 52wk min", wk(m/m.shift(1).rolling(52).min()-1,5), 10))
    rows.append(evaluate(f"IC ma{n} vs ma52", wk(m/ic.rolling(52).mean()-1,5), 10))
    rows.append(evaluate(f"IC ma{n} yoy (NSA)", wk(np.log(icn.rolling(n).mean()/icn.rolling(n).mean().shift(52)),5), 10))
    m=cc.rolling(n).mean(); rows.append(evaluate(f"CC ma{n} vs 52wk min", wk(m/m.shift(1).rolling(52).min()-1,12), 10))
    rows.append(evaluate(f"CC ma{n} yoy (NSA)", wk(np.log(ccn.rolling(n).mean()/ccn.rolling(n).mean().shift(52)),12), 10))
    m=iur.rolling(n).mean(); rows.append(evaluate(f"IUR ma{n} gap vs 52wk min", wk(m-m.shift(1).rolling(52).min(),12), 10))
    rows.append(evaluate(f"IUR ma{n} yoy", wk(m-m.shift(52),12), 10))
i4=icn.rolling(4).mean(); c4=ccn.rolling(4).mean().shift(1)
rows.append(evaluate("NSA yoy conjunct min(IC,CC)", wk(pd.concat([np.log(i4/i4.shift(52)), np.log(c4/c4.shift(52))],axis=1).min(axis=1),12), 10))
# ---- state breadth (ETA 539, 1986->) ----
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c3","c8","c19"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
iur_st=d.pivot_table(index="c2", columns="st", values="c19", aggfunc="max").sort_index(); m4=iur_st.rolling(4).mean()
for g in [0.2,0.3,0.5]: rows.append(evaluate(f"states with IUR 4wk yoy >= {g}", wk((m4-m4.shift(52)>=g).sum(axis=1),9), 10))
cw=d.pivot_table(index="c2", columns="st", values="c8", aggfunc="sum").sort_index(); s8=cw.rolling(8).sum(); g8=s8/s8.shift(52)-1
for p in [0.10,0.20]: rows.append(evaluate(f"states with CC 8wk yoy >= {int(p*100)}%", wk((g8>=p).sum(axis=1),9), 10))
rows=[r for r in rows if r]
df=pd.DataFrame(rows); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",400)
df.to_csv("stage27_margins.csv", index=False)
print("statistics scanned:", len(df))
print("\n=== channels that call >=3 recessions inside +-1 with zero false alarms, by worst margin (sd units) ===")
print(df[df.covered>=3].sort_values(["covered","min_margin"], ascending=[False,False]).head(40).to_string())
for yr in ["1969","1973","1980","1981","1990","2001","2007","2020","2024"]:
    sub=df[df.which.apply(lambda w: yr in w)].copy(); sub["m"]=sub.apply(lambda r: r.margins[[e[0][:4] for e in EP].index(yr)], axis=1)
    print(f"\n--- widest channels for {yr} (margin in quiet-sd units) ---"); print(sub.sort_values("m", ascending=False).head(8)[["stat","Q","sd","m","covered","which"]].to_string())
