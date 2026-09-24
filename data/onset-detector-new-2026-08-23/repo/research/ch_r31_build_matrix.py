import csv,re,os,json,collections

LANES=[l.strip() for l in open('research/_r31_lanes.txt') if l.strip()]

def base_of(lane):
    b=lane
    for suf in ('_fredmd_panel_vintages_deep','_api_vintages_deep','_fredmd_panel_vintages',
                '_api_vintages','_vintages_deep','_vintages','_api_current','_current_revised',
                '_current','_live','_daily','_monthly','_weekly','_quarterly'):
        if b.endswith(suf): b=b[:-len(suf)]; break
    return b

def mode_of(lane):
    if lane.endswith('_vintages_deep'): return 'deep'
    if lane.endswith('_vintages'): return 'vintage'
    return 'current'

# store coverage: base -> set(modes) ; also track provider tag (fredmd panel vs api)
store=collections.defaultdict(lambda:{'current':None,'vintage':None,'deep':None,'lanes':[]})
for l in LANES:
    b=base_of(l); m=mode_of(l)
    store[b]['lanes'].append(l)
    store[b][m]=l

# fred_id guess: uppercase the token after provider prefix
def fred_id_guess(base):
    b=base
    for pfx in ('fred_','philadelphia_','census_','treasury_','bls_','dol_','nyfed_','fhfa_',
                'fdic_','fema_','cdc_','ofr_','philly_'):
        if b.startswith(pfx): b=b[len(pfx):]; break
    return b.upper()

# R25 roster: revision class per fred series
r25={}
for r in csv.DictReader(open('research/revision_certification_v2_roster.csv')):
    r25[r['fred_id'].upper()]={'class':r['class_r25'],'nv':r['n_alfred_vintages'],
        'fv':r['first_vintage'],'lv':r['last_vintage'],'share':r['share_revised']}

# R26 survey candidates
r26={}
for r in csv.DictReader(open('research/hf_universe_survey_v1.csv')):
    fid=(r.get('fred_id') or r.get('candidate') or '').upper()
    r26[fid]={'held':r.get('held'),'rev':r.get('revision_class'),'route':r.get('route'),
              'depth_s':r.get('depth_start'),'depth_e':r.get('depth_end'),'tier':r.get('tier')}

# FRED-MD panel
fredmd={}
for r in csv.DictReader(open('research/revision_certification_v3_fredmd_panel.csv')):
    fredmd[r['column'].upper()]={'class':r['class'],'vp':r['vintages_present'],'share':r['share_revised']}

# RTDSM vars from prefetch cache
rtdsm=[d for d in os.listdir('research/prefetch/rtdsm') if not d.startswith('_')]

# NBER macrohistory catalog
nber=[]
nb='research/prefetch/nber_macrohistory'
for root,_,files in os.walk(nb):
    for f in files:
        if f.endswith(('.csv','.json','.txt')) and not f.startswith('_'):
            nber.append(os.path.relpath(os.path.join(root,f),nb))

# fred_miss
fmiss=[d for d in os.listdir('research/prefetch/fred_miss') if not d.startswith('_')]

# ---- build universe of rows ----
rows=[]
def cell_collapse(cls,share):
    if cls in ('never_revised','negligible_revision','never_revised_or_negligible'): return 'HELD'
    if cls in ('rebasing_artifact',): return 'PARTIAL'  # growth collapses, level doesn't
    if cls in ('no_vintage_evidence','no_overlap','',None): return 'MISSING'  # unknown->treat missing
    return 'MISSING'  # revised classes -> not collapse

def estimate_layer(cls):
    # estimate-layer eligible if genuinely revised (revision layer = estimate vs final)
    if cls in ('heavily_revised','moderately_revised','rebasing_artifact'): return 'HELD'
    return 'MISSING'

seen=set()
def emit(sid,fred_id,source,note):
    if fred_id in seen: return
    seen.add(fred_id)
    st=None
    # find store base matching this fred_id
    for b,cov in store.items():
        if fred_id_guess(b)==fred_id:
            st=cov;break
    latest = 'HELD' if (st and st['current']) else 'MISSING'
    vint   = 'HELD' if (st and st['deep']) else ('PARTIAL' if (st and st['vintage']) else 'MISSING')
    cls=(r25.get(fred_id,{}).get('class') or fredmd.get(fred_id,{}).get('class') or '')
    share=(r25.get(fred_id,{}).get('share') or fredmd.get(fred_id,{}).get('share') or '')
    # first release: NO store lane exists for any series -> MISSING unless collapse HELD (then equals latest)
    coll=cell_collapse(cls,share)
    first = 'HELD' if coll=='HELD' and latest=='HELD' else 'MISSING'
    rows.append(dict(series_id=sid,fred_id=fred_id,source=source,rev_class=cls or '?',
        latest=latest,vintage=vint,first_release=first,collapse=coll,
        estimate_layer=estimate_layer(cls),note=note))

# store members first
for b,cov in sorted(store.items()):
    fid=fred_id_guess(b)
    emit(cov['lanes'][0],fid,'store','+'.join(m for m in('current','vintage','deep') if cov[m]))
# R25 roster
for fid,d in sorted(r25.items()):
    emit('roster:'+fid,fid,'R25_roster',d['class'])
# R26 survey
for fid,d in sorted(r26.items()):
    if fid: emit('survey:'+fid,fid,'R26_survey',d.get('rev') or '')
# FRED-MD panel
for fid,d in sorted(fredmd.items()):
    emit('fredmd:'+fid,fid,'FREDMD_panel',d['class'])
# RTDSM vars
for v in sorted(rtdsm):
    emit('rtdsm:'+v,('RTDSM_'+v).upper(),'RTDSM_cache','quarterly_vintage_cache')
# NBER + fred_miss listed as candidates (identity-heavy) - roll up as rows w/o fred match
for v in sorted(fmiss):
    emit('miss:'+v,v.upper(),'fred_miss_cache','never_revised_daily_or_shiller')

out='research/timedata_gap_matrix_v1.csv'
with open(out,'w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=['series_id','fred_id','source','rev_class','latest','vintage','first_release','collapse','estimate_layer','note'])
    w.writeheader()
    for r in rows: w.writerow(r)

# summary
import collections as C
def col(k): 
    c=C.Counter(r[k] for r in rows); return dict(c)
print("ROWS",len(rows))
for k in ('latest','vintage','first_release','collapse','estimate_layer'):
    print(k,col(k))
print("store_bases",len(store),"rtdsm",len(rtdsm),"nber_files",len(nber),"fred_miss",len(fmiss))
print("WROTE",out)
