import sys,glob,re,json,statistics as st
sys.path.insert(0,'research'); from ch_r20_stream import stream_records

# The four CH-R20 LARGE_BUT_REBASING bases + their (floor_asof,edge_asof) from
# research/revision_cert_r20/revision_certification_v1.csv (earliest/latest vintage).
TARGETS={
 'INDPRO':  ('20000101','20260717'),
 'CMRMTSPL':('20130620','20260730'),
 'GDPC1':   ('20200101','20260730'),
 'W875RX1': ('20100620','20260730'),
}
bases=json.load(open('research/CH-R20_base_files.json'))
def fullpath(sha): return glob.glob(f'live_data/store/normalized/sha256/{sha[:2]}/{sha}*.json')[0]
def asofkey(sid):
    m=re.search(r'ASOF(\d{8})$',sid); return m.group(1) if m else None
def decimals(s):
    # count decimal places in the reported value string (quantization width)
    if '.' in s: return len(s.split('.')[1].rstrip())
    return 0

def pctl(xs,q):
    if not xs: return None
    xs=sorted(xs); k=(len(xs)-1)*q; f=int(k); c=min(f+1,len(xs)-1)
    return xs[f]+(xs[c]-xs[f])*(k-f)

rows=[]
log=open('research/CH-R21_part1.log','w')
for base,(fl,ed) in TARGETS.items():
    early={}; late={}   # op -> (val, decimals)
    for src,sha,sz in bases[base]:
        fp=fullpath(sha)
        for r in stream_records(fp):
            ak=asofkey(r['series_id'])
            if ak!=fl and ak!=ed: continue
            v=r.get('value')
            try: val=float(v)
            except (TypeError,ValueError): continue
            op=r['observation_period']; d=decimals(str(v))
            if ak==fl: early[op]=(val,d)
            else:      late[op]=(val,d)
    ov=sorted(set(early)&set(late))
    # rebase factor = median ratio over deep overlap window (skip zeros)
    ratios=[]; pairs=[]
    for op in ov:
        ev,ed_=early[op]; lv,ld=late[op]
        if ev==0: continue
        ratios.append(lv/ev); pairs.append((op,ev,ed_,lv,ld))
    factor=st.median(ratios) if ratios else None
    ratio_iqr=(pctl(ratios,.75)-pctl(ratios,.25)) if len(ratios)>3 else None
    # rebase-net residuals
    abs_resid=[]; pct_resid=[]; genuine=0; measn=0; worst=[]
    for op,ev,ed_,lv,ld in pairs:
        measn+=1
        resid=lv-factor*ev                      # absolute genuine revision, rebase removed
        rel=(lv/ev)/factor-1.0                   # fractional genuine revision
        # per-obs quantization floor: half-ULP propagated into the ratio
        q=0.5*(10**(-ed_))/abs(ev) + 0.5*(10**(-ld))/abs(lv) if lv else None
        abs_resid.append(abs(resid))
        if lv: pct_resid.append(abs(resid)/abs(lv)*100.0)
        if q is not None and abs(rel)>q: genuine+=1
        worst.append((op,ev,lv,resid,rel,q))
    share=genuine/measn if measn else 0.0
    mean_abs=st.mean(abs_resid) if abs_resid else 0.0
    p95_abs=pctl(abs_resid,.95); p95_pct=pctl(pct_resid,.95)
    # compare vs CH-R20 gross share_revised to show how much was rebasing
    rows.append(dict(base=base,floor_asof=fl,edge_asof=ed,n_overlap=len(ov),
        n_measurable=measn,rebase_factor=factor,ratio_iqr=ratio_iqr,
        share_revised_rebasenet=round(share,4),mean_abs_resid=mean_abs,
        p95_abs_resid=p95_abs,p95_pct_of_level=p95_pct))
    log.write(f"=== {base} factor={factor} iqr={ratio_iqr} overlap={len(ov)} share_net={share:.4f}\n")
    for op,ev,lv,resid,rel,q in sorted(worst,key=lambda x:-abs(x[4]))[:12]:
        log.write(f"  {op} early={ev} late={lv} resid={resid:.6g} rel={rel:.3e} qfloor={q:.3e}\n")
    print(f"done {base} factor={factor:.6g} share_net={share:.4f} p95%={p95_pct}",flush=True)
log.close()
import csv
cols=['base','floor_asof','edge_asof','n_overlap','n_measurable','rebase_factor',
      'ratio_iqr','share_revised_rebasenet','mean_abs_resid','p95_abs_resid','p95_pct_of_level']
with open('research/revision_certification_v1_rebasenet.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k:r.get(k) for k in cols})
print("WROTE research/revision_certification_v1_rebasenet.csv rows=",len(rows))
