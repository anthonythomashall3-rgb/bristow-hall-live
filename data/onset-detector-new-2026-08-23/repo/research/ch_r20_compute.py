import json,glob,os,re,sys
sys.path.insert(0,'research'); from ch_r20_stream import stream_records
bases=json.load(open('research/CH-R20_base_files.json'))
def fullpath(sha):
    return glob.glob(f'live_data/store/normalized/sha256/{sha[:2]}/{sha}*.json')[0]
def asofkey(sid):
    m=re.search(r'ASOF(\d{8})$',sid)
    return m.group(1) if m else None
rows=[]
perobs_dump=open('research/revision_certification_perobs_sample.csv','w')
perobs_dump.write("base,obs_period,first_asof,first_val,last_asof,last_val,abs_rev,pct_rev\n")
import statistics as st
for base in sorted(bases):
    files=bases[base]
    # obs -> [min_asof,minval,max_asof,maxval]
    acc={}
    floor=None; edge=None; nrec=0; lanes=set()
    for src,sha,sz in files:
        lanes.add('deep' if 'deep' in src else 'std')
        fp=fullpath(sha)
        for r in stream_records(fp):
            nrec+=1
            sid=r['series_id']; ak=asofkey(sid)
            if ak is None: continue
            if floor is None or ak<floor: floor=ak
            if edge is None or ak>edge: edge=ak
            v=r.get('value')
            try: val=float(v)
            except (TypeError,ValueError): continue
            op=r['observation_period']
            e=acc.get(op)
            if e is None:
                acc[op]=[ak,val,ak,val]
            else:
                if ak<e[0]: e[0]=ak; e[1]=val
                if ak>e[2]: e[2]=ak; e[3]=val
    # compute revisions
    absrevs=[]; pcts=[]; signs=[]; nrev=0; n=0
    sample=[]
    for op,(a0,fv,a1,lv) in acc.items():
        if a0==a1:  # only one vintage covers this obs -> cannot measure revision
            continue
        n+=1
        rev=lv-fv; ar=abs(rev)
        absrevs.append(ar)
        lvl=abs(lv) if lv!=0 else (abs(fv) if fv!=0 else None)
        pct=(ar/lvl*100.0) if lvl else None
        if pct is not None: pcts.append(pct)
        if ar>1e-9: nrev+=1; signs.append(1 if rev>0 else -1)
        sample.append((op,a0,fv,a1,lv,ar,pct))
    def p(xs,q):
        if not xs: return None
        xs=sorted(xs); k=(len(xs)-1)*q; f=int(k); c=min(f+1,len(xs)-1)
        return xs[f]+(xs[c]-xs[f])*(k-f)
    meanabs=st.mean(absrevs) if absrevs else 0.0
    p95=p(absrevs,0.95); p95pct=p(pcts,0.95)
    medlvl=st.median([abs(lv) for _,(_,_,_,lv) in acc.items() if lv]) if acc else None
    share_rev=(nrev/n) if n else 0.0
    posbias=(sum(1 for s in signs if s>0)/len(signs)) if signs else None
    rows.append(dict(base=base,lanes='+'.join(sorted(lanes)),nrec=nrec,
        floor_asof=floor,edge_asof=edge,n_obs_measurable=n,
        share_revised=round(share_rev,4),mean_abs_rev=meanabs,p95_abs_rev=p95,
        p95_pct_of_level=p95pct,median_level=medlvl,pos_share=posbias,
        n_obs_total=len(acc)))
    # dump up to 40 largest-revision obs per base
    for op,a0,fv,a1,lv,ar,pct in sorted(sample,key=lambda x:-x[5])[:40]:
        perobs_dump.write(f"{base},{op},{a0},{fv},{a1},{lv},{ar:.6g},{'' if pct is None else round(pct,4)}\n")
    print(f"done {base} nrec={nrec} n_measurable={n} share_rev={share_rev:.3f} p95%={p95pct}", flush=True)
perobs_dump.close()
# write main csv
import csv
cols=['base','lanes','nrec','floor_asof','edge_asof','n_obs_total','n_obs_measurable','share_revised','mean_abs_rev','p95_abs_rev','p95_pct_of_level','median_level','pos_share']
with open('research/revision_certification_v1.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k:r.get(k) for k in cols})
print("WROTE research/revision_certification_v1.csv rows=",len(rows))
