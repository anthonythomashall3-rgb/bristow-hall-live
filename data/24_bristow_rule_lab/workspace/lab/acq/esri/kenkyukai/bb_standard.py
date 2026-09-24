"""A faithful Bry-Boschan (1971) for monthly series, as ESRI applies it to each coincident
component, and its validation against ESRI's own per-component turning points parsed from
the committee tables (esri_hdi_components.csv).

Steps (Bry and Boschan, Table 1 of the 1971 monograph):
  1. outliers: replace values beyond 3.5 standard deviations from a Spencer curve
  2. turning points on the 12-month centred moving average (5-month neighbourhood extrema,
     alternation), cycles of at least 15 months
  3. refine on the Spencer curve within +/-5 months; cycles >= 15 months
  4. refine on the MCD (months for cyclical dominance) short-term moving average within
     +/-5 months; phases >= 5 months
  5. final: unsmoothed series within +/-4 months of step 4; phases >= 5 months, cycles >= 15
     months, no turn within 6 months of either end, alternation, and at each end the extreme
     value is not exceeded by a later (earlier) observation in the same phase.
"""
import pandas as pd, numpy as np, sys, re
SPENCER=np.array([-3,-6,-5,3,21,46,67,74,67,46,21,3,-5,-6,-3])/320.0
def spencer(x):
    v=x.values.astype(float); n=len(v); out=np.full(n,np.nan)
    for i in range(7,n-7): out[i]=np.dot(SPENCER,v[i-7:i+8])
    s=pd.Series(out,index=x.index)
    return s.bfill().ffill()
def ma_centred(x,k):
    return x.rolling(k,center=True,min_periods=max(2,k//2)).mean()
def mcd(x):
    """months for cyclical dominance: the smallest span k (1..6) for which the mean absolute
    change of the irregular over k months is below that of the trend-cycle (Spencer)"""
    tc=spencer(x); ir=x-tc
    for k in range(1,7):
        ai=(ir.diff(k).abs()).mean(); ac=(tc.diff(k).abs()).mean()
        if ai/ac<1.0: return k
    return 6
def local_extrema(v,w):
    c=[]
    for i in range(w,len(v)-w):
        seg=v[i-w:i+w+1]
        if np.isnan(seg).any(): continue
        if v[i]==seg.max() and (seg==seg.max()).sum()==1: c.append((i,'P'))
        elif v[i]==seg.min() and (seg==seg.min()).sum()==1: c.append((i,'T'))
    return c
def alternate(tp,v):
    """keep alternation: of consecutive same-kind turns keep the higher peak / lower trough"""
    out=[]
    for i,k in tp:
        if out and out[-1][1]==k:
            j=out[-1][0]
            if (k=='P' and v[i]>v[j]) or (k=='T' and v[i]<v[j]): out[-1]=(i,k)
        else: out.append((i,k))
    return out
def enforce(tp,v,min_phase=5,min_cycle=15):
    tp=alternate(tp,v); changed=True
    while changed and len(tp)>1:
        changed=False
        # cycles: peak-to-peak and trough-to-trough at least min_cycle
        for a in range(len(tp)-2):
            if tp[a+2][0]-tp[a][0]<min_cycle:
                # drop the weaker of the two same-kind turns (and the turn between them)
                i,j=tp[a][0],tp[a+2][0]; k=tp[a][1]
                keep_first=(v[i]>=v[j]) if k=='P' else (v[i]<=v[j])
                del tp[a+1]; del tp[a+1 if keep_first else a]
                changed=True; break
        if changed: continue
        for a in range(len(tp)-1):
            if tp[a+1][0]-tp[a][0]<min_phase:
                i,j=tp[a][0],tp[a+1][0]
                # remove the pair (a peak and a trough too close together = not a phase)
                del tp[a+1]; del tp[a]; changed=True; break
        tp=alternate(tp,v)
    return tp
def refine(tp_prev,v,window,min_phase,min_cycle):
    out=[]
    for i,k in tp_prev:
        lo=max(0,i-window); hi=min(len(v)-1,i+window)
        seg=v[lo:hi+1]
        if np.isnan(seg).all(): continue
        j=lo+(np.nanargmax(seg) if k=='P' else np.nanargmin(seg))
        out.append((j,k))
    return enforce(out,v,min_phase,min_cycle)
OUTLIER_SD=None   # None = no outlier replacement (a three-month collapse is a phase, not an irregular)
def bry_boschan_std(x, end_guard=6):
    x=x.dropna().astype(float)
    # 1. outliers vs Spencer (off by default)
    tc=spencer(x); ir=x-tc; sd=ir.std()
    xc=x.where((ir.abs()<=OUTLIER_SD*sd), tc) if OUTLIER_SD else x.copy()
    # 2. 12-month MA
    m12=ma_centred(xc,12); v12=m12.values
    tp=enforce(local_extrema(v12,5),v12,5,15)
    # 3. Spencer
    sp=spencer(xc).values
    tp=refine(tp,sp,5,5,15)
    # 4. MCD moving average
    k=mcd(xc); mk=ma_centred(xc,k).values if k>1 else xc.values
    tp=refine(tp,mk,5,5,15)
    # 5. unsmoothed
    v=xc.values
    tp=refine(tp,v,4,5,15)
    # end guards
    n=len(v); tp=[(i,kk) for i,kk in tp if end_guard<=i<n-end_guard]
    # the extreme must not be exceeded by a later observation before the next turn (peaks) etc.
    tp=enforce(tp,v,5,15)
    return [(x.index[i],kk) for i,kk in tp], k
if __name__=='__main__':
    sys.path.insert(0,'/home/claude'); import bristow_rule_v3 as B
    E=pd.read_csv('esri_hdi_components.csv',parse_dates=['month'])
    E['file_order']=E.file.str.extract(r'^(\d+)')[0].str[:6].astype(int)
    E=E.sort_values(['name','month','file_order']).drop_duplicates(['name','month'],keep='last')
    NAME_MAP={'生産指数(鉱工業)':'industrial_production','鉱工業用生産財出荷指数':'producer_goods_shipments',
              '耐久消費財出荷指数':'durable_consumer_goods_shipments','労働投入量指数(調査産業計)':'labor_input',
              '投資財出荷指数(除輸送機械)':'investment_goods_shipments','商業販売額(小売業)(前年同月比)':'retail_sales_yoy',
              '商業販売額(卸売業)(前年同月比)':'wholesale_sales_yoy','営業利益(全産業)':'operating_profits',
              '有効求人倍率(除学卒)':'effective_job_offer_rate','輸出数量指数':'exports_volume'}
    def esri_tp(sig):
        out=[]; s=sig.sort_index()
        for a,b in zip(s.index[:-1],s.index[1:]):
            if s[a]=='+' and s[b]=='-': out.append((a,'P'))
            if s[a]=='-' and s[b]=='+': out.append((a,'T'))
        return out
    def match(ref,cand,tol):
        """share of reference turning points with a candidate of the same kind within tol months"""
        hit=0
        for d,k in ref:
            if any(kk==k and abs((dd.year-d.year)*12+dd.month-d.month)<=tol for dd,kk in cand): hit+=1
        return hit
    TOT={'tool':[0,0,0],'std':[0,0,0]}; NREF=0; extra={'tool':0,'std':0}
    for nm,f in NAME_MAP.items():
        sub=E[E.name==nm]
        if sub.empty: continue
        sig=sub.set_index('month').sign; ref=esri_tp(sig)
        lo,hi=sig.index.min(),sig.index.max()
        s=pd.read_csv(f'/home/claude/lab/esri/JPN_{f}.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
        tool=[(d,k) for d,k in B.bry_boschan(s,3) if lo<=d<=hi]
        std_tp,mcdk=bry_boschan_std(s); std=[(d,k) for d,k in std_tp if lo<=d<=hi]
        NREF+=len(ref)
        for lab,c in (('tool',tool),('std',std)):
            for t in range(3): TOT[lab][t]+=match(ref,c,t)
            extra[lab]+=max(0,len(c)-len(ref))
        f_=lambda L:[(d.strftime('%y-%m'),k) for d,k in L]
        print(f'== {nm} ({f}), MCD {mcdk}\n   ESRI {f_(ref)}\n   tool {f_(tool)}\n   std  {f_(std)}')
    print(f'\nESRI turning points {NREF}: matched within 0/1/2 months — tool {TOT["tool"]}, standard BB {TOT["std"]}; extra turns beyond ESRI\'s count: tool {extra["tool"]}, std {extra["std"]}')
