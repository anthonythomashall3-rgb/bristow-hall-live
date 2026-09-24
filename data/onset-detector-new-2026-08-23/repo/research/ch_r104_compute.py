# CH-R104: reproduce CH-R20 revision method over ALL vintage-bearing lanes now landed.
# Method identical to research/ch_r20_compute.py: first-print = value in EARLIEST as-of
# vintage in corpus for an obs; latest = NEWEST vintage; revision = latest-first per obs;
# measurable = obs covered by >=2 distinct vintages. Only change vs R20: base_files is
# auto-discovered from source_heads (adapter contains 'vintage'), and acc is keyed by
# (base,op) so a multi-base blob could not cross-contaminate (all blobs measured single-base).
import json,glob,os,re,sys,statistics as st,csv
sys.path.insert(0,'research'); from ch_r20_stream import stream_records
HEADS='live_data/runtime/source_heads'
def fp(sha): return glob.glob(f'live_data/store/normalized/sha256/{sha[:2]}/{sha}*.json')[0]
ASOF=re.compile(r'ASOF(\d{8})$'); STRIP=re.compile(r'\.(DEEP|NEAR)?ASOF\d{8}$')
# discover vintage sources
heads={}
for p in glob.glob(HEADS+'/*.json'):
    d=json.load(open(p)); heads[d['source_id']]=d
vint={sid:d for sid,d in heads.items() if 'vintage' in (d.get('adapter') or '')}
# map base -> list of (source_id, sha). base = first record's stripped id (single-base blobs)
base_files={}
base_provider={}
for sid,d in sorted(vint.items()):
    sha=d['normalized_sha256']; f=fp(sha)
    b=None
    for r in stream_records(f, maxrec=1):
        b=STRIP.sub('', r['series_id']); break
    base_files.setdefault(b,[]).append((sid,sha))
json.dump({k:v for k,v in base_files.items()},open('research/revision_rerank/base_files.json','w'),indent=1)
def pctile(xs,q):
    if not xs: return None
    xs=sorted(xs); k=(len(xs)-1)*q; fi=int(k); c=min(fi+1,len(xs)-1)
    return xs[fi]+(xs[c]-xs[fi])*(k-fi)
rows=[]
for base in sorted(base_files):
    acc={}; floor=None; edge=None; nrec=0; lanes=set()
    for sid,sha in base_files[base]:
        lanes.add('deep' if 'deep' in sid else 'std')
        for r in stream_records(fp(sha)):
            nrec+=1; sid_r=r['series_id']; m=ASOF.search(sid_r)
            if not m: continue
            ak=m.group(1)
            if floor is None or ak<floor: floor=ak
            if edge is None or ak>edge: edge=ak
            try: val=float(r.get('value'))
            except (TypeError,ValueError): continue
            op=r['observation_period']; e=acc.get(op)
            if e is None: acc[op]=[ak,val,ak,val]
            else:
                if ak<e[0]: e[0]=ak; e[1]=val
                if ak>e[2]: e[2]=ak; e[3]=val
    absrevs=[]; pcts=[]; signs=[]; nrev=0; n=0
    for op,(a0,fv,a1,lv) in acc.items():
        if a0==a1: continue
        n+=1; rev=lv-fv; ar=abs(rev); absrevs.append(ar)
        lvl=abs(lv) if lv!=0 else (abs(fv) if fv!=0 else None)
        if lvl: pcts.append(ar/lvl*100.0)
        if ar>1e-9: nrev+=1; signs.append(1 if rev>0 else -1)
    meanabs=st.mean(absrevs) if absrevs else 0.0
    var=st.pvariance(absrevs) if len(absrevs)>1 else 0.0
    p95=pctile(absrevs,0.95); p95pct=pctile(pcts,0.95)
    medlvl=st.median([abs(lv) for _,(_,_,_,lv) in acc.items() if lv]) if acc else None
    share=(nrev/n) if n else 0.0
    posb=(sum(1 for s in signs if s>0)/len(signs)) if signs else None
    rows.append(dict(base=base,lanes='+'.join(sorted(lanes)),nrec=nrec,
        floor_asof=floor,edge_asof=edge,n_obs_total=len(acc),n_obs_measurable=n,
        share_revised=round(share,4),mean_abs_rev=meanabs,rev_variance=var,
        p95_abs_rev=p95,p95_pct_of_level=p95pct,median_level=medlvl,pos_share=posb))
    print(f"done {base:18s} lanes={rows[-1]['lanes']:8s} nrec={nrec:>9} n={n:>6} share={share:.4f} p95%={p95pct}",flush=True)
cols=['base','lanes','nrec','floor_asof','edge_asof','n_obs_total','n_obs_measurable','share_revised','mean_abs_rev','rev_variance','p95_abs_rev','p95_pct_of_level','median_level','pos_share']
with open('research/revision_rerank/revision_rerank_v1.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); [w.writerow({k:r.get(k) for k in cols}) for r in rows]
json.dump(rows,open('research/revision_rerank/rows_raw.json','w'),indent=1)
print("WROTE rows=",len(rows))
