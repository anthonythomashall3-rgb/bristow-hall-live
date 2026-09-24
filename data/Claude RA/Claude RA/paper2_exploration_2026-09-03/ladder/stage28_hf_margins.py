"""Stage 28: margin scan over ALL fetched daily/weekly FRED series (data_fetched/fred_daily, fred_weekly, extra) plus corpus daily.
Statistics per series, both signs (sign reported): changes over 20/60/120/250 trading days (weekly: 4/13/26/52 weeks), drawdown from
trailing-250-day max, rise above trailing-250-day min, level z-score vs trailing 250. Margin per recession = (worst reading in
[peak-1, peak+1] release window - worst gated quiet reading) / sd(quiet). Same scoring as stage27 (2024 = Apr-Aug)."""
exec(open("stage27_margins.py").read().split("rows=[]")[0])
import glob, warnings; warnings.filterwarnings("ignore")
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
files=[(f,"daily") for f in glob.glob(DF+"fred_daily/*.csv")]+[(f,"weekly") for f in glob.glob(DF+"fred_weekly/*.csv")]+[(f,"extra") for f in glob.glob(DF+"extra/*.csv")]
files+=[(f,"daily") for f in glob.glob(ODD+"05_financial_conditions/daily/*.csv")]+[(f,"daily") for f in glob.glob(ODD+"09_output_production/daily/*.csv")]
rows=[]; seen=set()
for f,kind in files:
    sid=os.path.basename(f).replace(".csv","")
    if sid in seen: continue
    seen.add(sid)
    try: s=loadfred(f)
    except Exception: continue
    if len(s)<500 or s.index.min()>pd.Timestamp("1995-12-31"): continue
    # infer frequency
    gap=np.median(np.diff(s.index.values).astype("timedelta64[D]").astype(int))
    if gap<=2: cwins=[(20,"20d"),(60,"60d"),(120,"120d"),(250,"250d")]; lag=1; hold=5
    elif gap<=8: cwins=[(4,"4w"),(13,"13w"),(26,"26w"),(52,"52w")]; lag=6; hold=10
    elif gap<=16: cwins=[(2,"2p"),(6,"6p"),(13,"13p"),(26,"26p")]; lag=8; hold=16
    else: continue   # monthly/other skipped here
    L=250 if gap<=2 else (52 if gap<=8 else 26)
    pos=(s>0).all()
    stats={}
    for w,nm in cwins:
        stats[f"chg{nm}"]=(np.log(s/s.shift(w)) if pos else (s-s.shift(w)))
    stats["dd"]=(np.log(s/s.rolling(L).max()) if pos else (s-s.rolling(L).max()))
    stats["rise"]=(np.log(s/s.rolling(L).min()) if pos else (s-s.rolling(L).min()))
    stats["z"]=(s-s.rolling(L).mean())/s.rolling(L).std()
    for nm,x in stats.items():
        x=x.dropna()
        if len(x)<300: continue
        for sign,tag in [(1,"up"),(-1,"down")]:
            ser=pd.Series(sign*x.values, index=x.index+pd.Timedelta(days=lag))
            try: r=evaluate(f"{sid} {nm} {tag}", ser, hold)
            except Exception as e: print("ERR", sid, nm, str(e)[:80], type(ser.index), ser.index[:2]); r=None
            if r: r["kind"]=kind; rows.append(r)
df=pd.DataFrame(rows); df.to_csv("stage28_hf_margins.csv", index=False)
pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",400)
print("series scanned:", len(seen), "| statistic-sign rows:", len(df))
print("\n=== daily/weekly channels calling >=3 recessions inside +-1 with zero false alarms (gated), by worst margin ===")
print(df[df.covered>=3].sort_values(["covered","min_margin"], ascending=[False,False]).head(40)[["stat","Q","sd","covered","which","min_margin","margins"]].to_string())
for yr in ["1969","1973","1980","1981","1990","2001","2007","2020","2024"]:
    sub=df[df.which.apply(lambda w: yr in w)].copy(); sub["m"]=sub.apply(lambda r: r.margins[[e[0][:4] for e in EP].index(yr)], axis=1)
    print(f"\n--- widest daily/weekly channels for {yr} ---"); print(sub.sort_values("m", ascending=False).head(10)[["stat","Q","sd","m","covered","which"]].to_string())
