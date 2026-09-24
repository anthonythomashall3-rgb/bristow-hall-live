import json, os, re
from vq import norm
targets=json.load(open('targets.json'))
by_idx={}
for i,u,p in targets: by_idx.setdefault(i,[]).append((u,p+'.txt'))
entries={x['idx']:x for x in json.load(open('entries.json'))}
cache={}
def body(p):
    if p not in cache: cache[p]=open(p).read() if os.path.exists(p) else ''
    return cache[p]

def trim(s):
    return s.strip().strip(' ,.;:')

def probe(b, q):
    """return 'exact' | 'trimmed' | 'partial' | None"""
    parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*', q) if x.strip()]
    if all(norm(x) in b for x in parts): return 'exact'
    if all(norm(trim(x)) in b for x in parts): return 'trimmed'
    # partial: does at least 70% of the longest fragment's words appear contiguously?
    lg=max(parts,key=len); n=norm(trim(lg)); w=n.split()
    if len(w)>=8:
        for frac in (0.8,0.6,0.5):
            k=int(len(w)*frac)
            if k>=6 and ' '.join(w[:k]) in b: return f'partial({frac})'
    return None

results=[]
for idx in sorted(by_idx):
    e=entries.get(idx)
    if not e or not e['quotes']: continue
    bodies=[(u,body(p),p) for u,p in by_idx[idx]]
    for q in e['quotes']:
        best=None; bestu=None
        for u,b,p in bodies:
            if not b: continue
            r=probe(b,q)
            if r and (best is None or r=='exact'): best=r; bestu=u
            if r=='exact': break
        results.append({'idx':idx,'quote':q,'status':best,'src':bestu,
                        'have_text':any(b for _,b,_ in bodies)})
json.dump(results, open('quote_results.json','w'), indent=0)
import collections
c=collections.Counter(r['status'] if r['status'] else ('NOTEXT' if not r['have_text'] else 'MISS') for r in results)
print(len(results),'quotes:',dict(c))
