"""Wrapper on parse_ic_tolerant for the page-harvest volumes (v23, v30:28-53, v34:27-52 from babel imgsrv, 6 Sep 2026):
where the OCR dropped a state NAME the tolerant reader sees one block of 24 (or 36) tokens - two (three) rows of the
twelve-token 1971-83 layout glued together.  The table prints the jurisdictions in a fixed alphabetical order, so when
a block holds exactly k*12 tokens and the next k-1 names in that order are absent from the page, the extra rows are
given to them.  Nothing else changes; output file name and columns as parse_ic_tolerant.py."""
import sys, os, glob, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_ic_tolerant as P
ORDER=['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','District of Columbia','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming','Puerto Rico','Virgin Islands']
def split_blocks(blocks, L=12):
    have={b['state'] for b in blocks}; out=[]
    for b in blocks:
        n=len(b['toks'])
        if n in (2*L,3*L) and b['state'] in ORDER:
            k=n//L; i=ORDER.index(b['state']); nxt=ORDER[i+1:i+k]
            if len(nxt)==k-1 and not any(s in have for s in nxt):
                out.append(dict(state=b['state'],toks=b['toks'][:L]))
                for j,s in enumerate(nxt): out.append(dict(state=s,toks=b['toks'][(j+1)*L:(j+2)*L])); have.add(s)
                continue
        out.append(b)
    return out
def parse_volume(d,label,outdir='.'):
    rows=[]; nsplit=0
    for p in sorted(glob.glob(os.path.join(d,'*.txt'))):
        era,d1,d2,blocks=P.page_blocks(p)
        if era is None or pd.isna(d1): continue
        b2=split_blocks(blocks); nsplit+=len(b2)-len(blocks)
        for b in b2:
            for which,ic,chg,chy in P.ic_from_block(era,b['toks']):
                wk=d1 if which=='d1' else d2
                if pd.isna(wk): continue
                rows.append(dict(week=wk,state=b['state'],ic=ic,chg=chg,chg_yr=chy,era=era,page=os.path.basename(p),raw='|'.join(b['toks'])))
    df=pd.DataFrame(rows)
    if not len(df): print(label,'nothing'); return df
    df=df[(df.ic>0)&(df.ic<400000)]; df['volume']=label
    df.to_csv(f'{outdir}/ic_tolerant_{label}.csv',index=False)
    print(f'{label}: {len(df)} state-week prints ({nsplit} rows recovered from glued blocks), weeks {df.week.min().date()} to {df.week.max().date()}, states {df.state.nunique()}')
    return df
if __name__=='__main__': parse_volume(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else '.')
