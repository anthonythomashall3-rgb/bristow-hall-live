import os,glob,csv,re,statistics as st

BASE="data_archive/additional_vintages/fred_md_official"
# ---- build vintage file list: (asofYYYYMM, path) ----
vints=[]
for p in glob.glob(f"{BASE}/extracted/fred_md_1999_2014/Historical FRED-MD Vintages Final/*.csv"):
    m=re.search(r'(\d{4})-(\d{2})\.csv$',p);  vints.append((m.group(1)+m.group(2),p)) if m else None
for p in glob.glob(f"{BASE}/extracted/fred_md_2015_2024/*.csv"):
    m=re.search(r'(\d{4})-(\d{2})\.csv$',p) or re.search(r'(\d{4})m(\d{2})\.csv$',p)
    if m: vints.append((m.group(1)+m.group(2),p))
for p in glob.glob(f"{BASE}/current/fred_md_*.csv"):
    m=re.search(r'(\d{4})-(\d{2})\.csv$',p);  vints.append((m.group(1)+m.group(2),p)) if m else None
vints=sorted(set(vints))
FLOOR=vints[0][0]; EDGE=vints[-1][0]

DATE=re.compile(r'^\s*\d{1,2}/\d{1,2}/\d{4}\s*$')
def obs_period(s):
    mm,dd,yy=s.strip().split('/'); return f"{int(yy):04d}-{int(mm):02d}"
def decimals(s):
    s=s.strip()
    return len(s.split('.')[1]) if '.' in s else 0

# acc[col][op] = [min_asof,minval,mindec, max_asof,maxval,maxdec]
acc={}
colseen={}   # col -> count of vintages containing it
nrows_total=0
for asof,path in vints:
    with open(path,newline='') as f:
        rdr=csv.reader(f)
        header=next(rdr)
        cols=header[1:]  # drop sasdate
        for c in cols: colseen[c]=colseen.get(c,0)+1
        for row in rdr:
            if not row: continue
            if not DATE.match(row[0]):    # Transform: row and any non-date row
                continue
            op=obs_period(row[0]); nrows_total+=1
            vals=row[1:]
            for ci,c in enumerate(cols):
                if ci>=len(vals): break
                raw=vals[ci].strip()
                if raw=='' : continue
                try: val=float(raw)
                except ValueError: continue
                d=decimals(raw)
                ca=acc.get(c)
                if ca is None: ca={}; acc[c]=ca
                e=ca.get(op)
                if e is None: ca[op]=[asof,val,d,asof,val,d]
                else:
                    if asof<e[0]: e[0]=asof; e[1]=val; e[2]=d
                    if asof>e[3]: e[3]=asof; e[4]=val; e[5]=d

def pctl(xs,q):
    if not xs: return None
    xs=sorted(xs); k=(len(xs)-1)*q; f=int(k); c=min(f+1,len(xs)-1)
    return xs[f]+(xs[c]-xs[f])*(k-f)

rows=[]
for col in sorted(acc):
    ca=acc[col]
    absrevs=[]; pcts=[]; signs=[]; nrev=0; n=0
    ratios=[]; net_abs=[]; net_pct=[]; net_genuine=0; net_n=0
    for op,(a0,fv,fd,a1,lv,ld) in ca.items():
        if a0==a1: continue          # single-vintage obs, unmeasurable
        n+=1
        rev=lv-fv; ar=abs(rev)
        absrevs.append(ar)
        lvl=abs(lv) if lv!=0 else (abs(fv) if fv!=0 else None)
        if lvl: pcts.append(ar/lvl*100.0)
        if ar>1e-9: nrev+=1; signs.append(1 if rev>0 else -1)
        if fv!=0: ratios.append(lv/fv)
    share=(nrev/n) if n else 0.0
    factor=st.median(ratios) if ratios else None
    ratio_iqr=(pctl(ratios,.75)-pctl(ratios,.25)) if len(ratios)>3 else None
    # rebase-net pass (CH-R21): residual after removing median ratio factor
    if factor:
        for op,(a0,fv,fd,a1,lv,ld) in ca.items():
            if a0==a1 or fv==0: continue
            net_n+=1
            resid=lv-factor*fv
            rel=(lv/fv)/factor-1.0
            q=0.5*(10**(-fd))/abs(fv)+ (0.5*(10**(-ld))/abs(lv) if lv else 0)
            net_abs.append(abs(resid))
            if lv: net_pct.append(abs(resid)/abs(lv)*100.0)
            if abs(rel)>q: net_genuine+=1
    net_share=(net_genuine/net_n) if net_n else 0.0
    rows.append(dict(
        column=col, vintages_present=colseen.get(col,0),
        n_obs_measurable=n,
        share_revised=round(share,4),
        mean_abs_rev=(st.mean(absrevs) if absrevs else 0.0),
        p95_abs_rev=pctl(absrevs,.95),
        p95_pct_of_level=pctl(pcts,.95),
        pos_share=(sum(1 for s in signs if s>0)/len(signs)) if signs else None,
        rebase_factor=factor, ratio_iqr=ratio_iqr,
        share_revised_rebasenet=round(net_share,4),
        p95_pct_rebasenet=pctl(net_pct,.95),
    ))

# ---- classification (thresholds recorded in brief) ----
def classify(r):
    if r['n_obs_measurable']==0: return 'UNMEASURABLE'
    if r['share_revised']==0.0: return 'NEVER_REVISED'
    reb = (r['rebase_factor'] is not None and abs(r['rebase_factor']-1.0)>0.005
           and r['ratio_iqr'] is not None and r['ratio_iqr']<0.02)
    if r['share_revised']<0.05 and (r['p95_pct_of_level'] or 0)<0.10:
        return 'NEGLIGIBLE'
    if reb and r['share_revised']>0.5 and r['share_revised_rebasenet']<0.20:
        return 'LARGE_BUT_REBASING'
    if r['share_revised_rebasenet']>=0.20 or (r['p95_pct_of_level'] or 0)>=0.10:
        return 'GENUINELY_REVISED'
    return 'MINOR_REVISED'
for r in rows: r['class']=classify(r)

cols=['column','class','vintages_present','n_obs_measurable','share_revised',
      'mean_abs_rev','p95_abs_rev','p95_pct_of_level','pos_share','rebase_factor',
      'ratio_iqr','share_revised_rebasenet','p95_pct_rebasenet']
with open('research/revision_certification_v3_fredmd_panel.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in sorted(rows,key=lambda x:x['column']): w.writerow({k:r.get(k) for k in cols})

from collections import Counter
cc=Counter(r['class'] for r in rows)
print("VINTS",len(vints),"FLOOR",FLOOR,"EDGE",EDGE,"COLS",len(rows),"ROWS_READ",nrows_total)
print("CLASSCOUNTS",dict(cc))
print("WROTE research/revision_certification_v3_fredmd_panel.csv")
