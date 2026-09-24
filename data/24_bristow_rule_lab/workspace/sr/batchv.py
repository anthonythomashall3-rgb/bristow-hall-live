import json, os, re
from vq import norm
targets=json.load(open('targets.json'))
by_idx={}
for i,u,p in targets: by_idx.setdefault(i,[]).append((u,p+'.txt'))
entries={x['idx']:x for x in json.load(open('entries.json'))}
cache={}
def body(p):
    if p not in cache:
        cache[p]=open(p).read() if os.path.exists(p) else ''
    return cache[p]
results=[]
for idx in sorted(by_idx):
    e=entries.get(idx)
    if not e or not e['quotes']: continue
    bodies=[(u,body(p)) for u,p in by_idx[idx]]
    for q in e['quotes']:
        parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*', q) if x.strip()]
        hit=None
        for u,b in bodies:
            if b and all(norm(x) in b for x in parts): hit=u; break
        results.append({'idx':idx,'quote':q,'found':hit,'srcs':[u for u,_ in by_idx[idx]]})
json.dump(results, open('quote_results.json','w'), indent=0)
ok=sum(1 for r in results if r['found'])
print('checked',len(results),'matched',ok,'unmatched',len(results)-ok)
