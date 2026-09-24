"""First-print replay outside the United States, on the OECD's short-term-statistics
revisions database (every monthly edition since February 1999; fetch.py).

A genuine real-time run: the editions are walked in order, and at each one the panel —
industrial production, retail trade volume, employment where the database carries it — is
rebuilt from that edition alone and the composite deviation statistic D recomputed from it.
No official chronology enters at any point.  Two decisions are taken on D:

  a contraction is called at the first edition in which D's latest value stands at or above
  the threshold; the peak is dated then by the rule's own peak clause (date_episode) on the
  vintage, window closed at the latest month in hand, and re-dated at each later edition
  until the trough is called;
  the trough is called by the tool's real-time trough rule (real_time_trough_calls' decision,
  taken edition by edition): once D has fallen for `fall` consecutive months and by `drop`
  points from its maximum, the trough is the month of that maximum.  After the call the
  machine returns to quiet.

The calls are then matched to the committee's contractions (a call within six months of the
committee's month, one call per end), and every other call is listed as a false alarm.  The
last column re-dates each contraction on the final edition with the window the memo uses,
peak minus twelve to trough plus twelve — the current-vintage result on the same thin panel,
for comparison.  'Within the month' is an edition month no later than the month after the
turning-point month.  This is the level route on two or three channels; Japan's diffusion
route and Korea's growth-cycle route are not reproducible from these vintages, so their rows
are the level route's, not the shipped tool's.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
import bristow_rule_v3 as B
RT='/home/claude/lab/oecd_rt'
CHAN={'industrial production':('PRVM','BTE','IX'),'retail volume':('TOVM','G47','IX'),'employment':('EMP','_T','PS')}
# every committee contraction whose trough falls inside the editions (a peak before the first
# edition is marked 'pre' rather than scored as a miss)
CHRON={
 'USA':[('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')],
 'CAN':[('2008-10','2009-05'),('2020-02','2020-04')],
 'JPN':[('1997-05','1999-01'),('2000-11','2002-01'),('2008-02','2009-03'),('2012-03','2012-11'),('2018-10','2020-05')],
 'KOR':[('1996-03','1998-08'),('2000-08','2001-07'),('2002-12','2005-04'),('2008-01','2009-02'),('2011-08','2013-03'),('2017-09','2020-05')],
 'BRA':[('2000-12','2001-09'),('2002-10','2003-06'),('2008-07','2009-01'),('2014-03','2016-12'),('2019-12','2020-06')],
 'DEU':[('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')],
 'MEX':[('2000-09','2002-01'),('2008-06','2009-05'),('2019-05','2020-05')],
 'ZAF':[('2007-11','2009-08'),('2013-11','2017-04'),('2019-06','2020-04')],
 # the three quarterly chronologies, the committee's quarter written as its middle month
 # (the bench's convention); errors for these are read in quarters below
 'EA':[('2008-02','2009-05'),('2011-08','2013-02'),('2019-11','2020-05')],
 'FRA':[('2008-02','2009-05'),('2019-11','2020-05')],
 'ESP':[('2008-05','2009-11'),('2010-11','2013-05'),('2019-11','2020-05')],
}
QUARTERLY={'EA','FRA','ESP'}
def qerr(d, ref):
    """error in quarters between a called month and the committee's quarter"""
    return (d.year*4+(d.month-1)//3)-(ref.year*4+(ref.month-1)//3)
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def ts(s): return pd.Timestamp(s+'-01')
def ed_ts(e): return pd.Timestamp(int(e[:4]),int(e[4:]),1)
_cache={}
def vintages(area, name):
    key=(area,name)
    if key in _cache: return _cache[key]
    meas,act,unit=CHAN[name]
    try: d=pd.read_csv(f'{RT}/{area}_{meas}_M.csv',usecols=['UNIT_MEASURE','ACTIVITY','EDITION','TIME_PERIOD','OBS_VALUE'])
    except FileNotFoundError: _cache[key]={}; return {}
    d=d[(d.ACTIVITY==act)&(d.UNIT_MEASURE==unit)]
    d['t']=pd.to_datetime(d.TIME_PERIOD,format='%Y-%m'); d['v']=pd.to_numeric(d.OBS_VALUE,errors='coerce')
    out={}
    for e,g in d.groupby('EDITION'):
        s=g.set_index('t').v.dropna().sort_index()
        if len(s)>=40: out[str(e)]=s.astype(float)
    _cache[key]=out; return out
def panel(area, edition, names):
    return [(nm,B.procyclical(vintages(area,nm)[edition],'level')) for nm in names if edition in vintages(area,nm)]
def editions(area, names):
    E=set()
    for nm in names: E|=set(vintages(area,nm).keys())
    return sorted(E)
def walk(area, names, threshold=2.0, fall=4, drop=0.5, smooth=3, lookback=12, min_channels=2,
         band_t=0.12, band_p=0.01, peak_cap=18, min_cycle=15):
    """the state machine over the editions: returns peak calls [(edition, date, last_date)] and
    trough calls [(edition, date)]"""
    E=editions(area,names); peaks=[]; troughs=[]; state='quiet'; start=None; cur=None; susp=None
    for e in E:
        chs=panel(area,e,names)
        if len(chs)<min_channels: continue
        D=B.composite_deviation(chs,lookback,smooth,min_channels).dropna()
        if len(D)<24: continue
        latest=D.index[-1]
        if start is None: start=latest-pd.DateOffset(months=36)   # the first edition carries decades of history; the machine sees only the recent past
        seg=D[start:]
        if not len(seg): continue
        if state=='recovering':
            # after a trough call D is still above the threshold (the level is still below its
            # trailing maximum); a new contraction can be called only once D has come back down
            if float(seg.iloc[-1])<threshold: state='quiet'
            continue
        if state=='quiet':
            if float(seg.iloc[-1])>=threshold:
                # the first month of the run of D >= threshold that ends at the latest month
                cross=latest
                for d,v in seg[::-1].items():
                    if v>=threshold: cross=d
                    else: break
                w0=cross-pd.DateOffset(months=peak_cap+12)
                r=B.date_episode(chs,w0,latest,band_trough=band_t,band_peak=band_p,smooth=smooth,lookback=lookback,peak_cap=peak_cap)
                if susp is not None and md(cross,susp['cross'])<min_cycle:
                    # the same contraction, called again after a first print that was revised away:
                    # the first call stands as the call
                    cur=susp; cur['last']=r['peak'] if r['peak'] is not None else cur['last']
                else:
                    if susp is not None: peaks.append((susp['edition'],susp['date'],susp['last']))
                    cur=dict(edition=e,cross=cross,date=r['peak'],last=r['peak'],w0=w0)
                susp=None; state='contraction'
        else:
            # re-date the peak on this edition
            r=B.date_episode(chs,cur['w0'],latest,band_trough=band_t,band_peak=band_p,smooth=smooth,lookback=lookback,peak_cap=peak_cap)
            if r['peak'] is not None:
                cur['last']=r['peak']
                if cur['date'] is None: cur['date']=r['peak']; cur['edition']=e
            # the harness's reset: if D has stood below the threshold for twelve months and the
            # trough rule has not fired, the contraction is over without a trough call
            if len(seg)>=12 and float(seg.iloc[-12:].max())<threshold:
                susp=cur; start=latest-pd.DateOffset(months=11); state='quiet'; cur=None; continue
            at=seg.idxmax(); hi=float(seg.max())
            after=seg[seg.index>at]
            if hi>=threshold and len(after)>=fall:
                tail=list(after.iloc[-fall:]); prev=float(after.iloc[-fall-1]) if len(after)>fall else hi
                falling=all(tail[k]<(tail[k-1] if k>0 else prev) for k in range(fall))
                if falling and (hi-float(after.iloc[-1]))>=drop:
                    if troughs and md(at,troughs[-1][1])<min_cycle:
                        start=latest+pd.DateOffset(months=1); state='recovering'; susp=cur; cur=None; continue
                    troughs.append((e,at)); peaks.append((cur['edition'],cur['date'],cur['last']))
                    start=latest+pd.DateOffset(months=1); state='recovering'; cur=None
    if cur is not None: peaks.append((cur['edition'],cur['date'],cur['last']))   # a contraction still open
    if susp is not None: peaks.append((susp['edition'],susp['date'],susp['last']))
    return peaks,troughs
def final_dates(area, names, chron, smooth=3, lookback=12, band_t=0.12, band_p=0.01, peak_cap=18):
    """the rule on the last edition, window peak-12 .. trough+12 (the memo's retrospective window)"""
    E=editions(area,names); chs=panel(area,E[-1],names); out=[]
    for pk,tr in chron:
        pkm,trm=ts(pk),ts(tr)
        r=B.date_episode(chs,pkm-pd.DateOffset(months=12),trm+pd.DateOffset(months=12),band_trough=band_t,band_peak=band_p,smooth=smooth,lookback=lookback,peak_cap=peak_cap)
        out.append((r['peak'],r['trough']))
    return out
def match(calls, refs, tol=6):
    """one call per committee end, nearest within tol months; returns {ref index: call}, other calls"""
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,c in enumerate(calls):
            if j in used or c[1] is None: continue
            e=md(c[1],ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=calls[best[0]]; used.add(best[0])
    return got,[c for j,c in enumerate(calls) if j not in used]
def report(area, verbose=True, **kw):
    names=[nm for nm in CHAN if vintages(area,nm)]
    chron=CHRON[area]; E=editions(area,names)
    peaks,troughs=walk(area,names,**kw); fin=final_dates(area,names,chron)
    gp,op=match(peaks,[ts(p) for p,t in chron]); gt,ot=match(troughs,[ts(t) for p,t in chron])
    rows=[]
    for i,(pk,tr) in enumerate(chron):
        pkm,trm=ts(pk),ts(tr); r=dict(area=area,peak=pk,trough=tr)
        err=(lambda d,ref: qerr(d,ref)) if area in QUARTERLY else md
        if pkm<ed_ts(E[0]) and i not in gp:
            r.update(peak_edition='pre',peak_called='pre',peak_err=None,peak_lag=None,peak_at_trough_call='pre',peak_at_trough_call_err=None)
        elif i in gp:
            e,d,l=gp[i]; r.update(peak_edition=e,peak_called=d.strftime('%Y-%m'),peak_err=err(d,pkm),peak_lag=md(ed_ts(e),pkm),peak_at_trough_call=l.strftime('%Y-%m') if l is not None else '--',peak_at_trough_call_err=err(l,pkm) if l is not None else None)
        else: r.update(peak_edition='--',peak_called='--',peak_err=None,peak_lag=None,peak_at_trough_call='--',peak_at_trough_call_err=None)
        if i in gt:
            e,d=gt[i]; r.update(trough_edition=e,trough_called=d.strftime('%Y-%m'),trough_err=err(d,trm),trough_lag=md(ed_ts(e),trm))
        else: r.update(trough_edition='--',trough_called='--',trough_err=None,trough_lag=None)
        fp,ft=fin[i]
        r.update(peak_final=fp.strftime('%Y-%m') if fp is not None else '--',peak_final_err=err(fp,pkm) if fp is not None else None,
                 trough_final=ft.strftime('%Y-%m') if ft is not None else '--',trough_final_err=err(ft,trm) if ft is not None else None)
        rows.append(r)
    df=pd.DataFrame(rows)
    if verbose:
        print(f'\n=== {area}: channels {names}; editions {E[0]}..{E[-1]}; committee contractions inside the editions: {len(chron)}')
        print(df.drop(columns=['area']).to_string(index=False))
        print('   other peak calls (edition, date):',[(e,d.strftime('%Y-%m') if d is not None else None) for e,d,l in op])
        print('   other trough calls (edition, date):',[(e,d.strftime('%Y-%m')) for e,d in ot])
    return df,op,ot
if __name__=='__main__':
    areas=sys.argv[1:] or list(CHRON)
    allr=[]; FA={}
    for a in areas:
        df,op,ot=report(a); allr.append(df); FA[a]=(len(op),len(ot))
    dfall=pd.concat(allr); dfall.to_csv(f'{RT}/replay_oecd.csv',index=False)
    for label,df in (('monthly chronologies (errors in months)',dfall[~dfall.area.isin(QUARTERLY)]),('quarterly chronologies (errors in quarters; within 1 is the memo\'s tolerance)',dfall[dfall.area.isin(QUARTERLY)])):
      if not len(df): continue
      def cnt(col, denom=None):
        x=pd.to_numeric(df[col],errors='coerce').dropna(); n=len(df) if denom is None else denom
        return f'called {len(x)} of {n}, exact {(x==0).sum()}, within 1 {(x.abs()<=1).sum()}, within 3 {(x.abs()<=3).sum()}'
      npk=int((df.peak_edition!='pre').sum()); fa_p=sum(FA[a][0] for a in set(df.area)); fa_t=sum(FA[a][1] for a in set(df.area))
      print(f'\n--- {label}')
      lp=pd.to_numeric(df.peak_lag,errors='coerce'); lt=pd.to_numeric(df.trough_lag,errors='coerce')
      print(f'\n=== all {len(df)} contractions, {len(set(df.area))} economies')
      print('peaks, as first called      :',cnt('peak_err',npk),f'| edition lag months min/median/max {lp.min():.0f}/{lp.median():.0f}/{lp.max():.0f} | within the month {(lp<=1).sum()} | other peak calls {fa_p}')
      print('peaks, at the trough call   :',cnt('peak_at_trough_call_err',npk))
      print('peaks, final edition        :',cnt('peak_final_err'))
      print('troughs, as called          :',cnt('trough_err'),f'| edition lag months min/median/max {lt.min():.0f}/{lt.median():.0f}/{lt.max():.0f} | within the month {(lt<=1).sum()} | other trough calls {fa_t}')
      print('troughs, final edition      :',cnt('trough_final_err'))
