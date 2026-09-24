"""Stage 178: the one-per-cent end rule against the revisions.  Round 24 measured the published
revisions to weekly claims: the first print differs from the settled value by more than one per
cent in sixty-three per cent of weeks.  An end rule that fires on a one per cent fall is reading
a number whose own revision is usually larger than the signal.  This resamples those revisions
and replays the ends."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, os
ZM={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZNn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
h=np.zeros(N,bool)
for n in ["Sahm","payrolls","housing","bill"]:
    z=np.where(np.isfinite(Zz[n]),Zz[n],-99.0); h|=(z>=ZM[n]+0.25)
h|=np.asarray(gapch(iur4,0.40),bool)
icv=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
icv["fv"]=pd.to_datetime(icv.first_vintage.astype(str),format="%Y%m%d")
gg=icv[icv.fv>pd.Timestamp("2009-05-28")]; rev=((gg.first_print/gg.current)-1).values; rev=rev[np.isfinite(rev)]
def replay_v(trig, ma, endpct):
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"):
                open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
        ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-endpct)
        if ok and endcall is None: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps
rng=np.random.default_rng(41); R=150
def draw(endpct):
    n1=rng.choice(rev,size=len(ic),replace=True)
    icx=pd.Series(ic.values*(1+n1),index=ic.index)
    m8=icx.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    co=pd.Series(CLx>=0.03).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    cco=pd.Series(CLx>=0.12).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
    fr=fresh(h&co,120)&G
    fr=fr|fresh((Zc>=ZNn+2.0)&cco&NG,120)
    x=icx.rolling(8).mean(); x.index=x.index+pd.Timedelta(days=5)
    ma=x.reindex(cal).ffill().values.astype(float)
    eps=replay_v(fr,ma,endpct)
    res,f=score_eps(eps,T_P1)
    det=sum(1 for x_ in res if x_["lag"] is not None)
    ends=[e["end_call"] for e in eps] if det==9 and len(eps)==9 else None
    return det,len(f) if f else 0,ends
BASE={0.03:[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09","2001-12-13","2009-05-14","2020-05-28","2024-09-26"]],
      0.01:[pd.Timestamp(x) for x in ["1970-11-26","1975-03-20","1980-07-17","1982-11-11","1991-04-25","2001-11-29","2009-04-30","2020-05-14","2024-09-12"]]}
print("%-8s %-14s %-16s %-28s %s"%("fall","nine of nine","and no false","end call shift, median days","10th to 90th percentile"))
for pct in [0.03,0.02,0.01]:
    d9=0; ok=0; shifts=[[] for _ in range(9)]
    for _ in range(R):
        det,nf,ends=draw(pct)
        if det==9: d9+=1
        if det==9 and nf==0:
            ok+=1
            if ends is not None and len(ends)==9:
                for i,e in enumerate(ends):
                    b=BASE.get(pct)
                    if b is not None and e is not None: shifts[i].append((e-b[i]).days)
    allsh=[x for s in shifts for x in s]
    med=np.median(allsh) if allsh else float("nan")
    p10=np.percentile(allsh,10) if allsh else float("nan"); p90=np.percentile(allsh,90) if allsh else float("nan")
    print("%-8.0f%% %-14s %-16s %-28s %s"%(100*pct,"%d%%"%(100*d9//R),"%d%%"%(100*ok//R),"%.0f"%med,"%.0f to %.0f"%(p10,p90)))
    worst=[(i,np.percentile(s,10),np.percentile(s,90)) for i,s in enumerate(shifts) if len(s)>20]
    worst.sort(key=lambda t:-(t[2]-t[1]))
    if worst: print("        widest episode: number %d, 10th to 90th percentile %.0f to %.0f days"%(worst[0][0]+1,worst[0][1],worst[0][2]))
