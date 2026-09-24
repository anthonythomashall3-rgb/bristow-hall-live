#!/usr/bin/env python3
"""CH-R25 ALFRED roster revision certification (read-only, network, research/ only).
Zero store/vault/config writes. Resume-safe cache under research/prefetch/alfred_*.
Never prints the API key.
"""
import csv, json, os, sys, time, urllib.request, urllib.parse, statistics, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = os.path.join(ROOT, 'research/prefetch/alfred_meta')
OBS  = os.path.join(ROOT, 'research/prefetch/alfred_obs')
os.makedirs(META, exist_ok=True); os.makedirs(OBS, exist_ok=True)
LOG = open(os.path.join(ROOT, 'research/CH-R25_compute.log'), 'a')
def log(*a):
    m=' '.join(str(x) for x in a); LOG.write(m+'\n'); LOG.flush(); print(m)

def api_key():
    for line in open(os.path.join(ROOT,'live_data/config/local.env')):
        if line.startswith('FRED_API_KEY='):
            return line.split('=',1)[1].strip()
    raise SystemExit('no FRED_API_KEY')
KEY = api_key()
BASE = 'https://api.stlouisfed.org/fred/'

def fetch(path, params, cachefile, tries=2):
    if os.path.exists(cachefile):
        try:
            return json.load(open(cachefile))
        except Exception:
            pass
    p = dict(params); p['api_key']=KEY; p['file_type']='json'
    url = BASE+path+'?'+urllib.parse.urlencode(p)
    for t in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.load(r)
            json.dump(data, open(cachefile,'w'))
            time.sleep(1.0)  # throttle ~1 req/s
            return data
        except Exception as e:
            # scrub key from any error text
            msg=str(e).replace(KEY,'<KEY>')
            log('  try',t+1,'fail',path,params.get('series_id'),msg[:120])
            time.sleep(1.5)
    json.dump({'error':'fetch_failed'}, open(cachefile,'w'))
    return {'error':'fetch_failed'}

def load_roster():
    rows=list(csv.DictReader(open(os.path.join(ROOT,'data_vault/catalog/metric_catalog.csv'))))
    out=[]
    for r in rows:
        if (r['local_vintage_file_count'] or '0').strip() in ('','0'):
            out.append((r['series_id'], (r['provider_series_id'] or r['series_id']).strip(),
                        r['provider'], r['revision_class']))
    return out

def vintagedates(fid):
    d = fetch('series/vintagedates', {'series_id':fid, 'limit':10000},
              os.path.join(META, fid+'.vintages.json'))
    if isinstance(d,dict) and 'vintage_dates' in d:
        return d['vintage_dates']
    return []

def obs_asof(fid, vintage):
    d = fetch('series/observations',
              {'series_id':fid,'realtime_start':vintage,'realtime_end':vintage},
              os.path.join(OBS, f'{fid}__{vintage}.json'))
    out={}
    for o in (d.get('observations',[]) if isinstance(d,dict) else []):
        v=o.get('value','.')
        if v not in ('.','',None):
            try: out[o['date']]=float(v)
            except ValueError: pass
    return out

def rebase_ratio(early, late, common):
    """CH-R21 rebase awareness: ratio late/early per common date; if tightly clustered
    around a single constant != 1, revision is a rescale (rebasing), not information."""
    ratios=[late[d]/early[d] for d in common if early[d]!=0]
    if len(ratios)<5: return None
    med=statistics.median(ratios)
    if med==0: return None
    # coefficient of variation of ratios
    mu=statistics.mean(ratios)
    sd=statistics.pstdev(ratios)
    cv = sd/abs(mu) if mu else 9.9
    return {'median_ratio':med, 'cv_ratio':cv}

def revstats(fid, vints):
    early_v, late_v = vints[0], vints[-1]
    early = obs_asof(fid, early_v)
    late  = obs_asof(fid, late_v)
    common=[d for d in early if d in late]
    if not common:
        return {'n_common':0}
    diffs=[late[d]-early[d] for d in common]
    absd=[abs(x) for x in diffs]
    levels=[abs(late[d]) for d in common]
    n=len(common)
    revised=sum(1 for x in absd if x>1e-9)
    share_revised=revised/n
    mean_abs=statistics.mean(absd)
    p95_abs=sorted(absd)[max(0,int(math.ceil(0.95*n))-1)]
    med_level=statistics.median([abs(late[d]) for d in common]) or 1e-9
    p95_pct=100.0*p95_abs/med_level if med_level else 0.0
    pos=sum(1 for x in diffs if x>1e-9)
    pos_share=pos/max(1,revised)
    rb=rebase_ratio(early,late,common)
    return {'n_common':n,'n_early_obs':len(early),'n_late_obs':len(late),
            'early_vintage':early_v,'late_vintage':late_v,
            'share_revised':round(share_revised,4),'mean_abs_rev':mean_abs,
            'p95_abs_rev':p95_abs,'p95_pct_of_level':round(p95_pct,4),
            'median_level':med_level,'pos_share':round(pos_share,4),
            'rebase_median_ratio': (round(rb['median_ratio'],6) if rb else ''),
            'rebase_cv': (round(rb['cv_ratio'],6) if rb else '')}

def classify(st, nvint):
    if nvint<2: return 'no_vintage_evidence'
    if st.get('n_common',0)==0: return 'no_overlap'
    sr=st['share_revised']; p95pct=st['p95_pct_of_level']
    rb_cv=st.get('rebase_cv',''); rb_ratio=st.get('rebase_median_ratio','')
    # rebasing artifact: tight proportional ratio, ratio clearly != 1
    if rb_cv!='' and rb_cv<0.02 and rb_ratio!='' and abs(rb_ratio-1.0)>0.02:
        return 'rebasing_artifact'
    if sr<0.02: return 'never_revised'
    if sr<0.20 and p95pct<1.0: return 'negligible_revision'
    if p95pct>=10.0: return 'heavily_revised'
    return 'moderately_revised'

def main():
    roster=load_roster()
    log(f'== CH-R25 roster size (no local vintage lanes): {len(roster)}')
    # PHASE 1: vintagedates
    vmap={}
    for i,(sid,fid,prov,rc) in enumerate(roster):
        vd=vintagedates(fid)
        vmap[fid]=vd
        if i%25==0: log(f'  vintagedates {i}/{len(roster)} {fid} -> {len(vd)} vintages')
    log('== phase1 done')
    # PHASE 2: stats for >=2 vintages
    out_rows=[]
    multi=[x for x in roster if len(vmap[x[1]])>=2]
    log(f'== series with >=2 ALFRED vintages: {len(multi)}')
    for j,(sid,fid,prov,rc) in enumerate(roster):
        vd=vmap[fid]; nvint=len(vd)
        st={}
        if nvint>=2:
            st=revstats(fid, vd)
        cls=classify(st, nvint)
        out_rows.append({'series_id':sid,'fred_id':fid,'provider':prov,
            'catalog_revision_class':rc,'n_alfred_vintages':nvint,
            'first_vintage': vd[0] if vd else '', 'last_vintage': vd[-1] if vd else '',
            'class_r25':cls, **{k:st.get(k,'') for k in
              ['n_common','n_early_obs','n_late_obs','early_vintage','late_vintage',
               'share_revised','mean_abs_rev','p95_abs_rev','p95_pct_of_level',
               'median_level','pos_share','rebase_median_ratio','rebase_cv']}})
        if j%25==0: log(f'  stats {j}/{len(roster)} {fid} {cls}')
    cols=['series_id','fred_id','provider','catalog_revision_class','n_alfred_vintages',
          'first_vintage','last_vintage','class_r25','n_common','n_early_obs','n_late_obs',
          'early_vintage','late_vintage','share_revised','mean_abs_rev','p95_abs_rev',
          'p95_pct_of_level','median_level','pos_share','rebase_median_ratio','rebase_cv']
    outp=os.path.join(ROOT,'research/revision_certification_v2_roster.csv')
    with open(outp,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(out_rows)
    log('== wrote', outp, len(out_rows),'rows')
    from collections import Counter
    log('== class counts:', dict(Counter(r['class_r25'] for r in out_rows)))

if __name__=='__main__':
    main()
