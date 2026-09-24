import sys, json, csv, datetime as dt
sys.path.insert(0,'research')
from _r28_lib import members, load_source, asof_date
DATES=[dt.date(2012,6,1),dt.date(2015,9,1),dt.date(2019,3,1),dt.date(2020,4,1),dt.date(2022,10,1),dt.date(2024,6,1)]
FREDMAP={'CMRMT':'CMRMTSPL','UNRATEv':'UNRATE','W875':'W875RX1','PHILLY':'GACDFSA066MSFRBPHI'}
CUR="data_archive/current_revised_and_spatial/"
def to_date(s):
    s=s[:10]; return dt.date(int(s[:4]),int(s[5:7]),int(s[8:10]))
def load_current(fred):
    o={}
    try:
        for r in csv.reader(open(CUR+fred+".csv")):
            if r and r[0][:1].isdigit() and len(r)>1 and r[1] not in("","."):
                o[to_date(r[0])]=float(r[1])
    except FileNotFoundError: return None
    return o
# ---- preload all vintage sources ONCE as (asof,op,value) tuples ----
ms,ch=members()
SRC_TUPLES={}
for name,m in ms.items():
    for s in m['store_vintage_sources']:
        if s in SRC_TUPLES: continue
        try: h,rr=load_source(s)
        except Exception: SRC_TUPLES[s]=[]; continue
        t=[]
        for r in rr:
            a=asof_date(r.get('series_id'))
            if a is None: continue
            try: v=float(r['value'])
            except: continue
            t.append((a,to_date(r['observation_period']),v))
        SRC_TUPLES[s]=t
        print('loaded',s,len(t),file=sys.stderr)
def asof_series(tuples,D):
    best={}
    for a,op,v in tuples:
        if a>D: continue
        c=best.get(op)
        if c is None or a>c[0]: best[op]=(a,v)
    return {op:val for op,(a,val) in best.items()}, max([a for a,_,_ in tuples if a<=D],default=None)
CURCACHE={}
def cur_for(fred):
    if fred not in CURCACHE: CURCACHE[fred]=load_current(fred)
    return CURCACHE[fred]
w=csv.writer(open('research/asof_replay_dryrun_v1.csv','w',newline=''))
w.writerow(['date','member','channel','status','asof_frontier_used','n_asof_obs',
            'latest_obs_period','latest_obs_asof','latest_obs_current','max_abs_divergence','divergence_where'])
summary={}
for D in DATES:
    summary[str(D)]={'asof':0,'fallback':0,'unrevised':0}
    for name,m in sorted(ms.items()):
        chn=m['channel']; srcs=m['store_vintage_sources']
        fred=m.get('fred_series') or FREDMAP.get(name)
        cur=cur_for(fred) if fred else None
        if not srcs:
            lc=max([d for d in cur if d<=D],default=None) if cur else None
            w.writerow([D,name,chn,'unrevised_exact','n/a',0,lc or '', '', cur[lc] if lc else '',0.0,'none(non-revising)'])
            summary[str(D)]['unrevised']+=1; continue
        tuples=[]
        for s in srcs: tuples+=SRC_TUPLES.get(s,[])
        asf,frontier=asof_series(tuples,D)
        if not asf:
            lc=max([d for d in cur if d<=D],default=None) if cur else None
            w.writerow([D,name,chn,'FALLBACK_current_revised','none<=D',0,lc or '','', cur[lc] if lc else '','','vintage_gap(pre-2020)'])
            summary[str(D)]['fallback']+=1; continue
        latest_op=max(asf); asof_latest=asf[latest_op]; cur_latest=cur.get(latest_op) if cur else None
        maxd=0.0
        if cur:
            for op,v in asf.items():
                if op in cur: maxd=max(maxd,abs(cur[op]-v))
        where='revision' if maxd>1e-9 else 'none(as-of==current)'
        w.writerow([D,name,chn,'AS_OF',frontier,len(asf),latest_op,round(asof_latest,4),
                    round(cur_latest,4) if cur_latest is not None else '',round(maxd,4),where])
        summary[str(D)]['asof']+=1
json.dump(summary,open('research/r28_summary.json','w'),indent=1)
for D in DATES: print(D, summary[str(D)])
