"""Ladder harness: daily -> weekly -> monthly onset rules scored against Anthony's rules:
 R1 all recessions (nine NBER 1960-2020 + 2024 episode, Paper 1: Apr-Aug 2024) detected, zero false alarms;
 R2 onset call within +-2 months of the peak month; end call within +-2 months of trough month;
 R3 dated turning point within +-3 months of NBER."""
import pandas as pd, numpy as np, os
HOME=os.path.expanduser("~"); ODD=HOME+"/mnt/Onset Detector Data/"
P=lambda s: pd.Period(s,"M")
EP=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
def load(path, col=None):
    d=pd.read_csv(path, parse_dates=[0]); d=d.set_index(d.columns[0]).iloc[:,0]; return pd.to_numeric(d, errors="coerce").dropna()
def runs(dates, gap_days):
    out=[]
    for m in dates:
        if out and (m-out[-1][1]).days<=gap_days: out[-1][1]=m
        else: out.append([m,m])
    return out
def score(sig, name, start=None, gap_days=45):
    """sig: boolean series (any freq). Onset call date = first True at/after (peak-2 months) within episode window."""
    sig=sig.dropna().astype(bool)
    if start: sig=sig[sig.index>=start]
    first=sig.index.min()
    rows=[]; ok=True
    for pk,tr in EP:
        if P(pk).to_timestamp()<first: rows.append(None); continue
        lo=(P(pk)-2).to_timestamp(); hi=(P(tr)+12).to_timestamp(how="end")
        w=sig[(sig.index>=lo)&(sig.index<=hi)]; h=w[w].index
        if len(h)==0: rows.append(("MISS",None)); ok=False; continue
        lag=(h[0].to_period("M")-P(pk)).n; rows.append((str(h[0].date()),lag))
        if lag>2: ok=False
    # false alarms: runs whose first date lies outside every [peak-2, trough+12]
    fa=[]
    for a,b in runs(list(sig[sig].index), gap_days):
        if not any((P(pk)-2).to_timestamp()<=a<=(P(tr)+12).to_timestamp(how="end") for pk,tr in EP): fa.append((str(a.date()),str(b.date())))
    if fa: ok=False
    covered=[r for r in rows if r is not None]
    lags=[r[1] for r in covered if r[0]!="MISS"]
    return dict(rule=name, data_from=str(first.date()), n_episodes_covered=len(covered), misses=sum(1 for r in covered if r[0]=="MISS"),
                lags=lags, max_lag=max(lags) if lags else None, n_fa=len(fa), fa=fa[:6], passes_R1_R2_onset=ok, calls=[r[0] if r else "-" for r in rows])
def show(results):
    pd.set_option("display.width",320); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_rows",500)
    print(pd.DataFrame(results).drop(columns=["calls"]).to_string())
