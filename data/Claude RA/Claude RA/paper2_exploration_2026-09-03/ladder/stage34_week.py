"""Stage 34: within-the-week search. Target T_r = first day of the month after the NBER peak (the recession's first day).
A channel = (statistic, threshold). Threshold set at the gated quiet maximum (strictly above it) so every channel has zero
false alarms by construction. For each channel: first crossing date in [peak-3 months, trough] per recession. A channel is
ADMISSIBLE if it never fires more than 7 days before T_r in any recession (an OR-rule fires at its earliest channel, so one
early channel breaks the week standard). Report, per recession, admissible channels firing inside [T_r-7, T_r+7], and the best
achievable coverage. Same over ALL monthly first prints, the weekly claims/IUR family, state breadth, and ALL fetched daily/weekly
series (both signs), plus ungated variants of the thresholds."""
exec(open("stage27_margins.py").read().split("rows=[]")[0])
import glob, warnings; warnings.filterwarnings("ignore")
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
T=[(pk+1).to_timestamp() for pk,tr in EPX]   # first day after the peak month
lo3=[cal.searchsorted((pk-3).to_timestamp()) for pk,tr in EPX]; hiT=[cal.searchsorted(tr.to_timestamp(how="end")) for pk,tr in EPX]
Ti=[cal.searchsorted(t) for t in T]
def channel_dates(name, s, hold, gated=True):
    v=np.full(N,np.nan); idx=cal.searchsorted(s.index)
    for i,x in zip(idx,s.values):
        if i<N: v[i:i+hold]=x
    qmask=quiet if gated else ((~allowed)&(cal>=pd.Timestamp("1968-06-01")))
    q=v[qmask]; q=q[~np.isnan(q)]
    if len(q)<100: return None
    Q=q.max(); on=v>Q+1e-12
    if gated: on=on&gate_d
    dates=[]; early=False; cover=[]
    for k,(a,b) in enumerate(zip(lo3,hiT)):
        if k==0: dates.append(None); continue   # 1960 not scored
        seg=on[a:b+1]
        if not seg.any(): dates.append(None); continue
        d=a+int(np.argmax(seg)); dates.append(d)
        if d<Ti[k]-7: early=True
        if Ti[k]-7<=d<=Ti[k]+7: cover.append(k)
    return dict(stat=name+(" [gate]" if gated else " [nogate]"), Q=round(Q,4), early=early, dates=[str(cal[d].date()) if d is not None else None for d in dates], days=[(d-Ti[k]) if d is not None else None for k,d in enumerate(dates)], cover=[EP[k][0][:4] for k in cover])
rows=[]
def add(name, s, hold):
    for g in [True,False]:
        r=channel_dates(name, s, hold, g)
        if r: rows.append(r)
# monthly first prints
BAD_UP={"UNRATE","UEMPMEAN","UNEMPLOY","LNS13023705","LNS13023621","LNS13026511","LNS13023653","LNS13025699","U6RATE"}
for f in sorted(glob.glob(A+"*_all_vintages.csv")):
    sid=os.path.basename(f).replace("_all_vintages.csv","")
    try: t=fp(sid+"_all_vintages.csv")
    except Exception: continue
    if len(t)<60: continue
    rel=pd.to_datetime(t.rel.values)
    for stat in ["d1","d2","d3","d6","dd6","dd12","lvl1","lvl3","up12","up6"]:
        x=t[stat].astype(float).values; sign=1 if sid in BAD_UP else -1
        if stat in ("up12","up6") and sid not in BAD_UP: continue
        add(f"{sid} {stat}", pd.Series(sign*x, index=rel).sort_index(), 40)
# weekly claims / IUR / state breadth
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
icn=load(ODD+"01_labor_unemployment/weekly/ICNSA.csv"); ccn=load(ODD+"01_labor_unemployment/weekly/CCNSA.csv")
for n in [2,4,8,13]:
    m=ic.rolling(n).mean(); add(f"IC ma{n} vs 52wk min", wk(m/m.shift(1).rolling(52).min()-1,5), 10); add(f"IC ma{n} vs ma52", wk(m/ic.rolling(52).mean()-1,5), 10)
    add(f"IC ma{n} yoy NSA", wk(np.log(icn.rolling(n).mean()/icn.rolling(n).mean().shift(52)),5), 10)
    m=cc.rolling(n).mean(); add(f"CC ma{n} vs 52wk min", wk(m/m.shift(1).rolling(52).min()-1,12), 10)
    m=iur.rolling(n).mean(); add(f"IUR ma{n} gap", wk(m-m.shift(1).rolling(52).min(),12), 10); add(f"IUR ma{n} yoy", wk(m-m.shift(52),12), 10)
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c3","c8","c19"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
iur_st=d.pivot_table(index="c2", columns="st", values="c19", aggfunc="max").sort_index(); m4=iur_st.rolling(4).mean()
for g in [0.2,0.3,0.5]: add(f"states IUR 4wk yoy>={g}", wk((m4-m4.shift(52)>=g).sum(axis=1),9), 10)
ics=d.pivot_table(index="c2", columns="st", values="c3", aggfunc="sum").sort_index(); s4=ics.rolling(4).sum(); g4=s4/s4.shift(52)-1
for p in [0.2,0.3,0.5]: add(f"states IC 4wk yoy>={int(p*100)}%", wk((g4>=p).sum(axis=1),9), 10)
# daily / weekly fetched series, both signs
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
files=glob.glob(DF+"fred_daily/*.csv")+glob.glob(DF+"fred_weekly/*.csv")+glob.glob(DF+"extra/*.csv")+glob.glob(ODD+"05_financial_conditions/daily/*.csv")
seen=set()
for f in files:
    sid=os.path.basename(f).replace(".csv","")
    if sid in seen or sid.startswith("USREC"): continue
    seen.add(sid)
    try: s=loadfred(f)
    except Exception: continue
    if len(s)<500 or s.index.min()>pd.Timestamp("1995-12-31"): continue
    gap=np.median(np.diff(s.index.values).astype("timedelta64[D]").astype(int))
    if gap<=2: cw=[(5,"5d"),(20,"20d"),(60,"60d"),(120,"120d")]; lag=1; hold=5; L=250
    elif gap<=8: cw=[(1,"1w"),(4,"4w"),(13,"13w"),(26,"26w")]; lag=6; hold=10; L=52
    else: continue
    pos=(s>0).all()
    st={}
    for w,nm in cw: st[f"chg{nm}"]=(np.log(s/s.shift(w)) if pos else (s-s.shift(w)))
    st["dd"]=(np.log(s/s.rolling(L).max()) if pos else (s-s.rolling(L).max())); st["rise"]=(np.log(s/s.rolling(L).min()) if pos else (s-s.rolling(L).min()))
    for nm,x in st.items():
        x=x.dropna()
        if len(x)<300: continue
        for sign,tag in [(1,"up"),(-1,"down")]:
            add(f"{sid} {nm} {tag}", pd.Series(sign*x.values, index=x.index+pd.Timedelta(days=lag)), hold)
df=pd.DataFrame(rows); df.to_csv("stage34_week.csv", index=False)
print("channels:", len(df), "| admissible (never >7d early):", int((~df.early).sum()))
adm=df[~df.early]
EPY=[e[0][:4] for e in EP]
print("\n=== ADMISSIBLE channels firing inside [T-7, T+7], per recession (T = first day after the peak month) ===")
best={}
for k in range(1,10):
    yr=EPY[k]; sub=adm[adm.cover.apply(lambda c: yr in c)].copy(); sub["day"]=sub.days.apply(lambda dd: dd[k])
    best[yr]=len(sub)
    print(f"\n{yr} (T={T[k].date()}): {len(sub)} admissible channels in the week")
    if len(sub): print(sub.sort_values("day")[["stat","Q","day","cover"]].head(12).to_string())
print("\ncoverage summary (recessions with >=1 admissible in-week channel):", {y:n for y,n in best.items()})
# which admissible channels cover the most recessions in-week
adm=adm.copy(); adm["ncov"]=adm.cover.apply(len)
print("\nadmissible channels covering >=2 recessions inside the week:"); print(adm[adm.ncov>=2].sort_values("ncov", ascending=False)[["stat","Q","cover","days"]].head(20).to_string())
