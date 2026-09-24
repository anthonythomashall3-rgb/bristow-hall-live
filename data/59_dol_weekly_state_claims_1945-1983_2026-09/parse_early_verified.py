"""Verified reader for the weekly release's EARLY layouts (1945-1954), both fields, 5 September 2026.

The two earlier readers took values by POSITION (token 9 of eleven; the first token) and so read the wrong
column whenever the OCR dropped or added a token, or a heading keyword put a page in the wrong layout: the
November 1949 pages say 'weeks of unemployment claimed' like the 1951 pages but carry the 1946 column order
(initial claims LAST), and were read as initial claims = total continued claims.  Against the Fieldhouse field
the 1947-50 initial-claims cells were wrong by more than 0.3 log points 30-70 per cent of the time.

This reader identifies columns by the table's OWN arithmetic, never by position alone:
  L11 (1946-06 .. 1950-06; headings 'Continued claims' or 'Weeks of unemployment claimed', with 'Waiting-period'):
      T1 T2 dT | W1 W2 | C1 C2 dC | I1 I2 dI   with  T1=W1+C1, T2=W2+C2, |T1-T2|=|dT|, |C1-C2|=|dC|, |I1-I2|=|dI|
      initial claims = I1 (week 1), I2 (week 2); continued claims (weeks claimed) = T1, T2
  L9  (1950-08 .. 1952-10; 'Insured unemployment' and 'Weeks of unemployment claimed', no 'Waiting-period'):
      I1 I2 dI | U1 U2 dU | N1 N2 dN   initial claims = I1, I2; weeks claimed = U1, U2 (insured unemployment N is
      the same series two weeks earlier: U2 == N1 on a clean row)
  E1953 (1952-10 .. 1954-03; two tables, 'filed under State and veteran programs' and 'Insured unemployment under'):
      Tot dTot St dSt Vet [rate]   with  Tot - St = Vet;  state programs = St
Every accepted value carries a tier: 'verified' (all identities hold), 'partial' (the field's own triple holds
and one neighbouring identity holds).  Rows whose arithmetic fails are dropped, not guessed.  Sign loss in the
OCR ('219' for '-219') is allowed for: identities are checked on absolute values.
Output: early_verified_<label>.csv with columns week,state,field,value,tier,layout,page,raw.
"""
import sys, os, re, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ic_tolerant import state_of, NUM2, numval, ROMAN
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
DATE=re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{1,2})\s*[,.]?\s*(19[3-8]\d)\b", re.I)
def dates_on(txt):
    out=[]
    for m in DATE.finditer(txt[:2500]):
        try: out.append(pd.Timestamp(int(m.group(3)),MONTHS[m.group(1)[:3].lower()],int(m.group(2))))
        except Exception: pass
    return out
def layout_of(txt):
    h=txt[:2000].lower().replace('clains','claims').replace('cla ims','claims').replace('wecks','weeks').replace('wocks','weeks')
    if 'filed during' in h: return None                       # 1954 on: the positional readers are right for that layout
    if 'waiting' in h and ('initial claims' in h or 'initial' in h): return 'L11'
    if 'filed under' in h and 'initial' in h: return 'E1953-IC'
    if 'insured unemployment under' in h and 'veteran' in h: return 'E1953-IU'
    if 'weeks of unemployment' in h or 'weeks claimed' in h: return 'L9'
    if 'compared with' in h or 'claims data' in h: return 'L11'
    return None
def eq(a,b,tol=1): return abs(abs(a)-abs(b))<=tol
def trip(v,i):
    """|v[i]-v[i+1]| == |v[i+2]| : the table's own change column"""
    return i+2<len(v) and eq(v[i]-v[i+1],v[i+2])
def read_L11(v):
    for i in range(0,min(4,len(v))):
        if i+11>len(v): break
        T1,T2,dT,W1,W2,C1,C2,dC,I1,I2,dI=v[i:i+11]
        ok=[trip(v,i), eq(T1,W1+C1,2), eq(T2,W2+C2,2), trip(v,i+5), trip(v,i+8)]
        if ok[4] and sum(ok)>=4 and I1<T1: return [('ic',1,I1),('ic',2,I2),('cc',1,T1),('cc',2,T2)],'verified'
    # partial: a verified C-triple immediately followed by a verified I-triple, larger before smaller
    for i in range(0,len(v)-5):
        if trip(v,i) and trip(v,i+3) and v[i]>v[i+3]>0 and v[i+1]>v[i+4]>0:
            return [('ic',1,v[i+3]),('ic',2,v[i+4])],'partial'
    return [],None
def read_L9(v):
    if len(v)>=6 and trip(v,0) and trip(v,3) and v[3]>v[0]>0:
        out=[('ic',1,v[0]),('ic',2,v[1]),('cc',1,v[3]),('cc',2,v[4])]
        return out,('verified' if (len(v)<9 or trip(v,6)) else 'partial')
    if len(v)>=3 and trip(v,0) and v[0]>0:
        return [('ic',1,v[0]),('ic',2,v[1])],'partial'
    return [],None
def read_E1953(v,field):
    for i in range(0,min(3,len(v))):
        if i+5>len(v): break
        Tot,dTot,St,dSt,Vet=v[i:i+5]
        if eq(Tot-St,Vet) and Tot>=St>0: return [(field,1,St)],'verified'
    if len(v)>=3 and v[0]>=v[2]>0 and abs(v[1])<v[0]: return [(field,1,v[2])],'partial'
    return [],None
def blocks_of(txt):
    """state blocks: a line opening with a state name starts a block; numeric tokens until the next name"""
    blocks=[]; cur=None
    for ln in txt.split('\n'):
        st=state_of(ln)
        if st:
            if cur: blocks.append(cur)
            rest=ROMAN.sub('',ln.strip())
            m=re.match(r"^[A-Za-z\.\s]{2,26}?[\.\s…:]*(?=[\d+\-]|$)",rest)
            rest=rest[m.end():] if m else rest
            cur=dict(state=st,toks=[t for t in re.split(r"\s+",rest.strip()) if NUM2.match(t)])
        elif cur is not None:
            for t in re.split(r"\s+",ln.strip()):
                if NUM2.match(t): cur['toks'].append(t)
    if cur: blocks.append(cur)
    return blocks
def parse_volume(d,label,outdir='.'):
    rows=[]; npages=0
    for p in sorted(glob.glob(os.path.join(d,'*.txt'))):
        txt=open(p,errors='ignore').read(); lay=layout_of(txt)
        if lay is None: continue
        ds=dates_on(txt)
        if not ds: continue
        w1=ds[0]; w2=w1-pd.Timedelta(days=7)      # every early heading names the current week first
        if lay=='E1953-IU': w1=ds[0]; w2=None
        npages+=1
        for b in blocks_of(txt):
            v=[numval(t) for t in b['toks']]; v=[x for x in v if x is not None]
            # drop footnote marks read as numbers ('2/' -> 2) at the head of a row: a leading value below 10 followed by a value 100x larger
            while len(v)>1 and 0<v[0]<10 and v[1]>100*v[0]: v=v[1:]
            if lay=='L11': vals,tier=read_L11(v)
            elif lay=='L9': vals,tier=read_L9(v)
            elif lay=='E1953-IC': vals,tier=read_E1953(v,'ic')
            else: vals,tier=read_E1953(v,'cc')
            for field,which,val in vals:
                wk=w1 if which==1 else w2
                if wk is None or val<=0: continue
                rows.append(dict(week=wk,state=b['state'],field=field,value=val,tier=tier,layout=lay,page=os.path.basename(p),raw='|'.join(b['toks'])))
    df=pd.DataFrame(rows)
    if not len(df): print(label,'nothing',npages,'pages'); return df
    df['volume']=label
    os.makedirs(outdir,exist_ok=True); df.to_csv(f'{outdir}/early_verified_{label}.csv',index=False)
    print(f"{label}: {npages} pages, {len(df)} prints ({(df.tier=='verified').mean()*100:.0f}% verified), weeks {df.week.min().date()}..{df.week.max().date()}, layouts {df.layout.value_counts().to_dict()}")
    return df
if __name__=='__main__':
    parse_volume(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
