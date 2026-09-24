import json, os, re
from vq import norm
targets=json.load(open('targets.json'))
ht=json.load(open('htargets.json'))
hmap={u:p+'.txt' for u,p in ht}
by_idx={}
for i,u,p in targets: by_idx.setdefault(i,[]).append((u,p+'.txt'))
entries={x['idx']:x for x in json.load(open('entries.json'))}
for idx,e in entries.items():
    for u in e['urls']:
        if u in hmap: by_idx.setdefault(idx,[]).append((u,hmap[u]))
cache={}
def body(p):
    if p not in cache: cache[p]=open(p).read() if os.path.exists(p) else ''
    return cache[p]
def trim(s): return s.strip().strip(' ,.;:')
def probe(b,q):
    parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*',q) if x.strip()]
    if all(norm(x) in b for x in parts): return 'exact'
    if all(norm(trim(x)) in b for x in parts): return 'trimmed'
    return None
results=[]
for idx in sorted(entries):
    e=entries[idx]
    if not e['quotes']: continue
    docs=by_idx.get(idx,[])
    bodies=[(u,norm(body(p))) for u,p in docs]
    have=any(b for _,b in bodies)
    for q in e['quotes']:
        st=None;src=None
        for u,b in bodies:
            if not b: continue
            r=probe(b,q)
            if r: st=r; src=u; break
        results.append({'idx':idx,'quote':q,'status':st,'src':src,'have':have,
                        'urls':e['urls']})
json.dump(results,open('quote_results.json','w'),indent=0)
import collections
c=collections.Counter(r['status'] or ('NOSRC' if not r['have'] else 'MISS') for r in results)
print(len(results),'quotes:',dict(c))
