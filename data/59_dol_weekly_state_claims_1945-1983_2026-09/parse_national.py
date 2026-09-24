"""The NATIONAL row of the weekly release, 1945-1983: weekly national initial claims and insured unemployment (State programs)
as first printed, and the insured unemployment rate where the release prints it (1955 on).  6 September 2026.

Why: the tool's national weekly objects (leg B, leg U, the low reading, closer K) run on files that begin in 1967 (ICNSA/CCNSA)
and 1971 (IURSA); the release printed the same national figures every week from 1945.  This reader takes the 'Total' row of
each table (OCR variants: 'Total', 'TOTAL', 'U.S.', 'United States', 'Tota1', 'al....'), gathers its numeric tokens until the
first state row, and reads them by the page's layout with the same arithmetic checks as the state readers:
  L11 (1946-50)  T1 T2 dT | W1 W2 | C1 C2 dC | I1 I2 dI  (verified triples; continued claims = T, initial = I)
  L9  (1950-52)  I1 I2 dI | U1 U2 dU | N1 N2 dN
  E1953 (1952-54, two tables)  Tot dTot St dSt Vet [rate]  -> State programs = St
  E1955 (1954-83) IC = first token, change second, change from a year ago third (1956 on); IU = the token before the first
        rate-like token, its changes after; 1954 pages without a rate: IU = first token above three times IC
Output: national_prints_<label>.csv  (week, field, value, chg, chg_yr, layout, page).  reconcile_national.py joins the prints."""
import sys, os, re, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ic_tolerant import state_of, NUM2, numval, ROMAN
from parse_early_verified import dates_on, layout_of as early_layout, eq, trip, read_L11, read_L9
import parse_ic_tolerant2 as T2
TOTAL=re.compile(r"^[\s\.,;:'_-]*(?:U\.?\s?S\.?\s*(?:total)?|S\.\s*total|United\s+States|Tota[l1]|TOTAL|otal|al\s*\.{3,}|Continental\s+U)\b", re.I)
def layout(txt):
    h=txt[:2500].lower().replace('clains','claims').replace('wecks','weeks').replace('unonploy','unemploy')
    if 'filed during' in h or 'insured unemployment for week' in h: return 'E1955'
    return early_layout(txt)
def ratelike(x): return 0<x<=25 and (x!=int(x) or x<10)
def read_E1955(v):
    out=[]
    if not v: return out
    ic=v[0]; chg=v[1] if len(v)>1 and abs(v[1])<=max(2*ic,5000) else None; chy=v[2] if len(v)>2 and chg is not None and abs(v[2])<=max(3*ic,5000) else None
    if ic>=20000: out.append(('ic',ic,chg,chy))
    # insured unemployment: token before the first rate-like token that is at least twice IC
    for j in range(2,len(v)-1):
        if v[j]>=2*ic and ratelike(v[j+1]):
            iu=v[j]; rate=v[j+1]; c=v[j+2] if len(v)>j+2 and abs(v[j+2])<=max(iu,2e6) else None; cy=v[j+3] if len(v)>j+3 and c is not None and abs(v[j+3])<=2e6 else None
            out.append(('iu',iu,c,cy)); out.append(('iur',rate,None,None)); return out
    big=[x for x in v[3:] if x>=3*ic]
    if big: out.append(('iu',big[0],None,None))
    return out
def read_E1953(v,field):
    for i in range(0,min(3,len(v))):
        if i+5>len(v): break
        Tot,dTot,St,dSt,Vet=v[i:i+5]
        if (eq(Tot-St,Vet,5) or (field=='iu' and 0.5*Tot<St<Tot and abs(dSt)<0.3*St)) and Tot>=St>0:
            r=[(field,St,dSt,None)]
            if field=='iu' and len(v)>i+5 and ratelike(v[i+5]): r.append(('iur',v[i+5],None,None))
            return r
    return []
def total_block(txt):
    """numeric tokens of the national row: the first 'Total'-like line that itself carries numbers (a bare column heading
    'Total' is skipped), then following lines until a state row; header day-numbers (< 100) before the first large value dropped"""
    lines=txt.split('\n'); toks=[]; found=False
    for i,ln in enumerate(lines):
        if not found:
            if TOTAL.match(ln.strip()) or re.match(r"^\s*al\.{4,}",ln):
                rest=re.sub(r"^[A-Za-z\.\s,;:'_-]+","",ln.strip()); rest=re.sub(r"(\d)([+-]\d)",r"\1 \2",rest)
                nums=[t for t in re.split(r"\s+",rest) if NUM2.match(t)]
                nxt=' '.join(lines[i+1:i+8]); nnext=[t for t in re.split(r"\s+",re.sub(r"(\d)([+-]\d)",r"\1 \2",nxt)) if NUM2.match(t)]
                if len(nums)>=2 or (nums and len(nnext)>=2) or (not nums and len(nnext)>=3 and not state_of(lines[i+1] if i+1<len(lines) else '')):
                    found=True; toks+=nums
            continue
        if state_of(ln) or (re.search(r"[A-Za-z]{4,}",ln) and not re.search(r"\d",ln)):
            if toks: break
            continue
        toks+=[t for t in re.split(r"\s+",re.sub(r"(\d)([+-]\d)",r"\1 \2",ln.strip())) if NUM2.match(t)]
        if len(toks)>=24: break
    if not found: return None
    j=[]; i=0
    while i<len(toks):
        if toks[i].endswith(',') and i+1<len(toks) and re.fullmatch(r"\d{3}",toks[i+1]): j.append(toks[i]+toks[i+1]); i+=2
        else: j.append(toks[i]); i+=1
    while j and (numval(j[0]) is None or abs(numval(j[0]))<1000): j=j[1:]
    return j
def parse_volume(d,label,outdir='.'):
    rows=[]; npages=0
    for p in sorted(glob.glob(os.path.join(d,'0*.txt'))):
        txt=open(p,errors='ignore').read(); lay=layout(txt)
        if lay is None: continue
        ds=dates_on(txt)
        if not ds: continue
        toks=total_block(txt)
        if not toks: continue
        v=[x for x in (numval(t) for t in toks) if x is not None]
        while len(v)>1 and 0<v[0]<10 and v[1]>100*v[0]: v=v[1:]
        d1=max(ds[:2]) if lay=='E1955' else ds[0]
        if lay=='E1955' and len(ds)==1: d1=ds[0]+pd.Timedelta(days=7) if re.search(r"insured\s+unemployment\s+for\s+w[a-z]{1,3}k\s+[ae]nded",txt[:3000],re.I) and 'filed during' not in txt[:3000].lower() else ds[0]
        npages+=1
        if lay=='L11':
            vals,tier=read_L11(v)
            for field,which,val in vals: rows.append(dict(week=d1 if which==1 else d1-pd.Timedelta(days=7),field=field,value=val,chg=None,chg_yr=None,tier=tier,layout=lay,page=os.path.basename(p)))
        elif lay=='L9':
            vals,tier=read_L9(v)
            for field,which,val in vals: rows.append(dict(week=d1 if which==1 else d1-pd.Timedelta(days=7),field=field,value=val,chg=None,chg_yr=None,tier=tier,layout=lay,page=os.path.basename(p)))
        elif lay in ('E1953-IC','E1953-IU'):
            for field,val,c,cy in read_E1953(v,'ic' if lay=='E1953-IC' else 'iu'): rows.append(dict(week=d1,field=field,value=val,chg=c,chg_yr=cy,tier='verified',layout=lay,page=os.path.basename(p)))
        else:
            for field,val,c,cy in read_E1955(v):
                wk=d1 if field=='ic' else d1-pd.Timedelta(days=7)
                rows.append(dict(week=wk,field=field,value=val,chg=c,chg_yr=cy,tier='positional',layout=lay,page=os.path.basename(p)))
    df=pd.DataFrame(rows)
    if not len(df): print(label,'nothing',npages); return df
    # the national State-programs row: initial claims never below 100,000 a week nor insured unemployment below 500,000 in 1945-83; smaller totals are the federal-programme tables
    df=df[~(((df.field=='ic')&(df.value<100000))|((df.field.isin(['iu','cc']))&(df.value<500000))|((df.field=='iur')&((df.value<0.5)|(df.value>15))))]
    df['volume']=label; os.makedirs(outdir,exist_ok=True); df.to_csv(f'{outdir}/national_prints_{label}.csv',index=False)
    print(f"{label}: {npages} pages, {len(df)} prints {df.field.value_counts().to_dict()}, weeks {df.week.min().date()}..{df.week.max().date()}")
    return df
if __name__=='__main__': parse_volume(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
