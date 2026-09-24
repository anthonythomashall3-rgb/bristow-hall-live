"""The quarterly committees on first prints: the euro area (CEPR-EABCN), France (AFSE) and
Spain (AEE) date GDP-based cycles, so this replay puts the committees' own object — quarterly
GDP volume as first published — beside the monthly channels of replay_oecd.py, edition by
edition, on the OECD revisions database.

At each monthly edition the quarterly panel is rebuilt from that edition alone: GDP volume
(B1GQ_Q) and the quarterly means of industrial production and retail volume (the OECD carries
no employment vintages for these three).  The composite deviation statistic D is computed at
quarterly frequency (lookback four quarters, no smoothing — the tool's quarterly settings)
and the same two decisions are taken: a contraction is called at the first edition in which
D's latest value stands at or above 2 per cent, the peak dated by the tool's quarterly clause
(date_episode_quarterly) with the window closed at the latest quarter; the trough is called
by the real-time rule with a two-quarter confirmation and a half-point drop from the maximum.
Errors are in quarters; 'within the quarter' is an edition month inside the quarter after
the turning quarter (the first GDP print of quarter q arrives in the second month of q+1).
Three panels are run: GDP alone, the monthly channels alone (quarterly means), and all three.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/oecd_rt')
import pandas as pd, numpy as np
import bristow_rule_v3 as B
import replay_oecd as R
RT=R.RT
CHRON={'EA':[('2008-02','2009-05'),('2011-08','2013-02'),('2019-11','2020-05')],
       'FRA':[('2008-02','2009-05'),('2019-11','2020-05')],
       'ESP':[('2008-05','2009-11'),('2010-11','2013-05'),('2019-11','2020-05')]}
_gdp={}
def gdp_vintages(area):
    if area in _gdp: return _gdp[area]
    d=pd.read_csv(f'{RT}/{area}_B1GQ_Q_Q.csv',usecols=['EDITION','TIME_PERIOD','OBS_VALUE'])
    d['t']=pd.PeriodIndex(d.TIME_PERIOD,freq='Q').to_timestamp(); d['v']=pd.to_numeric(d.OBS_VALUE,errors='coerce')
    out={}
    for e,g in d.groupby('EDITION'):
        s=g.set_index('t').v.dropna().sort_index()
        if len(s)>=20: out[str(e)]=s.astype(float)
    _gdp[area]=out; return out
def qpanel(area, edition, use_gdp=True, use_monthly=True):
    chs=[]
    if use_gdp and edition in gdp_vintages(area): chs.append(('GDP',gdp_vintages(area)[edition]))
    if use_monthly:
        for nm in ('industrial production','retail volume'):
            V=R.vintages(area,nm)
            if edition in V: chs.append((nm,B.to_quarter(V[edition])))
    return chs
def qd(a,b): return (a.year-b.year)*4+((a.month-1)//3-(b.month-1)//3)
def walk_q(area, use_gdp, use_monthly, threshold=2.0, fall=2, drop=0.5, lookback=4, min_channels=1, band_t=0.12, band_p=0.01, peak_cap=4, min_cycle=5):
    E=sorted(set(gdp_vintages(area).keys())|set(R.editions(area,['industrial production','retail volume'])))
    peaks=[]; troughs=[]; state='quiet'; start=None; cur=None; susp=None
    for e in E:
        chs=qpanel(area,e,use_gdp,use_monthly)
        if len(chs)<min_channels: continue
        D=B.composite_deviation(chs,lookback,1,min_channels).dropna()
        if len(D)<12: continue
        latest=D.index[-1]
        if start is None: start=latest-pd.DateOffset(months=36)
        seg=D[start:]
        if not len(seg): continue
        if state=='recovering':
            if float(seg.iloc[-1])<threshold: state='quiet'
            continue
        if state=='quiet':
            if float(seg.iloc[-1])>=threshold:
                cross=latest
                for d,v in seg[::-1].items():
                    if v>=threshold: cross=d
                    else: break
                w0=cross-pd.DateOffset(months=3*(peak_cap+4))
                r=B.date_episode_quarterly(chs,w0,latest,band_trough=band_t,band_peak=band_p,lookback=lookback,peak_cap=peak_cap)
                if susp is not None and qd(cross,susp['cross'])<min_cycle:
                    cur=susp; cur['last']=r['peak'] if r['peak'] is not None else cur['last']
                else:
                    if susp is not None: peaks.append((susp['edition'],susp['date'],susp['last']))
                    cur=dict(edition=e,cross=cross,date=r['peak'],last=r['peak'],w0=w0)
                susp=None; state='contraction'
        else:
            r=B.date_episode_quarterly(chs,cur['w0'],latest,band_trough=band_t,band_peak=band_p,lookback=lookback,peak_cap=peak_cap)
            if r['peak'] is not None:
                cur['last']=r['peak']
                if cur['date'] is None: cur['date']=r['peak']; cur['edition']=e
            if len(seg)>=4 and float(seg.iloc[-4:].max())<threshold:
                susp=cur; start=latest-pd.DateOffset(months=9); state='quiet'; cur=None; continue
            at=seg.idxmax(); hi=float(seg.max()); after=seg[seg.index>at]
            if hi>=threshold and len(after)>=fall:
                tail=list(after.iloc[-fall:]); prev=float(after.iloc[-fall-1]) if len(after)>fall else hi
                falling=all(tail[k]<(tail[k-1] if k>0 else prev) for k in range(fall))
                if falling and (hi-float(after.iloc[-1]))>=drop:
                    if troughs and qd(at,troughs[-1][1])<min_cycle:
                        start=latest+pd.DateOffset(months=3); state='recovering'; susp=cur; cur=None; continue
                    troughs.append((e,at)); peaks.append((cur['edition'],cur['date'],cur['last']))
                    start=latest+pd.DateOffset(months=3); state='recovering'; cur=None
    if cur is not None: peaks.append((cur['edition'],cur['date'],cur['last']))
    if susp is not None: peaks.append((susp['edition'],susp['date'],susp['last']))
    return peaks,troughs
def match(calls, refs, tol=2):
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,c in enumerate(calls):
            if j in used or c[1] is None: continue
            e=qd(c[1],ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=calls[best[0]]; used.add(best[0])
    return got,[c for j,c in enumerate(calls) if j not in used]
def qlag(e, ref):
    """edition months after the turning quarter's last month"""
    et=R.ed_ts(e); qend=pd.Timestamp(ref.year,3*((ref.month-1)//3+1),1)
    return R.md(et,qend)
if __name__=='__main__':
    rows=[]
    for area,chron in CHRON.items():
        for label,ug,um in (('GDP alone',True,False),('production and retail, quarterly means',False,True),('GDP with production and retail',True,True)):
            peaks,troughs=walk_q(area,ug,um)
            P=[R.ts(p) for p,t in chron]; T=[R.ts(t) for p,t in chron]
            gp,op=match(peaks,P); gt,ot=match(troughs,T)
            print(f'\n=== {area}, {label}')
            for i,(pk,tr) in enumerate(chron):
                pkm,trm=R.ts(pk),R.ts(tr)
                a=gp.get(i); b=gt.get(i)
                ps=f'peak {pk[:4]}Q{(pkm.month-1)//3+1}: '+(f'called {a[0]} dated {a[1].year}Q{(a[1].month-1)//3+1} err {qd(a[1],pkm):+d} q, {qlag(a[0],pkm):+d} mo after the quarter; last {a[2].year}Q{(a[2].month-1)//3+1} ({qd(a[2],pkm):+d})' if a else 'not called')
                ts_=f'trough {tr[:4]}Q{(trm.month-1)//3+1}: '+(f'called {b[0]} dated {b[1].year}Q{(b[1].month-1)//3+1} err {qd(b[1],trm):+d} q, {qlag(b[0],trm):+d} mo after the quarter' if b else 'not called')
                print('  ',ps); print('  ',ts_)
                rows.append(dict(area=area,panel=label,peak=pk,trough=tr,peak_err=qd(a[1],pkm) if a else None,peak_lag=qlag(a[0],pkm) if a else None,trough_err=qd(b[1],trm) if b else None,trough_lag=qlag(b[0],trm) if b else None))
            print('   other peak calls:',[(e,f'{d.year}Q{(d.month-1)//3+1}' if d is not None else None) for e,d,l in op])
            print('   other trough calls:',[(e,f'{d.year}Q{(d.month-1)//3+1}') for e,d in ot])
    df=pd.DataFrame(rows); df.to_csv(f'{RT}/replay_oecd_q.csv',index=False)
    print('\n=== totals by panel (8 contractions; errors in quarters; within the quarter = edition month <= 3 months after the turning quarter ends)')
    for label,g in df.groupby('panel',sort=False):
        pe=g.peak_err.dropna(); te=g.trough_err.dropna(); pl=g.peak_lag.dropna(); tl=g.trough_lag.dropna()
        print(f'{label:40s} peaks called {len(pe)}/8 exact {(pe==0).sum()} w1 {(pe.abs()<=1).sum()} withinQ {(pl<=3).sum()} | troughs called {len(te)}/8 exact {(te==0).sum()} w1 {(te.abs()<=1).sum()} withinQ {(tl<=3).sum()}')
