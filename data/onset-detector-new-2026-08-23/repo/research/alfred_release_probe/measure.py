import json,glob,os,statistics,csv
from datetime import date

CORP='research/prefetch/alfred_release'
def pd(s): 
    y,m,d=s.split('-'); return date(int(y),int(m),int(d))
def add_months(d,n):
    m=d.month-1+n; y=d.year+m//12; m=m%12+1
    return date(y,m,1)
def period_end(refstart,freq):
    # refstart = period start date; end = last day of period
    if freq=='q':
        nxt=add_months(refstart,3)
    elif freq=='m':
        nxt=add_months(refstart,1)
    elif freq=='w':
        # weekly: FRED weekly date is week-ending; treat date as period end itself
        return refstart.toordinal()
    else:
        nxt=add_months(refstart,1)
    return date(nxt.year,nxt.month,1).toordinal()-1  # last day prev

def infer_freq(dates):
    if len(dates)<3: return 'm'
    gaps=sorted((dates[i+1]-dates[i]).days for i in range(len(dates)-1))
    med=gaps[len(gaps)//2]
    if med<=10: return 'w'
    if med<=45: return 'm'
    return 'q'

rows=[]
for f in sorted(glob.glob(CORP+'/*.json')):
    sid=os.path.basename(f).replace('__ot4.json','')
    d=json.load(open(f))
    if isinstance(d,dict) and 'error' in d:
        rows.append(dict(series=sid,status='ERROR:'+d['error'],n=0)); continue
    obs=d.get('observations',[])
    # keep only real releases with realtime_start
    recs=[o for o in obs if o.get('realtime_start') and o.get('date')]
    refs=sorted(pd(o['date']) for o in recs)
    freq=infer_freq(refs)
    lags=[]
    for o in recs:
        rs=pd(o['realtime_start'])
        pe_ord=period_end(pd(o['date']),freq)
        lags.append(rs.toordinal()-pe_ord)
    lags_sorted=sorted(lags)
    def q(p):
        if not lags_sorted: return None
        return lags_sorted[min(len(lags_sorted)-1,int(p*len(lags_sorted)))]
    rows.append(dict(
        series=sid,status='ok',n=len(recs),freq=freq,
        ref_min=min(refs).isoformat() if refs else None,
        ref_max=max(refs).isoformat() if refs else None,
        rt_min=min(pd(o['realtime_start']) for o in recs).isoformat(),
        rt_max=max(pd(o['realtime_start']) for o in recs).isoformat(),
        lag_median=statistics.median(lags) if lags else None,
        lag_p90=q(0.90),lag_max=max(lags) if lags else None,
        lag_min=min(lags) if lags else None,
        neg_lag_count=sum(1 for x in lags if x<0),
    ))
json.dump(rows,open('research/alfred_release_probe/per_series.json','w'),indent=2)
for r in rows:
    print(f"{r['series']:22s} {r['status']:14s} n={r.get('n'):>4} freq={r.get('freq','-')} ref=[{r.get('ref_min')}..{r.get('ref_max')}] rt=[{r.get('rt_min')}..{r.get('rt_max')}] lag med={r.get('lag_median')} p90={r.get('lag_p90')} max={r.get('lag_max')} neg={r.get('neg_lag_count')}")
