import json, os, re, glob
from colx import norm
def sq(s): return re.sub(r'\s+','',s)
docs=[]
for f in sorted(glob.glob('src/*.col.txt'))+sorted(glob.glob('src/*.html.txt'))+['/home/claude/michez.pdf.col.txt','src/sahm_ch2.pdf.col.txt']:
    if os.path.exists(f) and os.path.getsize(f)>500:
        n=norm(open(f).read()); docs.append((f,n,sq(n)))
print('corpus docs:',len(docs))
res=json.load(open('quote_results.json'))
def trim(s): return s.strip().strip(' ,.;:')
out=[]
for r in res:
    if r['status']: out.append(r); continue
    q=r['quote']; parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*',q) if x.strip()]
    found=None; how=None
    for f,n,s in docs:
        if all(norm(trim(x)) in n for x in parts): found=f; how='global'; break
        if all(sq(norm(trim(x))) in s for x in parts): found=f; how='global-nospace'; break
    r2=dict(r); r2['status']=how; r2['src']=found
    out.append(r2)
json.dump(out, open('quote_results.json','w'), indent=0)
import collections
c=collections.Counter(r['status'] or 'UNVERIFIED' for r in out)
print(dict(c))
