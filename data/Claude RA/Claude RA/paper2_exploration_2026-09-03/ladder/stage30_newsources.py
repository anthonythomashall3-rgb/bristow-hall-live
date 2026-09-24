"""Stage 30: new sources — SF Fed Daily News Sentiment (1980->), OFR Financial Stress Index (2000->), World Bank monthly gold /
copper / oil (1960->; copper-to-gold, gold-to-oil), Treasury DTS daily UI benefit outflows (2005-2020), and normalized (log-ratio)
forms of the short-rate fall. Margin scan (stage27 method) and state-machine tests of the clean ones."""
exec(open("stage27_margins.py").read().split("rows=[]")[0])
import warnings; warnings.filterwarnings("ignore")
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
rows=[]
def sh(x, lagd): x=x.dropna().copy(); x.index=x.index+pd.Timedelta(days=lagd); return x
# --- SF Fed news sentiment (daily; treat as known next day) ---
ns=pd.read_csv(DF+"other/sffed_news_sentiment.csv", parse_dates=["date"]).set_index("date")["News Sentiment"]
for w in [20,40,60,120]:
    m=ns.rolling(w).mean()
    rows.append(evaluate(f"news sentiment {w}d mean level (low=bad)", sh(-m,1), 5))
    rows.append(evaluate(f"news sentiment {w}d mean, fall vs 250d max", sh(-(m-m.rolling(250).max()),1), 5))
    rows.append(evaluate(f"news sentiment {w}d mean, {w}d change down", sh(-(m-m.shift(w)),1), 5))
# --- OFR FSI (daily, 2000->) ---
of=pd.read_csv(DF+"other/ofr_fsi.csv", parse_dates=["Date"]).set_index("Date"); fsi=of["OFR FSI"]
rows.append(evaluate("OFR FSI level", sh(fsi,1), 5)); rows.append(evaluate("OFR FSI 20d mean", sh(fsi.rolling(20).mean(),1), 5))
for c in ["Credit","Equity valuation","Safe assets","Funding","Volatility"]:
    rows.append(evaluate(f"OFR FSI {c} 20d mean", sh(of[c].rolling(20).mean(),1), 5))
# --- World Bank monthly commodities (known ~ month end +5 days) ---
wb=pd.read_csv(DF+"other/wb_cmo_gold_copper_oil.csv", parse_dates=["month"]).set_index("month")
gold=wb["Gold"]; cu=wb["Copper"]; oil=wb["Crude oil, average"]
def mo(x, lagd=35): x=x.dropna().copy(); x.index=x.index+pd.Timedelta(days=lagd); return x
for w in [3,6,12]:
    rows.append(evaluate(f"copper/gold {w}m log change down", mo(-np.log((cu/gold)/(cu/gold).shift(w))), 40))
    rows.append(evaluate(f"copper {w}m log change down", mo(-np.log(cu/cu.shift(w))), 40))
    rows.append(evaluate(f"gold {w}m log change up", mo(np.log(gold/gold.shift(w))), 40))
    rows.append(evaluate(f"oil {w}m log change up", mo(np.log(oil/oil.shift(w))), 40))
    rows.append(evaluate(f"oil {w}m log change down", mo(-np.log(oil/oil.shift(w))), 40))
    rows.append(evaluate(f"gold/oil {w}m log change up", mo(np.log((gold/oil)/(gold/oil).shift(w))), 40))
rows.append(evaluate("copper/gold drawdown from 12m max", mo(-np.log((cu/gold)/(cu/gold).rolling(12).max())), 40))
# --- DTS daily UI benefits 2005-2020 (4-week sum vs a year earlier) ---
dts=pd.read_csv(DF+"other/dts_daily_ui_withheld.csv", parse_dates=["record_date"]); ui=dts.groupby("record_date").transaction_today_amt.sum().sort_index()
ui28=ui.rolling("28D").sum(); rows.append(evaluate("DTS UI benefits 28d sum yoy log up", sh(np.log(ui28/ui28.shift(365, freq="D").reindex(ui28.index, method="nearest")),3), 3))
# --- short-rate fall, normalized forms ---
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
tb6=loadfred(DF+"fred_daily/DTB6.csv")
for w in [40,60,80]:
    rows.append(evaluate(f"TB6 {w}d fall (pp)", sh(-(tb6-tb6.shift(w)),1), 5))
    rows.append(evaluate(f"TB6 {w}d log-ratio fall", sh(-np.log((tb6+0.25)/(tb6.shift(w)+0.25)),1), 5))
    rows.append(evaluate(f"TB6 {w}d fall / level", sh(-(tb6-tb6.shift(w))/(tb6.shift(w)+0.5),1), 5))
rows=[r for r in rows if r]
df=pd.DataFrame(rows); df.to_csv("stage30_margins.csv", index=False)
pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",200)
print(df.sort_values(["covered","min_margin"], ascending=[False,False]).to_string())
