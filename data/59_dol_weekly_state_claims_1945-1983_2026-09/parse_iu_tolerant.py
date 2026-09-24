"""Second field from the weekly releases: STATE INSURED UNEMPLOYMENT (continued weeks claimed in the week, State UI programs),
1945-1983, tolerant reader with the same cross-week reconciliation as the initial-claims reader (5 Sep 2026, night).
Anchor in the 1955-83 layouts: the insured-unemployment rate (%) is printed immediately after the insured-unemployment number,
so IU is the first token at position >= 3 that is at least 1.5x the initial-claims token and is followed by a rate-like token
(0 < x <= 25); the change from the previous week follows the rate (1957 on).  1946-51 (E1946): continued claims are the FIRST
verified triple (w1, w2, change); 1951-52 (E1951): the THIRD verified triple (insured unemployment, two weeks, change);
1952-54 (E1953): weeks of unemployment claimed, State programs = position 8 of 10 (total - State = veteran verifies).
Output: iu_tolerant_<label>.csv with week, state, iu, chg, era, page.  Uses parse_ic_tolerant2's page machinery."""
import sys, os, re, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_ic_tolerant2 as T2
from parse_ic_tolerant import state_of, NUM2, numval
def iu_from_vals(lay, vals):
    if not vals: return None
    if lay in ('E1955',):
        ic=vals[0]
        def ratelike(x): return 0<x<=25 and (x!=int(x) or x<10)
        for j in range(3,min(len(vals)-1,8)):
            if vals[j]<1.5*max(ic,1): continue
            if ratelike(vals[j+1]):                                   # 1957-83: number, rate, change from last week, change from a year ago (1958 on)
                chg=vals[j+2] if len(vals)>j+2 and abs(vals[j+2])<=max(2*vals[j],500) else None
                chy=vals[j+3] if (chg is not None and len(vals)>j+3 and abs(vals[j+3])<=max(3*vals[j],500)) else None
                return ('d1',vals[j],chg,None,chy)
            if len(vals)>j+2 and ratelike(vals[j+2]) and abs(vals[j+1])<=max(2*vals[j],500):   # 1954-56: number, change, rate
                return ('d1',vals[j],vals[j+1])
        return None
    tr=T2.triples(vals)
    if lay=='E1946':
        if tr: i,a,b,c=tr[0]; return ('d1',a,None,('d2',b))
    if lay=='E1951':
        if len(tr)>=3: i,a,b,c=tr[2]; return ('d1',a,None,('d2',b))
        if len(tr)==2: i,a,b,c=tr[1]; return ('d1',a,None,('d2',b))     # weeks claimed as the proxy when the third triple is lost
    if lay=='E1953':
        if len(vals)>=10 and abs(vals[5]-vals[7]-vals[9])<=2: return ('d1',vals[7],vals[8])
        if len(vals)>=8: return ('d1',vals[7],vals[8] if len(vals)>8 else None)
    return None
def page_rows(path, carry=None):
    txt=open(path,errors='ignore').read(); ds=T2.dates_on(txt); lay=T2.layout_of(txt)
    if lay=='E1955' and 'insured unemployment' not in txt[:900].lower().replace('unonploy','unemploy').replace('unanploy','unemploy'): return None,[]
    if not ds:
        if carry is None: return None,[]
        d1,lay=carry
    else:
        d1=max(ds[:2])
        if lay=='E1955' and len(ds)==1:
            m=re.search(r"insured\s+unemployment\s+for\s+w[a-z]{1,3}k\s+[ae]nded\s+",txt[:3000],re.I)
            if m: d1=ds[0]+pd.Timedelta(days=7)
    iu_week=d1-pd.Timedelta(days=7) if lay=='E1955' else d1          # 1955 on: the insured week printed is one week before the claims week
    blocks=[]; cur=None
    for ln in txt.split('\n'):
        st=state_of(ln)
        if st:
            if cur: blocks.append(cur)
            rest=ln.strip(); m=re.match(r"^[A-Za-z\.\s\)\*…]+",rest); rest=rest[m.end():] if m else rest
            cur=dict(state=st,toks=[t for t in re.split(r"\s+",rest.strip(" .:")) if NUM2.match(t)])
        elif cur is not None:
            for t in re.split(r"\s+",ln.strip()):
                if NUM2.match(t): cur['toks'].append(t)
    if cur: blocks.append(cur)
    if lay=='E1955':
        L=12; out=[]; run=[]
        for b in blocks:
            if not b['toks']: run.append(b); continue
            if run and L*(len(run)+1)-2<=len(b['toks'])<=L*(len(run)+1)+2:
                toks=b['toks']; names=run+[b]
                for i,nb in enumerate(names): out.append(dict(state=nb['state'],toks=toks[i*L:(i+1)*L] if i<len(names)-1 else toks[i*L:]))
                run=[]; continue
            out.extend(run); run=[]; out.append(b)
        out.extend(run); blocks=out
    if len(blocks)<10: return None,[]
    rows=[]
    for b in blocks:
        vals=[v for v in (numval(t) for t in b['toks']) if v is not None]
        r=iu_from_vals(lay,vals)
        if r is None: continue
        rows.append(dict(week=iu_week,state=b['state'],iu=r[1],chg=r[2],chg_yr=(r[4] if len(r)>4 else None),era=lay,page=os.path.basename(path)))
        if len(r)>3 and r[3] is not None: rows.append(dict(week=iu_week-pd.Timedelta(days=7),state=b['state'],iu=r[3][1],chg=None,era=lay,page=os.path.basename(path)))
    return d1,rows
def parse_volume(d,label,outdir='.'):
    pages=sorted(glob.glob(os.path.join(d,'0*.txt'))); dated=[]; allrows={}; carry=None; since=99
    for p in pages:
        txt=open(p,errors='ignore').read(); has=bool(T2.dates_on(txt)); since=0 if has else since+1
        d1,rows=page_rows(p, carry if (not has and since<=3 and carry and carry[1] in ('E1946','E1951','E1953')) else None)
        if has and d1 is not None: carry=(d1,T2.layout_of(txt) or (carry[1] if carry else None))
        if d1 is not None and rows: dated.append((p,d1)); allrows[p]=rows
    keep=set()
    for k,(p,d1) in enumerate(dated):
        nb=[dated[j][1] for j in (k-1,k+1) if 0<=j<len(dated)]
        if not nb or any(abs((d1-x).days)<=45 for x in nb): keep.add(p)
    df=pd.DataFrame([r for p in keep for r in allrows[p]])
    if not len(df): print(label,'nothing'); return df
    df=df[(df.iu>0)&(df.iu<3e6)]; df['volume']=label; df.to_csv(f'{outdir}/iu_tolerant_{label}.csv',index=False)
    print(f"{label}: {len(df)} IU prints, weeks {df.week.min().date()} to {df.week.max().date()}, layouts {df.era.value_counts().to_dict()}")
    return df
if __name__=='__main__': parse_volume(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
