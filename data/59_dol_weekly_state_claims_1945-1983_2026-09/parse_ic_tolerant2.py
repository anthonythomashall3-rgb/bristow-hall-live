"""Second pass of the tolerant reader for the 1945-54 volumes (5 Sep 2026, "clear all coverage floors").
Adds: (1) a heading-free date finder - the first 'Month day, year' on a page that carries a state table is the
initial-claims week in every layout (the second date is the compared or insured week); OCR year slips repaired when the two
dates are not 5-21 days apart; (2) layout by keywords, not by exact heading: 'compared with'/'claims data' -> E1946
(eleven fields, initial claims = the LAST verified triple a-b=c); 'weeks of unemployment' -> E1951 (initial claims = the
FIRST verified triple); 'filed under'/'veteran' -> E1953 (ic_total first, ic_state third); 'filed during' -> E1955 (first
token); (3) a per-volume date-sequence check: a page whose date is more than 45 days from both dated neighbours is dropped.
Output: ic_tolerant2_<label>.csv (same columns as the first pass) so reconcile_ic.py can take both."""
import sys, os, re, glob, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ic_tolerant import state_of, NUM2, numval
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
DATE=re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(\d{1,2})\s*,?\s*(19[3-8]\d)\b", re.I)
def dates_on(txt):
    out=[]
    for m in DATE.finditer(txt[:3000]):
        try: out.append(pd.Timestamp(int(m.group(3)),MONTHS[m.group(1)[:3].lower()],int(m.group(2))))
        except Exception: pass
    return out
def layout_of(txt):
    h=txt[:1500].lower().replace('clains','claims').replace('cla ims','claims')
    if 'compared with' in h or 'claims data' in h: return 'E1946'
    if 'filed under' in h or ('veteran' in h and 'filed during' not in h and 'insured unemployment under' not in h): return 'E1953'
    if 'weeks of unemployment' in h or 'weeks claimed' in h: return 'E1951'
    if 'filed during' in h or 'insured unemployment for week' in h: return 'E1955'
    return None
def triples(vals):
    out=[]
    for i in range(len(vals)-2):
        a,b,c=vals[i],vals[i+1],vals[i+2]
        if a>0 and b>0 and abs((a-b)-c)<=max(2,0.002*max(a,b)): out.append((i,a,b,c))
    return out
def page_rows(path, carry=None):
    txt=open(path,errors='ignore').read()
    ds=dates_on(txt)
    lay=layout_of(txt)
    if lay=='E1955' and 'initial claims' not in txt[:600].lower().replace('clains','claims'): return None,[]   # an insured-unemployment or extended-benefits table, not the initial-claims table
    if not ds:
        if carry is None: return None,[]
        d1,lay=carry                                   # a continuation page: the table runs on from the dated page before it
    else:
        d1=max(ds[:2])
        if lay=='E1955' and len(ds)==1:
            # the initial-claims date was broken by the OCR ('WEEK ENDED AUG.~PAGE 4~12, 1972'); the one date found is the insured week when it follows
            # 'insured unemployment for week ended', and the initial-claims week is always seven days later
            m=re.search(r"insured\s+unemployment\s+for\s+w[a-z]{1,3}k\s+[ae]nded\s+"+DATE.pattern.replace('\\b','',1), txt[:3000], re.I)
            if m: d1=ds[0]+pd.Timedelta(days=7)                              # the initial-claims week is the LATER of the two week-endings in every layout (the compared / insured week is a week or two earlier)
    if len(ds)>1:
        other=min(ds[:2]); gap=(d1-other).days
        if gap>300:                                      # a year slip on one of the two dates: make the pair 7-21 days apart
            for cand in (pd.Timestamp(other.year,d1.month,d1.day) if (d1.month,d1.day)!=(2,29) else None, pd.Timestamp(d1.year,other.month,other.day)+pd.DateOffset(years=0) if False else None):
                if cand is not None and 5<=(cand-other).days<=21: d1=cand; break
            else:
                try:
                    c2=pd.Timestamp(d1.year,other.month,other.day)
                    if 5<=(d1-c2).days<=21: pass                 # the earlier date carried the slip; d1 stands
                    else: d1=None
                except Exception: d1=None
            if d1 is None: return None,[]
    blocks=[]; cur=None
    for ln in txt.split('\n'):
        st=state_of(ln)
        if st:
            if cur: blocks.append(cur)
            rest=ln.strip()
            m=re.match(r"^[A-Za-z\.\s\)\*…]+",rest); rest=rest[m.end():] if m else rest
            cur=dict(state=st,toks=[t for t in re.split(r"\s+",rest.strip(" .:")) if NUM2.match(t)])
        elif cur is not None:
            for t in re.split(r"\s+",ln.strip()):
                if NUM2.match(t): cur['toks'].append(t)
    if cur: blocks.append(cur)
    if lay=='E1955':                                      # 1973-83 pages list several names first and their rows after (see parse_ic_tolerant.page_blocks)
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
        if not vals: continue
        if lay=='E1946':
            tr=triples(vals)
            if tr: i,a,bb,c=tr[-1]; rows.append((d1,b['state'],a,None,lay)); rows.append((d1-pd.Timedelta(days=7),b['state'],bb,None,lay))
        elif lay=='E1951':
            tr=triples(vals)
            if tr: i,a,bb,c=tr[0]; rows.append((d1,b['state'],a,None,lay)); rows.append((d1-pd.Timedelta(days=7),b['state'],bb,None,lay))
        elif lay=='E1953':                                  # total, change, State, change, veteran: total - State = veteran verifies the row
            if len(vals)>=5 and abs(vals[0]-vals[2]-vals[4])<=2: rows.append((d1,b['state'],vals[2],vals[3],lay))
            elif len(vals)>=4: rows.append((d1,b['state'],vals[2],vals[3],lay))
            elif len(vals)>=2: rows.append((d1,b['state'],vals[0],vals[1],lay))
        elif lay=='E1955':
            chg=vals[1] if len(vals)>1 and abs(vals[1])<=max(2*vals[0],500) else None
            rows.append((d1,b['state'],vals[0],chg,lay))
        elif d1.year<=1954:
            tr=triples(vals)                               # unknown heading (1945-54 only, where headings are unreliable): accept only a verified triple
            if tr: i,a,bb,c=tr[0]; rows.append((d1,b['state'],a,None,'triple'))
    return d1,[dict(week=w,state=s,ic=ic,chg=chg,era=lay or 'unknown',page=os.path.basename(path)) for w,s,ic,chg,lay in rows]
def parse_volume(d,label,outdir='.'):
    pages=sorted(glob.glob(os.path.join(d,'0*.txt'))); dated=[]; allrows={}
    carry=None; since=99
    for p in pages:
        txt=open(p,errors='ignore').read()
        has_date=bool(dates_on(txt)); since=0 if has_date else since+1
        d1,rows=page_rows(p, carry if (not has_date and since<=3 and carry and carry[1] in ('E1946','E1951','E1953')) else None)   # continuation pages only in the early layouts; a 1955+ page must carry its own 'initial claims' heading
        if has_date and d1 is not None: carry=(d1,layout_of(txt) or (carry[1] if carry else None))
        if d1 is not None and rows: dated.append((p,d1)); allrows[p]=rows
    # date-sequence check
    keep=set()
    for k,(p,d1) in enumerate(dated):
        nb=[dated[j][1] for j in (k-1,k+1) if 0<=j<len(dated)]
        if not nb or any(abs((d1-x).days)<=45 for x in nb): keep.add(p)
    rows=[r for p in keep for r in allrows[p]]
    df=pd.DataFrame(rows)
    if not len(df): print(label,'nothing'); return df
    df=df[(df.ic>0)&(df.ic<400000)]; df['volume']=label; df['raw']=''
    df.to_csv(f'{outdir}/ic_tolerant2_{label}.csv',index=False)
    print(f"{label}: pages dated {len(dated)}, kept {len(keep)}, {len(df)} prints, weeks {df.week.min().date()} to {df.week.max().date()}, layouts {df.era.value_counts().to_dict()}")
    return df
if __name__=='__main__':
    parse_volume(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
