exec(open("stage13_sm3b.py").read().split("rows=[]")[0])
um=load(ODD+"15_sentiment_surveys/monthly/UMCSENT.csv"); um=um[um.index>="1978-01-01"]
ta=load(ODD+"10_consumption_retail/monthly/TOTALSA.csv")
def mo(sig, lagdays):  # monthly series dated first of month; known at month end + lagdays
    s=sig.copy(); s.index=s.index+pd.offsets.MonthEnd(0)+pd.Timedelta(days=lagdays); return D(s)
UM={f"um_d3_{x}": mo(um-um.shift(3)<=-x, 0) for x in [8,10,12,15]}
UM.update({f"um_d1_{x}": mo(um-um.shift(1)<=-x, 0) for x in [6,8,10]})
UM.update({f"um_dd12_{x}": mo(um/um.rolling(13).max()-1<=-x/100, 0) for x in [15,20,25]})
TA={f"ta_d3_{x}": mo(ta/ta.shift(3)-1<=-x/100, 5) for x in [10,15,20,25]}
TA.update({f"ta_dd12_{x}": mo(ta/ta.rolling(13).max()-1<=-x/100, 5) for x in [15,20,25,30]})
base=[SAHM[0.35], IC["ic8_30_k1"], PAY]
rows=[]
for nm,ch in list(UM.items())+list(TA.items())+[("none",None)]:
    chs=base+([ch] if ch is not None else [])
    eps=replay3(chs, GATE[12], 120)
    for tname,T in [("P1",T_P1)]:
        res,false=score_eps(eps,T); L=[r["lag"] for r in res]
        rows.append(dict(extra=nm, misses=sum(l is None for l in L), n_false=len(false), false=false[:4], lags=L, end=[r["end_lag"] for r in res], onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",130)
print(df.drop(columns=["onsets"]).to_string())
for _,r in df[(df.n_false<=1)].iterrows(): print(r.extra, r.onsets)
