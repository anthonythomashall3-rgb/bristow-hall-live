"""The recession engine — one procedure, any country, any era.

The instrument is not a list of series.  It is a rule about whatever series exist:

  1  CHANNELS.  From each input series build channels of fixed functional forms.
       a level (an unemployment rate)     -> its three-month mean less its twelve-month minimum
       an activity series (output, sales, -> the worse of this month's and last month's fall,
       employment, clearings, freight)        and its six-month fall
  2  SCALE.  Each channel is measured in its OWN robust standard deviations: subtract the median
       of its quiet-period readings, divide by 1.4826 times their median absolute deviation.
  3  FIRE.  A channel fires when it exceeds its OWN quiet record by delta robust standard
       deviations.  delta is the only number in the instrument and is the same everywhere.
  4  FLOOR.  No episode may open unless a labour-market channel is already above its own
       twelve-month low.  Where no labour series exists the floor is absent, not failed.
  5  GATE.  Where both a short and a long interest rate exist, the fast lane additionally
       requires the term spread to have been negative within the prior twelve months.

Nothing above names a country or a decade.  The American instrument of 2026 and the Japanese
instrument of 1994 and the American instrument of 1893 are the same five steps run on different
inputs, which is what makes the international record evidence about the national one."""
import numpy as np, pandas as pd

WARM_YEARS=5.0
def channels(series, idx):
    """series: dict name -> (pandas Series, kind) where kind is 'level' or 'activity'."""
    S={}
    for nm,(s,kind) in series.items():
        if s is None or len(s.dropna())<24: continue
        if kind=="level":
            v=s.reindex(idx).interpolate(limit_area="inside")
            S[nm+" gap"]=v.rolling(3).mean()-v.rolling(12).min()
        else:
            v=s.reindex(idx,method="ffill")
            pos=(v.dropna()>0).all()
            d1=-(v/v.shift(1)-1)*100 if pos else -(v-v.shift(1))
            d6=-(v/v.shift(6)-1)*100 if pos else -(v-v.shift(6))
            S[nm+" 1m"]=pd.concat([d1,d1.shift(1)],axis=1).min(axis=1)
            S[nm+" 6m"]=d6
    return S
def quiet_mask(idx, episodes, pre=6, post=9):
    q=pd.Series(True,index=idx)
    for P,T in episodes:
        q &= ~((idx>=P-pd.DateOffset(months=pre))&(idx<=T+pd.DateOffset(months=post)))
    return q
def gate_from_rates(short_rate, long_rate, idx, months=12):
    if short_rate is None or long_rate is None: return None
    sp=long_rate.reindex(idx,method="ffill")-short_rate.reindex(idx,method="ffill")
    return (sp<0).rolling(months,min_periods=1).max().fillna(0).astype(bool)
def floor_from_labour(S, idx, labour_names, level=0.30):
    f=None; have=None
    for nm in labour_names:
        k=nm+" gap"
        if k not in S: continue
        a=(S[k]>=level).reindex(idx).fillna(False); h=S[k].notna().reindex(idx).fillna(False)
        f=a if f is None else (f|a); have=h if have is None else (have|h)
    if f is None: return pd.Series(True,index=idx)
    return (f|(~have)).rolling(6,min_periods=1).max().fillna(0).astype(bool)
def fire(S, idx, q, delta, gate=None, warm_years=WARM_YEARS, minobs=36):
    """returns (boolean trigger series, number of channels used)"""
    hit=pd.Series(False,index=idx); used=0
    for nm,x in S.items():
        v=x[q].dropna()
        if len(v)<minobs: continue
        med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
        if not np.isfinite(mad) or mad<=0: continue
        z=(x-med)/mad
        rec=float(z[q].dropna().max())
        first=x.dropna().index.min()
        live=pd.Series(idx>=first+pd.DateOffset(years=warm_years),index=idx)
        on=((z>=rec+delta)&live).reindex(idx).fillna(False)
        if gate is not None: on=on&gate.reindex(idx).fillna(False)
        hit=hit|on; used+=1
    return hit,used
def run(series, episodes, idx, delta=0.10, labour_names=(), short_rate=None, long_rate=None,
        pre=6, post=9, gap_days=200):
    S=channels(series, idx)
    q=quiet_mask(idx, episodes, pre, post)
    g=gate_from_rates(short_rate, long_rate, idx)
    fl=floor_from_labour(S, idx, labour_names)
    hitG,nG=fire(S, idx, q, delta, gate=g) if g is not None else (pd.Series(False,index=idx),0)
    hitU,nU=fire(S, idx, q, delta, gate=None)
    hit=(hitG|hitU) if g is not None else hitU
    trig=(hit&fl).reindex(idx).fillna(False)
    hits=list(idx[trig.values])
    det=[];lags=[]
    for P,T in episodes:
        w=[h for h in hits if P-pd.DateOffset(months=pre)<=h<=T+pd.DateOffset(months=post)]
        det.append(bool(w)); lags.append((w[0].to_period("M")-P.to_period("M")).n if w else None)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=gap_days: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[a for a,b in runs if not any(P-pd.DateOffset(months=pre)<=a<=T+pd.DateOffset(months=post) for P,T in episodes)]
    return dict(detected=det, lags=lags, false=[str(x.date())[:7] for x in fa],
                channels=max(nU,nG), quiet_years=float(q.sum())/12.0, hits=hits)
