#!/usr/bin/env python3
"""Price every transmission series as a candidate leg, so the good ones can enter walk 70.

A transmission leg is the thing that makes the rule work for a recession type nobody has designed
for: it does not read the CAUSE, it reads the economy stopping. Every series here is oriented so
HIGH = deteriorating, screened against a rolling quantile of its own past, then gated exactly as
legs M, R, E and T are, because a gate is what has made every sparse object admissible.
"""
import json, os, glob, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
_C = [os.path.expanduser('~/Projects/Onset Detector Data'), os.path.expanduser('~/mnt/Onset Detector Data')]
BASE = next((c for c in _C if os.path.isdir(os.path.join(c,'183_transmission_channels_2026-09-15'))), _C[0])
HERE = os.path.join(BASE,'183_transmission_channels_2026-09-15')
DATA, OUT = os.path.join(HERE,'data'), os.path.join(HERE,'out'); os.makedirs(OUT, exist_ok=True)
S176 = os.path.join(BASE,'176_financial_leg_conjunction_2026-09-15','data')

PEAKS=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01',
       '1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07',
         '1982-11','1991-03','2001-11','2009-06','2020-04','2024-09']
CR=(pd.Timestamp('1965-07-01'),pd.Timestamp('1968-06-30'))
def me(y): return pd.Timestamp(y+'-01')+pd.offsets.MonthEnd(0)
PK,TR=[me(p) for p in PEAKS],[me(t) for t in TROUGHS]
def inside(t): return any(p<=t<=tr for p,tr in zip(PK,TR))
HUB=0.3667
LAG={'D':1,'W':12,'M':40,'Q':120}

def rd(p):
    q=pd.read_csv(p); c=list(q.columns)
    s=pd.Series(pd.to_numeric(q[c[1]],errors='coerce').values,
                index=pd.to_datetime(q[c[0]],errors='coerce')).dropna().sort_index()
    return s[~s.index.duplicated(keep='last')]
def freq(s):
    d=np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int))
    return 'D' if d<=3 else ('W' if d<=10 else ('M' if d<=45 else 'Q'))

g10,g1=rd(os.path.join(S176,'GS10.csv')),rd(os.path.join(S176,'GS1.csv'))
TS=(g10-g1.reindex(g10.index,method='ffill')).dropna(); TS.index=TS.index+pd.Timedelta(days=15)
u=rd(os.path.join(S176,'UNRATE.csv')); m3=u.rolling(3).mean()
SAHM=(m3-m3.rolling(12).min()); SAHM.index=SAHM.index+pd.Timedelta(days=40)
def g_term(t,q):
    ln=TS.shift(1).expanding(min_periods=120).quantile(q/100.)
    pv,pl=TS[TS.index<=t],ln[ln.index<=t]
    return len(pv) and len(pl) and pd.notna(pl.iloc[-1]) and float(pv.iloc[-1])<=float(pl.iloc[-1])
def g_sahm(t,fr):
    pv=SAHM[SAHM.index<=t]; return len(pv) and float(pv.iloc[-1])>=HUB*fr
GATES=[('NONE',None,[0]),('TERM',g_term,[2,5,10,20]),('SAHM',g_sahm,[1/6,1/3,1/2])]

MAN=pd.read_csv(os.path.join(HERE,'MANIFEST_transmission.csv'))
UP={'DRALACBS','DRCCLACBS','DRBLACBN','DRCLACBS','DRSFRMACBS','DRCRELEXFACBS','CORALACBN',
    'CORCACBS','CORBLACBS','ISRATIO','NFCI','ANFCI','NFCICREDIT','NFCILEVERAGE','STLFSI4',
    'DRTSCILM','DRTSCLCC','BAMLH0A0HYM2','BAMLC0A0CM','ICSA','CCSA','IURSA'}
rows=[]
for _,m in MAN[MAN.status=='ok'].iterrows():
    sid=m['id']; p=os.path.join(DATA,sid+'.csv')
    if not os.path.exists(p): continue
    try: s=rd(p)
    except Exception: continue
    if len(s)<80: continue
    f=freq(s)
    for tf,name in [(lambda x:x,'level'),(lambda x:-x.pct_change(6)*100,'fall6'),(lambda x:x.diff(6),'chg6')]:
        try: x=tf(s).dropna()
        except Exception: continue
        if name=='level' and sid not in UP: continue
        if name!='level' and sid in UP: continue
        if len(x)<80: continue
        x=x.copy(); x.index=x.index+pd.Timedelta(days=LAG[f])
        for q in [95,97,99]:
            for win in [60,120]:
                w = win if f in ('M','Q') else win*4
                ln=x.shift(1).rolling(w,min_periods=max(20,w//3)).quantile(q/100.)
                hit=(x>ln)&ln.notna()
                base,last=[],None
                for t in x.index[hit]:
                    if last is not None and (t-last).days<540: continue
                    base.append(t); last=t
                if not base: continue
                for gn,fn,lv_ in GATES:
                    for lv in lv_:
                        kept=base if fn is None else [t for t in base if fn(t,lv)]
                        hits,used={},set()
                        for pk in PK:
                            c=[t for t in kept if 0<=(pk-t).days<=400]
                            if c: tt=c[-1]; hits[pk.strftime('%Y-%m')]=(tt-pk).days; used.add(tt)
                        inw={k:v for k,v in hits.items() if -92<=v<=-1}
                        quiet=[t for t in kept if t not in used and not inside(t)]
                        crunch=[t for t in quiet if CR[0]<=t<=CR[1]]
                        rows.append(dict(series=sid,route=m['route'],transform=name,q=q,win=win,
                                         gate=gn,level=round(lv,4),n_fire=len(kept),n_hit=len(hits),
                                         n_in=len(inw),n_quiet=len(quiet),n_crunch=len(crunch),
                                         inwindow=json.dumps(inw)))
D=pd.DataFrame(rows); D.to_csv(os.path.join(OUT,'transmission_pricing.csv'),index=False)
print('configurations:',len(D))
z=D[(D.n_quiet==0)&(D.n_crunch==0)&(D.n_in>0)].sort_values(['n_in','n_hit'],ascending=False)
print('\n=== ADMISSIBLE: zero quiet, 1966 silent, at least one in-window ===')
print('unique series admissible:', z.series.nunique())
if len(z):
    b=z.drop_duplicates('series').head(16)
    print(b[['series','route','transform','q','win','gate','level','n_fire','n_hit','n_in','inwindow']].to_string(index=False))
