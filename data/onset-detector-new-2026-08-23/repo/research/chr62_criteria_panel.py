#!/usr/bin/env python3
"""CH-R62 — FACTOR-COUNT CRITERIA PANEL (read-only, §20-class). Zero store writes.
Six estimators (Bai-Ng PC_p1/PC_p2/IC_p1/IC_p2, Onatski ED, Ahn-Horenstein ER/GR)
+ CH3-R2's Horn & Kaiser as controls, on the 121-base full universe and 18-base
instrumentable universe. kmax sensitivity. FRED-MD reproduction of McCracken-Ng's 8.
numpy only."""
import os, json, glob, bisect, re, csv, datetime as dt
import numpy as np
np.random.seed(20260806)

REPO="/Users/anthonyhall/Desktop/RecessionMonitor 2/Recession Monitor V2"
NORM=REPO+"/live_data/store/normalized"
enum=json.load(open(REPO+"/research/ch3_bases_enum.json"))
VINT_BASES=set(enum["vint_bases"]); CR_BASES=set(enum["cr_bases"])
VINT_ONLY=VINT_BASES-CR_BASES

# ---------- rebuild CH3-R2 transformed matrix X (T x N) exactly ----------
WIN_START=dt.date(2000,1,1); WIN_END=dt.date(2024,12,1)
months=[]; y,mo=WIN_START.year,WIN_START.month
while dt.date(y,mo,1)<=WIN_END:
    months.append(dt.date(y,mo,1)); mo+=1
    if mo>12: mo=1; y+=1
MONTH_ORD=[d.toordinal() for d in months]; NM=len(months)
def parse_period(s):
    try:
        if "Q" in s: yy,q=s.split("-Q"); return dt.date(int(yy),(int(q)-1)*3+1,1).toordinal()
        p=s.split("-")
        if len(p)==1: return dt.date(int(p[0]),1,1).toordinal()
        if len(p)==2: return dt.date(int(p[0]),int(p[1]),1).toordinal()
        return dt.date(int(p[0]),int(p[1]),int(p[2])).toordinal()
    except: return None
def month_end(pairs):
    pairs=sorted(set(pairs)); ks=[p[0] for p in pairs]; vv=[p[1] for p in pairs]
    out=np.full(NM,np.nan)
    for i,mo_ in enumerate(MONTH_ORD):
        j=bisect.bisect_right(ks,mo_)-1
        if j>=0: out[i]=vv[j]
    return out
def vintage_key(sid):
    m=re.search(r'(?:ASOF|DEEPASOF)(\d{6,8})', sid); return m.group(1) if m else ""
cr_obs={}; cr_series_base={}; vo_obs={}
files=sorted(glob.glob(NORM+"/sha256/*/*.json"))
for f in files:
    try: d=json.load(open(f))
    except: continue
    for r in d.get("records",[]):
        sid=r.get("series_id")
        if not sid: continue
        base=sid.split(".")[0]; m=r.get("information_set_mode")
        op=r.get("observation_period"); v=r.get("value")
        if op is None or v in (None,"","."): continue
        o=parse_period(op)
        if o is None: continue
        try: fv=float(v)
        except: continue
        if m=="current_revised":
            cr_obs.setdefault(sid,[]).append((o,fv)); cr_series_base[sid]=base
        elif m=="archive_snapshot_asof" and base in VINT_ONLY:
            vo_obs.setdefault(sid,[]).append((o,fv))
vo_rep={}
for sid in vo_obs:
    base=sid.split(".")[0]; vk=vintage_key(sid); cur=vo_rep.get(base)
    if cur is None or vk>cur[1]: vo_rep[base]=(sid,vk)
by_base_cr={}
for sid,base in cr_series_base.items(): by_base_cr.setdefault(base,[]).append(sid)
rep={}
for base,sids in by_base_cr.items():
    best=max(sids,key=lambda s:len(cr_obs[s])); rep[base]=(best,"current_revised",cr_obs[best])
for base,(sid,vk) in vo_rep.items(): rep[base]=(sid,"latest_vintage_proxy",vo_obs[sid])
ADF5=-2.86
def adf_stat(yv):
    yv=np.asarray(yv,float); n=len(yv)
    if n<24: return None
    dy=np.diff(yv); p=min(4,n//4); T=n-1-p
    if T<12: return None
    yl=yv[p:n-1]; X=[np.ones(T),yl]
    for i in range(1,p+1): X.append(dy[p-i:n-1-i])
    X=np.column_stack(X); Y=dy[p:]
    try:
        beta,*_=np.linalg.lstsq(X,Y,rcond=None); resid=Y-X@beta; s2=resid@resid/(T-X.shape[1])
        se=np.sqrt(s2*np.linalg.pinv(X.T@X)[1,1]); return beta[1]/se if se>0 else None
    except: return None
def yoy12(col):
    out=np.full(NM,np.nan)
    for i in range(12,NM):
        if not np.isnan(col[i]) and not np.isnan(col[i-12]) and col[i-12]!=0:
            out[i]=(col[i]/col[i-12]-1)*100
    return out
kept=[]; cols=[]
for base in sorted(rep):
    sid,mode,obs=rep[base]; col=month_end(obs)
    if np.isnan(col[12:]).any(): continue
    st=adf_stat(col[12:])
    if st is not None and st<ADF5: use=col[12:]
    else:
        yy=yoy12(col)
        if np.isnan(yy[12:]).any() or np.nanstd(yy[12:])==0: continue
        use=yy[12:]
    if np.nanstd(use)==0: continue
    kept.append(base); cols.append(use)
X=np.column_stack(cols); n_obs,n_ser=X.shape

# ---------- estimator implementations ----------
def corr_eigs(Xmat):
    """eigenvalues of the correlation matrix (sum = N)."""
    Xs=(Xmat-Xmat.mean(0))/Xmat.std(0); T=Xs.shape[0]
    G=Xs.T@Xs/T
    ev=np.linalg.eigvalsh(G)[::-1]; return np.clip(ev,0,None)

def horn_kaiser(Xmat,nsim=200):
    Xs=(Xmat-Xmat.mean(0))/Xmat.std(0); m,p=Xs.shape
    G=Xs@Xs.T/m; ev=np.clip(np.linalg.eigvalsh(G)[::-1],0,None)
    kaiser=int(np.sum(ev>1)); rank=min(p,m); rnd=np.zeros((nsim,rank))
    for k in range(nsim):
        R=np.random.standard_normal((m,p)); Rs=(R-R.mean(0))/R.std(0)
        e=np.linalg.eigvalsh(Rs@Rs.T/m)[::-1]; rnd[k,:min(len(e),rank)]=e[:rank]
    p95=np.percentile(rnd,95,axis=0); q=min(len(ev),len(p95))
    horn=int(np.sum((ev[:q]>p95[:q])&(ev[:q]>1e-6))); return horn,kaiser

def bai_ng(Xmat,kmax):
    """PC_p1/PC_p2/IC_p1/IC_p2. Returns dict k for each. evn sum to 1."""
    ev=corr_eigs(Xmat); N=ev.size; T=Xmat.shape[0]; evn=ev/ev.sum()
    def V(k): return float(evn[k:].sum())
    NT=N*T; g1=((N+T)/NT)*np.log(NT/(N+T)); g2=((N+T)/NT)*np.log(min(N,T))
    sig2=V(kmax); out={}
    for nm,g in (("PC_p1",g1),("PC_p2",g2)):
        vals=[V(k)+k*sig2*g for k in range(kmax+1)]; out[nm]=int(np.argmin(vals))
    for nm,g in (("IC_p1",g1),("IC_p2",g2)):
        vals=[(np.log(V(k))+k*g) if V(k)>0 else np.inf for k in range(kmax+1)]; out[nm]=int(np.argmin(vals))
    return out

def onatski_ed(ev,rmax):
    ev=np.asarray(ev,float); j=rmax+1
    rhat=0
    for _ in range(12):
        hi=j+4
        if hi>=len(ev): j=len(ev)-5; hi=j+4
        idx=np.arange(j-1,j+4)
        idx=idx[(idx>=0)&(idx<len(ev))]
        if len(idx)<3: break
        y=ev[idx]; xreg=(idx.astype(float)+1.0)**(2.0/3.0)
        A=np.column_stack([np.ones(len(idx)),xreg])
        beta=np.linalg.lstsq(A,y,rcond=None)[0]; delta=2*abs(beta[1])
        diffs=ev[:rmax]-ev[1:rmax+1]
        cand=[i+1 for i in range(rmax) if diffs[i]>=delta]
        newr=max(cand) if cand else 0
        if newr+1==j: rhat=newr; break
        rhat=newr; j=newr+1
    return int(rhat)

def ahn_horenstein(ev,kmax):
    ev=np.clip(np.asarray(ev,float),1e-12,None); N=ev.size
    ER=[ev[k-1]/ev[k] for k in range(1,kmax+1)]; kER=int(np.argmax(ER))+1
    def Vt(k): return ev[k:].sum()
    GR=[]
    for k in range(1,kmax+1):
        num=np.log(Vt(k-1)/Vt(k)); den=np.log(Vt(k)/Vt(k+1)); GR.append(num/den if den>0 else 0.0)
    kGR=int(np.argmax(GR))+1
    return kER,kGR

def full_panel(Xmat,kmax):
    ev=corr_eigs(Xmat); horn,kaiser=horn_kaiser(Xmat)
    bn=bai_ng(Xmat,kmax); ed=onatski_ed(ev,min(kmax,ev.size-6))
    er,gr=ahn_horenstein(ev,kmax)
    return {"N":int(Xmat.shape[1]),"T":int(Xmat.shape[0]),"kmax":kmax,
            "PC_p1":bn["PC_p1"],"PC_p2":bn["PC_p2"],"IC_p1":bn["IC_p1"],"IC_p2":bn["IC_p2"],
            "onatski_ED":ed,"AH_ER":er,"AH_GR":gr,"horn":horn,"kaiser":kaiser}

# ---------- run on both universes ----------
inst_idx=[i for i in range(n_ser) if kept[i] in VINT_BASES]
Xinst=X[:,inst_idx]
KMAX_DEFAULT=8
results={"full":{},"instrumentable":{}}
KMAX_GRID=[6,8,10,15,20]
for kmax in KMAX_GRID:
    if kmax<X.shape[1]-1: results["full"][kmax]=full_panel(X,kmax)
for kmax in [4,6,8,10,15,17]:
    if kmax<Xinst.shape[1]-1: results["instrumentable"][kmax]=full_panel(Xinst,kmax)

full_var=[round(float(v),4) for v in (corr_eigs(X)/corr_eigs(X).sum())[:12]]
inst_var=[round(float(v),4) for v in (corr_eigs(Xinst)/corr_eigs(Xinst).sum())[:12]]

# ---------- FRED-MD reproduction (McCracken-Ng) ----------
def mcc_transform(x,tc):
    x=np.asarray(x,float); y=np.full_like(x,np.nan)
    if tc==1: y=x.copy()
    elif tc==2: y[1:]=np.diff(x)
    elif tc==3: y[2:]=np.diff(x,2)
    elif tc==4:
        with np.errstate(invalid='ignore'): y=np.log(x)
    elif tc==5:
        with np.errstate(invalid='ignore'): y[1:]=np.diff(np.log(x))
    elif tc==6:
        with np.errstate(invalid='ignore'): y[2:]=np.diff(np.log(x),2)
    elif tc==7:
        tmp=x[1:]/x[:-1]-1.0; y[2:]=np.diff(tmp)
    return y
def remove_outliers(col):
    c=col.copy(); med=np.nanmedian(c); q75,q25=np.nanpercentile(c,75),np.nanpercentile(c,25)
    iqr=q75-q25
    if iqr>0: c[np.abs(c-med)>10*iqr]=np.nan
    return c
def load_fredmd(path):
    with open(path,newline='') as fh:
        rdr=list(csv.reader(fh))
    header=rdr[0][1:]; tline=rdr[1]
    assert tline[0].lower().startswith("transform"), tline[0]
    tcodes=[int(float(x)) for x in tline[1:]]
    data=[];
    for row in rdr[2:]:
        if not row or not re.match(r'^\s*\d{1,2}/\d{1,2}/\d{4}\s*$',row[0]): continue
        vals=[]
        for x in row[1:1+len(header)]:
            x=x.strip()
            vals.append(float(x) if x not in ("",) else np.nan)
        if len(vals)<len(header): vals+=[np.nan]*(len(header)-len(vals))
        data.append(vals)
    return header,tcodes,np.array(data,float)
def fredmd_criteria(path,kmax=8,outlier=True):
    header,tcodes,raw=load_fredmd(path)
    T0,N0=raw.shape; cols=[]
    for j in range(N0):
        c=mcc_transform(raw[:,j],tcodes[j])
        if outlier: c=remove_outliers(c)
        cols.append(c)
    M=np.column_stack(cols)
    # drop first 2 rows (max transform lag), build balanced rectangle
    M=M[2:,:]
    # drop columns with any nan in the balanced window: iteratively trim
    good_col=~np.isnan(M).any(0)
    # if too few full columns, trim leading rows until enough columns full
    if good_col.sum()<50:
        # trim rows from top until >=100 columns are complete
        for cut in range(0,M.shape[0]):
            gc=~np.isnan(M[cut:,:]).any(0)
            if gc.sum()>=100: M=M[cut:,:]; good_col=gc; break
    Mb=M[:,good_col]
    # drop any residual nan rows
    rmask=~np.isnan(Mb).any(1); Mb=Mb[rmask,:]
    bn=bai_ng(Mb,kmax); ev=corr_eigs(Mb)
    er,gr=ahn_horenstein(ev,kmax); ed=onatski_ed(ev,min(kmax,ev.size-6))
    horn,kaiser=horn_kaiser(Mb)
    evn=ev/ev.sum()
    return {"path":os.path.basename(path),"N":int(Mb.shape[1]),"T":int(Mb.shape[0]),
            "outlier_removed":outlier,"kmax":kmax,
            "PC_p1":bn["PC_p1"],"PC_p2":bn["PC_p2"],"IC_p1":bn["IC_p1"],"IC_p2":bn["IC_p2"],
            "onatski_ED":ed,"AH_ER":er,"AH_GR":gr,"horn":horn,"kaiser":kaiser,
            "var_share_top8":[round(float(v),4) for v in evn[:8]],
            "cum_var_8":round(float(evn[:8].sum()),4)}
FMD="data_archive/additional_vintages/fred_md_official"
vint_paths=[]
for pat in [f"{FMD}/current/fred_md_2026-06.csv",
            f"{FMD}/extracted/fred_md_2015_2024/FRED-MD_2024m12.csv",
            f"{FMD}/extracted/fred_md_2015_2024/FRED-MD_2020m12.csv"]:
    if os.path.exists(REPO+"/"+pat): vint_paths.append(REPO+"/"+pat)
# add a couple 1999_2014 historical vintages if present
for p in sorted(glob.glob(REPO+f"/{FMD}/extracted/fred_md_1999_2014/*/*.csv"))[-2:]:
    vint_paths.append(p)
fredmd_results=[]
for p in vint_paths:
    try:
        fredmd_results.append(fredmd_criteria(p,kmax=8,outlier=True))
        fredmd_results.append(fredmd_criteria(p,kmax=8,outlier=False))
    except Exception as e:
        fredmd_results.append({"path":os.path.basename(p),"error":str(e)})

# ---------- assemble output ----------
control_ok = (results["full"].get(8,{}).get("horn")==11 and results["full"].get(8,{}).get("kaiser")==18
              and results["instrumentable"].get(8,{}).get("horn")==2 and results["instrumentable"].get(8,{}).get("kaiser")==3)

OUT={"CH_R62_factor_criteria_panel":{
  "universes":{
    "full":{"N":int(X.shape[1]),"T":int(X.shape[0]),"var_share_top12":full_var},
    "instrumentable":{"N":int(Xinst.shape[1]),"T":int(Xinst.shape[0]),"bases":[kept[i] for i in inst_idx],"var_share_top12":inst_var}},
  "panel_full":results["full"],
  "panel_instrumentable":results["instrumentable"],
  "control_reproduce_ch3r2":{
    "expected_full_horn_kaiser":[11,18],"expected_inst_horn_kaiser":[2,3],
    "got_full_horn_kaiser":[results["full"].get(8,{}).get("horn"),results["full"].get(8,{}).get("kaiser")],
    "got_inst_horn_kaiser":[results["instrumentable"].get(8,{}).get("horn"),results["instrumentable"].get(8,{}).get("kaiser")],
    "PASS":bool(control_ok)},
  "fredmd_reproduction":{
    "target_mccracken_ng_2016":"PC_p2=8 (9 without outlier adj), stable 8/8/8/7 across vintages",
    "results":fredmd_results},
  "NOTE":"A factor count is a property of (estimator, N, T, kmax) not of the economy. "
         "Bai-Ng depends on kmax; Onatski/AH do not. Criterion spread here mirrors Hartigan-Morley."}}
json.dump(OUT,open(REPO+"/research/factor_criteria_panel_v1.json","w"),indent=1,default=str)

# ---------- CSV: estimator x (universe,kmax) ----------
with open(REPO+"/research/factor_criteria_panel_v1.csv","w",newline="") as fh:
    w=csv.writer(fh)
    w.writerow(["universe","N","T","kmax","PC_p1","PC_p2","IC_p1","IC_p2","onatski_ED","AH_ER","AH_GR","horn","kaiser"])
    for uni in ("full","instrumentable"):
        for kmax in sorted(results[uni]):
            r=results[uni][kmax]
            w.writerow([uni,r["N"],r["T"],kmax,r["PC_p1"],r["PC_p2"],r["IC_p1"],r["IC_p2"],r["onatski_ED"],r["AH_ER"],r["AH_GR"],r["horn"],r["kaiser"]])
    for r in fredmd_results:
        if "error" in r: continue
        w.writerow(["fredmd:"+r["path"]+("|out" if r["outlier_removed"] else "|raw"),r["N"],r["T"],r["kmax"],
                    r["PC_p1"],r["PC_p2"],r["IC_p1"],r["IC_p2"],r["onatski_ED"],r["AH_ER"],r["AH_GR"],r["horn"],r["kaiser"]])

print("=== CH-R62 ===")
print("control PASS:",control_ok)
print("FULL kmax=8:",results["full"].get(8))
print("INST kmax=8:",results["instrumentable"].get(8))
print("--- FULL kmax sensitivity (PC_p2 / onatski / AH_ER / AH_GR) ---")
for k in sorted(results["full"]):
    r=results["full"][k]; print(f"  kmax={k}: PC_p1={r['PC_p1']} PC_p2={r['PC_p2']} IC_p2={r['IC_p2']} ED={r['onatski_ED']} ER={r['AH_ER']} GR={r['AH_GR']}")
print("--- INST kmax sensitivity ---")
for k in sorted(results["instrumentable"]):
    r=results["instrumentable"][k]; print(f"  kmax={k}: PC_p2={r['PC_p2']} IC_p2={r['IC_p2']} ED={r['onatski_ED']} ER={r['AH_ER']} GR={r['AH_GR']}")
print("--- FRED-MD reproduction ---")
for r in fredmd_results:
    if "error" in r: print("  ERR",r["path"],r["error"]); continue
    print(f"  {r['path']} {'out' if r['outlier_removed'] else 'raw'} N={r['N']} T={r['T']}: PC_p1={r['PC_p1']} PC_p2={r['PC_p2']} IC_p2={r['IC_p2']} ED={r['onatski_ED']} ER={r['AH_ER']} GR={r['AH_GR']} kaiser={r['kaiser']}")
