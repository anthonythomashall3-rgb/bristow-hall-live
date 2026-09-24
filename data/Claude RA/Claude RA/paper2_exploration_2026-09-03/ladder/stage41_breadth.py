"""Stage 41: neglected levels — industry payroll breadth on ALFRED first prints, metro/state LAUS breadth, and existing
nowcasts (GDPNow vintages, WEI, ADS). Margin test (stage27 method) plus the state-machine test for anything clean."""
exec(open("stage32_backstops.py").read().split("rows=[]")[0])
import glob, warnings; warnings.filterwarnings("ignore")
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
def qmaxarr(v, gated=True, start="1968-06-01"):
    q=(~allowed)&(cal>=pd.Timestamp(start))&(GATE[12] if gated else np.ones(N,bool))
    return float(np.nanmax(v[q])), str(cal[q][np.nanargmax(v[q])].date())
def firstprint_ch(sid, h):
    """per-release: h-month log change of the first print"""
    df=pd.read_csv(A+f"{sid}_all_vintages.csv", index_col=0, parse_dates=True); out={}
    for c in df.columns:
        s=df[c].dropna(); m=s.index[-1]
        if m in out or len(s)<h+1: continue
        out[m]=(pd.to_datetime(c[-8:]), s.iloc[-1]/s.iloc[-1-h]-1)
    return pd.Series([v[1] for v in out.values()], index=pd.to_datetime([v[0] for v in out.values()])).sort_index()
IND=["USCONS","USTRADE","USTPU","USMINE","USFIRE","USGOVT","USSERV","USPRIV","SRVPRD","DMANEMP","NDMANEMP","MANEMP","USWTRADE","USINFO","USPBS","USEHS","USLAH"]
print("=== INDUSTRY PAYROLL BREADTH (ALFRED first prints; share of industries with a falling 3-month print) ===")
for h in [1,3]:
    S={}
    for sid in IND:
        try: S[sid]=firstprint_ch(sid,h)
        except Exception: pass
    idx=sorted(set().union(*[set(s.index) for s in S.values()]))
    M=pd.DataFrame({k:v.reindex(idx).ffill() for k,v in S.items()}, index=pd.to_datetime(idx))
    sh=(M<0).sum(axis=1)/M.notna().sum(axis=1)
    v=sh.reindex(cal).ffill().values
    Q,Qd=qmaxarr(v); Qu,Qud=qmaxarr(v,False)
    rec=[float(np.nanmax(v[cal.searchsorted((P(pk)-1).to_timestamp()):cal.searchsorted((P(pk)+1).to_timestamp(how='end'))+1])) for pk,tr in T_P1]
    print(f"  {h}-month breadth: gated quiet max {Q:.3f} ({Qd}); ungated {Qu:.3f} ({Qud}); [peak-1,peak+1] maxima {[round(x,2) for x in rec]}")
    carried=[T_P1[i][0] for i,x in enumerate(rec) if x>Q]
    if carried:
        thr=(Q+min(rec[i] for i,x in enumerate(rec) if x>Q))/2
        ch=D(pd.Series(sh.values, index=sh.index)>=thr)
        r=score(pd.Series(ch&GATE[12], index=cal), f"industry breadth {h}m>={thr:.3f}", start="1968-06-01")
        print(f"     threshold {thr:.3f} carries {carried}: false alarms {r['n_fa']} {r['fa'][:3]} lags {r['lags']}")
        eps=replay3([SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43), ch], GATE[12], 120)
        res,false=score_eps(eps,T_P1); print(f"     added to v4-core: false {false[:3]} onsets {[x['onset'] for x in res]}")
print("\n=== EXISTING NOWCASTS ===")
for sid,lag in [("GDPNOW",1)]:
    try:
        df=pd.read_csv(A+f"{sid}_all_vintages.csv", index_col=0, parse_dates=True); out={}
        for c in df.columns:
            s=df[c].dropna()
            if len(s)==0: continue
            out[pd.to_datetime(c[-8:])]=s.iloc[-1]
        g=pd.Series(out).sort_index(); print(f"  {sid}: {len(g)} vintages {g.index.min().date()} -> {g.index.max().date()}")
        v=(-g).reindex(cal).ffill().values; Q,Qd=qmaxarr(v,True,"2011-07-01")
        rec=[(pk, round(float(np.nanmax(v[cal.searchsorted((P(pk)-1).to_timestamp()):cal.searchsorted((P(pk)+1).to_timestamp(how='end'))+1])),2)) for pk,tr in T_P1 if P(pk).to_timestamp()>=pd.Timestamp("2011-07-01")]
        print(f"     GDPNow (negative = worse): gated quiet max {Q:.2f} on {Qd}; recession-window maxima {rec}")
    except Exception as e: print(" ",sid,"ERR",str(e)[:80])
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
for nm,f,lag,st in [("WEI (weekly, 2008->)","fred_weekly/WEI.csv",5,"2008-01-05")]:
    try:
        s=loadfred(DF+f); x=-(s); x.index=x.index+pd.Timedelta(days=lag); v=x.reindex(cal).ffill().values
        Q,Qd=qmaxarr(v,True,st); rec=[(pk, round(float(np.nanmax(v[cal.searchsorted((P(pk)-1).to_timestamp()):cal.searchsorted((P(pk)+1).to_timestamp(how='end'))+1])),2)) for pk,tr in T_P1 if P(pk).to_timestamp()>=pd.Timestamp(st)]
        print(f"  {nm}: gated quiet max {Q:.2f} on {Qd}; recession-window maxima {rec}")
    except Exception as e: print(" ",nm,"ERR",str(e)[:80])
ads=pd.read_csv(ODD+"bristow-hall/projects-old/raw/ADS_INDEX.csv"); ads["d"]=pd.to_datetime(ads.Date.str.replace(":","-")); a=ads.set_index("d").ADS_Index
for w,nm in [(1,"level"),(20,"20d mean")]:
    x=-(a.rolling(w).mean()); x.index=x.index+pd.Timedelta(days=7); v=x.reindex(cal).ffill().values
    Q,Qd=qmaxarr(v); rec=[round(float(np.nanmax(v[cal.searchsorted((P(pk)-1).to_timestamp()):cal.searchsorted((P(pk)+1).to_timestamp(how='end'))+1])),2) for pk,tr in T_P1]
    print(f"  ADS {nm} (current vintage): gated quiet max {Q:.2f} on {Qd}; recession-window maxima {rec}")
