"""Parse ECRI's July 2021 table (Business Cycle Peak and Trough Dates, 22 Countries,
1948-2020; pdftotext -layout) into {country: [(kind, 'YYYY-MM'), ...]}, by assigning each
date token to the nearest column centre of the header line.  Validated against the 2010
table already parsed (ecri_chronology_2010.json)."""
import re, json, sys
txt=open('/home/claude/lab/cmp/ecri_BC_2107.txt',encoding='utf-8').read()
pages=txt.split('\f')
HEAD={0:['United States','Canada','Mexico','Brazil','Germany','France','United Kingdom','Italy','Spain','Switzerland','Sweden','Austria','Russia','Poland'],
      1:['Japan','China','India','Korea','Australia','Taiwan','New Zealand','South Africa']}
out={}
for pi,page in enumerate(pages[:2]):
    lines=page.split('\n')
    # the header line with the country names
    hl=next(l for l in lines if ('Peak or' in l and 'United' in l) or ('Trough' in l and 'Japan' in l))
    # column centres: locate each header word's centre
    names=HEAD[pi]; centres=[]
    pos=0
    for nm in names:
        key=nm.split()[0] if nm not in ('United Kingdom','South Africa','New Zealand') else nm.split()[0]
        # 'United' appears twice on page 0: States then Kingdom
        i=hl.find(key,pos); assert i>=0,(nm,key)
        centres.append(i+len(key)/2); pos=i+len(key)
    for nm in names: out[nm]=[]
    for l in lines:
        m=re.match(r'\s*(?:\d{4}-\d{4})?\s+([PT])\s+(.*\S)\s*$',l)
        if not m: continue
        kind=m.group(1); body=l
        for t in re.finditer(r'(\d{1,2})/(\d{2})',body):
            c=(t.start()+t.end())/2
            j=min(range(len(centres)),key=lambda k:abs(centres[k]-c))
            mo=int(t.group(1)); yy=int(t.group(2)); y=1900+yy if yy>=30 else 2000+yy
            out[names[j]].append((kind,f'{y}-{mo:02d}'))
for k in out: out[k].sort(key=lambda x:x[1])
json.dump(out,open('/home/claude/lab/cmp/ecri_chronology_2021.json','w'),indent=1)
old=json.load(open('/home/claude/lab/cmp/ecri_chronology_2010.json'))
for k in out:
    o=set(map(tuple,old.get(k,[]))); n=set(out[k])
    print(k, len(out[k]), '| in 2010 not 2021:', sorted(o-n), '| new in 2021:', sorted(x for x in n-o))
