from harness import *
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv")
idx=pd.read_csv(ODD+"bristow-hall-harvest/data/dol_claims_press/weekly_claims_press_index.csv", parse_dates=["release_date"]).dropna(subset=["initial_claims_headline"])
idx["week"]=idx.release_date-pd.Timedelta(days=5); fp=idx.set_index("week")["initial_claims_headline"].astype(float).sort_index()
EPS=[e for e in EP if e[0]>="1969"]
def run(series, x, w=8, label=""):
    ma=series.rolling(w).mean().dropna()
    for pk,tr in EPS:
        if ma.index.min()>P(pk).to_timestamp(): continue
        seg=ma[(ma.index>=(P(pk)-1).to_timestamp())&(ma.index<=(P(tr)+18).to_timestamp(how="end"))]
        runmax=-1; pkd=None; call=None; hist=[]
        for d,v in seg.items():
            if v>runmax:
                if call is not None: hist.append(f"superseded {call.date()} (peak was {pkd.date()})"); call=None
                runmax=v; pkd=d
            elif call is None and v<=runmax*(1-x): call=d
        print(f"{label} trough {tr}: claims 8wk peak {pkd.date()} (err {(pkd.to_period('M')-P(tr)).n:+d} mo), call {call.date() if call else None} (lag {(call.to_period('M')-P(tr)).n if call else None}); release ~{(call+pd.Timedelta(days=5)).date() if call else None}; {hist}")
print("== current vintage, 3% =="); run(ic,0.03,label="cv")
print("== first prints (DOL headline, 2002->), 3% =="); run(fp,0.03,label="fp")
print("== current vintage, 4% =="); run(ic,0.04,label="cv")
