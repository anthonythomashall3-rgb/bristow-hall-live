# q24.py - DAILY AND WEEKLY SERIES IN THE SUDDEN STOP (collection 108). The sudden stop K reads one labour datum (a claims
# week 35 per cent over its base) with the market 20 per cent under its 20-day high; the labour datum is weekly, which is
# why 2020 waited for 19 March. Here each daily or weekly candidate is put in the labour slot WITH THE SAME NUMBERS (the
# 28-day mean's 365-day low and 0.85 x its five-year median as the base for a daily series; 35 per cent; the crash 20),
# entering at its own first observation (Rule 23 clause 3, the evolving menu), and read causally (a day's datum is known
# the next morning; the S&P at the prior close, or the same close for a datum published after the close). Reported: the
# first day of 2020 (and of 2008 where the series exists) on which the clause fires; every fire outside a recession
# window (six months before the peak month to the trough month) on the series' span; and, for the record, the
# candidate ALONE without the market gate (its false alarms are why the gate exists). Also, for information only and
# marked as fitted: the market-type series (VIX, OFR FSI, Baa spread, EPU, the infectious-disease EMV tracker, the
# news sentiment index) against the highest level each reached outside a recession before 2020.
# Run: PYTHONPATH=. python3 s2/q24.py
import sys,os,io,contextlib,glob
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk46.py').read().split(_MARK)[0])
MNT=os.path.expanduser('~/Projects/Onset Detector Data'); C108=os.path.join(MNT,'108_high_frequency_speed_2026-09-10'); C25=os.path.join(MNT,'25_fred_daily_weekly')
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
def fred(sid,freq='daily'):
    f=os.path.join(C25,'fred_'+freq,sid+'.csv')
    if not os.path.exists(f): return None
    d=pd.read_csv(f); d=d.iloc[:,:2]; d.columns=['d','v']; d['d']=pd.to_datetime(d['d'],errors='coerce'); return pd.to_numeric(d.set_index('d')['v'],errors='coerce').dropna()
# ---- the candidates in the labour slot ----
def trends(tag):
    """Google Trends daily halves stitched onto the weekly four-year windows (each window normalized on its own; the
    windows overlap by a year and are chained onto the 2020-24 window's scale). Returns the daily series."""
    W={}
    for f in sorted(glob.glob(os.path.join(C108,'google_trends',f'{tag}_weekly_*.csv'))):
        d=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float); W[f]=d
    if not W: return None
    keys=sorted(W); 
    # chain: scale every window to the one containing 2020-03
    base=[k for k in keys if W[k].index.min()<=pd.Timestamp('2020-03-01')<=W[k].index.max()][0]
    S={base:1.0}
    order=keys[keys.index(base)+1:]
    for k in order:  # later windows
        prev=[p for p in keys if p<k][-1]; o=W[k].index.intersection(W[prev].index)
        S[k]=S[prev]*(W[prev].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[prev]
    for k in reversed(keys[:keys.index(base)]):
        nxt=[p for p in keys if p>k][0]; o=W[k].index.intersection(W[nxt].index)
        S[k]=S[nxt]*(W[nxt].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[nxt]
    wk=pd.concat([W[k]*S[k] for k in keys]); wk=wk[~wk.index.duplicated(keep='last')].sort_index()
    D=[]
    for f in sorted(glob.glob(os.path.join(C108,'google_trends',f'{tag}_daily_*.csv'))):
        d=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float)
        wsum=d.resample('W-SAT').mean(); wsum.index=wsum.index-pd.Timedelta(days=6); o=wsum.index.intersection(wk.index)   # Trends weeks run Sunday to Saturday and are labelled by the Sunday
        fac=(wk.loc[o].mean()/max(wsum.loc[o].mean(),1e-9)) if len(o) and wsum.loc[o].mean()>0 else np.nan
        D.append(d*fac)
    day=pd.concat(D); day=day[~day.index.duplicated(keep='last')].sort_index().dropna()
    return day,wk
def base_daily(s,up=True):
    m=s.rolling(28,min_periods=20).mean(); lo=m.rolling(365,min_periods=300).min().shift(1); med=m.rolling(5*365,min_periods=3*365).median().shift(1)
    if up: return np.fmax(lo,ALPHA*med)   # fmax/fmin ignore a missing median in the series' first three years
    hi=m.rolling(365,min_periods=300).max().shift(1); return np.fmin(hi,(2-ALPHA)*med)
def base_weekly(s,up=True):
    m=s.rolling(4).mean(); lo=m.rolling(52,min_periods=52).min().shift(1); med=m.rolling(MED_W,min_periods=156).median().shift(1)
    if up: return np.maximum(lo,ALPHA*med)
    hi=m.rolling(52,min_periods=52).max().shift(1); return np.minimum(hi,(2-ALPHA)*med)
_SPXd=_SPX.copy(); _cr=(1-_SPXd/_SPXd.rolling(20,min_periods=10).max())*100
def crash_prior(day):
    s=_cr[_cr.index<day]; return float(s.iloc[-1]) if len(s) else np.nan
def crash_same(day):
    s=_cr[_cr.index<=day]; return float(s.iloc[-1]) if len(s) else np.nan
def episodes(days,gap=182):
    eps=[]; last=None
    for d in sorted(days):
        if last is None or (d-last).days>gap: eps.append(d)
        last=d
    return eps
def test(name,s,up=True,lag_days=1,daily=True,same_close=True):
    """s: the series by observation day; known lag_days later. Fires when the datum is 35 per cent over (under) its base
    and the S&P is 20 under its 20-day high at the last close known at that moment."""
    b=base_daily(s,up) if daily else base_weekly(s,up)
    rel=((s/b-1)*100) if up else ((1-s/b)*100); rel=rel.dropna()
    known=rel.copy(); known.index=known.index+pd.Timedelta(days=lag_days)
    alone=[d for d,v in known.items() if v>=35-EPS]
    gated=[d for d in alone if (crash_same(d) if same_close else crash_prior(d))>=20-EPS]
    ea=episodes(alone); eg=episodes(gated)
    fa_a=[d for d in ea if not in_rec(d)]; fa_g=[d for d in eg if not in_rec(d)]
    f20=[d for d in gated if d.year==2020]; f08=[d for d in gated if pd.Timestamp('2007-06-01')<=d<=pd.Timestamp('2009-06-30')]
    print(f"{name} [{s.index.min().date()}..{s.index.max().date()}]: ALONE {len(ea)} episodes, {len(fa_a)} outside a recession {[d.date().isoformat() for d in fa_a][:12]}; "
          f"WITH THE MARKET GATE {len(eg)} episodes {[d.date().isoformat() for d in eg]}, {len(fa_g)} outside; first 2020 fire {f20[0].date().isoformat() if f20 else None}; first 2008 fire {f08[0].date().isoformat() if f08 else None}")
    return rel
print('=== the labour slot with a daily datum (35 over base, the market 20 under its 20-day high; Rule 23 entry at first observation)')
TR_={}
for tag,kw in [('unemp','unemployment'),('file','file for unemployment'),('benefits','unemployment benefits')]:
    r=trends(tag)
    if r is None: print(f'google trends {kw}: no files'); continue
    day,wk=r; TR_[tag]=(day,wk)
    rel=test(f'google searches "{kw}", 7-day mean of the daily index (the week analog; known next day; same-day close)',day.rolling(7,min_periods=7).mean(),up=True,lag_days=1,daily=True,same_close=True)
    print('   March 2020 day by day (per cent over base, as known that morning):',{d.strftime('%m-%d'):round(float(v)) for d,v in rel[(rel.index>='2020-03-08')&(rel.index<='2020-03-22')].items()})
    test(f'google searches "{kw}", 7-day mean (known next day; PRIOR close)',day.rolling(7,min_periods=7).mean(),up=True,lag_days=1,daily=True,same_close=False)
    test(f'google searches "{kw}", weekly windows (a week Sunday-Saturday, labelled by its Sunday; known the Monday after; prior close)',wk,up=True,lag_days=8,daily=False,same_close=False)
tsa=pd.read_csv(os.path.join(C108,'tsa','tsa_daily_throughput.csv'),parse_dates=['date']).set_index('date')['n'].astype(float)
tsa7=tsa.rolling(7,min_periods=7).mean()   # the day-of-week cycle removed
rel=test('TSA checkpoint throughput, 7-day mean (down; known next day)',tsa7,up=False,lag_days=1)
print('   March 2020:',{d.strftime('%m-%d'):round(float(v)) for d,v in rel[(rel.index>='2020-03-08')&(rel.index<='2020-03-22')].items()})
ind=fred('IHLIDXUS')
if ind is not None: rel=test('Indeed job postings index, daily (down; known next day)',ind,up=False,lag_days=1); print('   March-April 2020:',{d.strftime('%m-%d'):round(float(v)) for d,v in rel[(rel.index>='2020-03-10')&(rel.index<='2020-04-10')].items() if d.day in (10,13,16,19,20,23,27,31,3,6,10)})
icn=fred('ICNSA','weekly')
if icn is not None: test('initial claims NOT seasonally adjusted, weekly (the release day; prior close)',icn,up=True,lag_days=5,daily=False,same_close=False)
# the claims week itself with the same code, as the check that the code reproduces K
test('initial claims, the first prints (K itself; prior close)',ICfp.dropna(),up=True,lag_days=5,daily=False,same_close=False)
# ---- for information: market-type daily series against the highest level outside a recession before 2020 (a fitted line) ----
print('=== for information only (fitted lines): the highest level outside a recession before 2020 and the first day of 2020 above it')
def info(name,s,up=True,lag=1):
    s=s.dropna(); pre=s[(s.index<'2020-01-01')]; out=pre[[not in_rec(d) for d in pre.index]]
    if up: lvl=out.max(); when=out.idxmax(); first=[d for d,v in s[(s.index>='2020-01-01')&(s.index<='2020-12-31')].items() if v>lvl]
    else: lvl=out.min(); when=out.idxmin(); first=[d for d,v in s[(s.index>='2020-01-01')&(s.index<='2020-12-31')].items() if v<lvl]
    print(f"{name}: non-recession {'max' if up else 'min'} before 2020 {round(float(lvl),2)} on {when.date()}; 2020 first beyond it {first[0].date().isoformat() if first else None} (known {(first[0]+pd.Timedelta(days=lag)).date().isoformat() if first else None}); crossings 2021-26 {[d.date().isoformat() for d in episodes([d for d,v in s[s.index>='2021-01-01'].items() if (v>lvl if up else v<lvl)])]}")
vix=fred('VIXCLS'); vxo=fred('VXOCLS')
if vix is not None: info('VIX close (from 1990)',vix)
if vxo is not None: info('VXO close (from 1986; the 1987 crash)',vxo)
fsi=pd.read_csv(os.path.join(C108,'ofr_fsi','fsi.csv')); fsi['Date']=pd.to_datetime(fsi['Date']); fsi=fsi.set_index('Date')['OFR FSI'].astype(float); info('OFR financial stress index (from 2000)',fsi)
baa=fred('BAA10Y')
if baa is not None: info('Baa corporate over 10-year Treasury, daily (from 1986)',baa)
epu=fred('USEPUINDXD')
if epu is not None: info('economic policy uncertainty, daily, 7-day mean (from 1985)',epu.rolling(7).mean())
emv=fred('INFECTDISEMVTRACKD')
if emv is not None: info('infectious-disease equity-market volatility tracker, 7-day mean (from 1985; built in 2020)',emv.rolling(7).mean())
dn=pd.read_csv(os.path.join(C108,'sffed_dnsi','news_sentiment_daily.csv')); dn['date']=pd.to_datetime(dn['date']); dn=dn.set_index('date').iloc[:,0].astype(float); info('daily news sentiment index (SF Fed, from 1980; published with about a week\'s lag)',dn,up=False,lag=7)
nf=fred('NFCI','weekly')
if nf is not None: info('Chicago Fed NFCI, weekly (from 1971; revised)',nf,lag=5)
st=fred('STLFSI4','weekly')
if st is not None: info('St. Louis Fed financial stress index, weekly (from 1993; revised)',st,lag=6)
print('=== March 2020 day by day: S&P crash at that close | VIX | OFR FSI | Baa spread | news sentiment')
for d in pd.date_range('2020-03-02','2020-03-20',freq='B'):
    g=lambda s: (round(float(s[s.index<=d].iloc[-1]),2) if s is not None and len(s[s.index<=d]) else None)
    print(d.date(), round(crash_same(d),1), g(vix), g(fsi), g(baa), g(dn))
