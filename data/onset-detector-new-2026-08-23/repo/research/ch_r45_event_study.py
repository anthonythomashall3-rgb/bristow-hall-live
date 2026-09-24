#!/usr/bin/env python3
"""CH-R45 REVISION EVENT STUDY (S12/S13) — read-only, network, research/ only.
Zero store/vault/config writes. Resume-safe cache under research/prefetch/alfred_final.

Question: do FIRST PRINTS systematically UNDERSTATE deterioration near recession onsets
(the known payroll early-recession bias)? Per member with true ALFRED vintage coverage,
per 1969-> onset: first print vs final in the 6 months around the NBER peak.

first print  = ot4 (initial release) value for each obs date (left-censored obs excluded).
final        = current latest-vintage value for same obs date.
bad_sign     = +1 if series RISES in recession (up=bad: claims/unrate/sahm),
               -1 if series FALLS in recession (down=bad: payems/indpro/gdp/houst/...).
revision        = final - first_print
understatement  = bad_sign * (final - first_print)
   > 0  => first print looked BETTER than the final truth => understated deterioration.
"""
import csv, json, os, time, urllib.request, urllib.parse, statistics, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL  = os.path.join(ROOT, 'research/prefetch/alfred_release')
FIN  = os.path.join(ROOT, 'research/prefetch/alfred_final'); os.makedirs(FIN, exist_ok=True)
LOG  = open(os.path.join(ROOT, 'research/CH-R45_compute.log'), 'a')
def log(*a):
    m=' '.join(str(x) for x in a); LOG.write(m+'\n'); LOG.flush(); print(m)

def api_key():
    for line in open(os.path.join(ROOT,'live_data/config/local.env')):
        if line.startswith('FRED_API_KEY='):
            return line.split('=',1)[1].strip()
    raise SystemExit('no FRED_API_KEY')
KEY=api_key(); BASE='https://api.stlouisfed.org/fred/'

def fetch_final(series, cachefile, tries=3):
    if os.path.exists(cachefile):
        try:
            d=json.load(open(cachefile))
            if 'error' not in d: return d
        except Exception: pass
    p={'series_id':series,'api_key':KEY,'file_type':'json'}  # no realtime -> latest vintage
    url=BASE+'series/observations?'+urllib.parse.urlencode(p)
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: data=json.load(r)
            json.dump(data, open(cachefile,'w')); time.sleep(1.0); return data
        except Exception as e:
            log('  try',t+1,'fail',series,str(e).replace(KEY,'<KEY>')[:80]); time.sleep(2.0)
    json.dump({'error':'fetch_failed'}, open(cachefile,'w')); return {'error':'fetch_failed'}

# member -> bad_sign (+1 up-in-recession, -1 down-in-recession)
BAD = {'PAYEMS':-1,'INDPRO':-1,'GDPC1':-1,'HOUST':-1,'PERMIT':-1,'CMRMTSPL':-1,
       'TCU':-1,'UMCSENT':-1,'W875RX1':-1,'GACDFSA066MSFRBPHI':-1,
       'ICSA':1,'IURSA':1,'UNRATE':1,'SAHMREALTIME':1}

# NBER business-cycle PEAK months (recession onsets), 1969->
ONSETS = [('1969-12',1969,12),('1973-11',1973,11),('1980-01',1980,1),('1981-07',1981,7),
          ('1990-07',1990,7),('2001-03',2001,3),('2007-12',2007,12),('2020-02',2020,2)]

def ym(d):  # 'YYYY-MM-DD' -> (y,m)
    return (int(d[:4]), int(d[5:7]))
def monthspan(y1,m1,y2,m2):
    return (y2-y1)*12 + (m2-m1)

def load_firstprint(series):
    f=os.path.join(REL, series+'__ot4.json')
    if not os.path.exists(f): return None
    d=json.load(open(f))
    obs=d.get('observations',[])
    if not obs: return None
    floor=min(o['realtime_start'] for o in obs)
    fp={}
    for o in obs:
        if o['realtime_start']==floor: continue   # exclude left-censored
        if o['value'] in ('.',''): continue
        fp[o['date']]=(float(o['value']), o['realtime_start'])
    return fp

def load_final(series):
    d=fetch_final(series, os.path.join(FIN, series+'__final.json'))
    fin={}
    for o in d.get('observations',[]):
        if o['value'] in ('.',''): continue
        fin[o['date']]=float(o['value'])
    return fin

# level-revision is confounded by rebasing/benchmarking for real-dollar & index series;
# the DELTA (period-over-period change) view cancels any uniform vintage level offset and
# is the clean "did the first-print change understate the deterioration" test (S13 target).
REBASE_CONFOUND={'GDPC1','CMRMTSPL','W875RX1','INDPRO','PAYEMS'}  # level view confounded

MEMBERS=list(BAD.keys())
rows=[]        # per member x episode aggregate
detail=[]      # per obs
for series in MEMBERS:
    fp=load_firstprint(series)
    if fp is None:
        log(series,'no first-print cache -> skip'); continue
    fin=load_final(series)
    bad=BAD[series]; conf=1 if series in REBASE_CONFOUND else 0
    # prev-obs map (period-over-period) over the union of dated obs, per vintage independently
    fp_dates=sorted(fp); fp_prev={d:(fp_dates[i-1] if i>0 else None) for i,d in enumerate(fp_dates)}
    fin_dates=sorted(fin); fin_prev={d:(fin_dates[i-1] if i>0 else None) for i,d in enumerate(fin_dates)}
    for label,oy,om in ONSETS:
        win=[]
        for d in sorted(fp):
            fpv,rts=fp[d]
            y,m=ym(d); off=monthspan(oy,om,y,m)
            if not (-2<=off<=3) or d not in fin: continue
            fv=fin[d]; rev=fv-fpv; und=bad*rev
            pct = 100.0*rev/abs(fpv) if fpv!=0 else 0.0
            # delta view: change vs previous obs, first-print vs final
            und_d=None; fpd=fnd=None
            pd_fp=fp_prev.get(d); pd_fn=fin_prev.get(d)
            if pd_fp and pd_fp in fp and pd_fp==pd_fn and pd_fp in fin:
                fpd=fpv-fp[pd_fp][0]; fnd=fv-fin[pd_fp]; und_d=bad*(fnd-fpd)
            win.append((d,off,fpv,fv,rev,und,pct,und_d,fpd,fnd))
            detail.append([series,label,d,off,round(fpv,3),round(fv,3),round(rev,4),
                           round(und,4),round(pct,4),
                           '' if und_d is None else round(und_d,4),
                           '' if fpd is None else round(fpd,4),
                           '' if fnd is None else round(fnd,4)])
        if not win: continue
        unds=[w[5] for w in win]; pcts=[w[6] for w in win]; revs=[w[4] for w in win]
        dund=[w[7] for w in win if w[7] is not None]
        n=len(win); pos=sum(1 for u in unds if u>0)
        posd=sum(1 for u in dund if u>0)
        rows.append([series,bad,conf,label,n,
                     round(statistics.mean([w[2] for w in win]),3),
                     round(statistics.mean([w[3] for w in win]),3),
                     round(statistics.mean(revs),4),
                     round(statistics.mean(unds),4),
                     round(statistics.mean(pcts),4),
                     round(pos/n,3),
                     len(dund),
                     round(statistics.mean(dund),4) if dund else '',
                     round(posd/len(dund),3) if dund else ''])
        log(f"{series:20} {label} n={n} lvl_und={statistics.mean(unds):+.2f}({pos}/{n}) "
            f"Δund={statistics.mean(dund):+.4f}({posd}/{len(dund)})" if dund else
            f"{series:20} {label} n={n} lvl_und={statistics.mean(unds):+.2f}({pos}/{n}) Δ=NA")

os.makedirs(os.path.join(ROOT,'research'),exist_ok=True)
with open(os.path.join(ROOT,'research/revision_event_study_v1.csv'),'w',newline='') as fo:
    w=csv.writer(fo)
    w.writerow(['member','bad_sign','rebase_confound','episode','n_obs',
                'mean_first_print','mean_final','mean_lvl_revision','mean_lvl_understatement',
                'mean_pct_revision','lvl_consistency_frac','n_delta',
                'mean_delta_understatement','delta_consistency_frac'])
    w.writerows(rows)
with open(os.path.join(ROOT,'research/revision_event_study_detail_v1.csv'),'w',newline='') as fo:
    w=csv.writer(fo)
    w.writerow(['member','episode','obs_date','month_off','first_print','final',
                'lvl_revision','lvl_understatement','pct_revision',
                'delta_understatement','first_print_delta','final_delta'])
    w.writerows(detail)
log('WROTE', len(rows),'aggregate rows,',len(detail),'detail rows')
