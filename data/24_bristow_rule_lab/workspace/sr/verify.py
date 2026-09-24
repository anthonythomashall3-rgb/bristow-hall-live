import json, os, re
from colx import norm

def sq(s): return re.sub(r'\s+','', s)

targets=json.load(open('targets.json'))
ht=json.load(open('htargets.json'))
hmap={u:p+'.txt' for u,p in ht}
by_idx={}
for i,u,p in targets:
    by_idx.setdefault(i,[]).append((u,[p+'.col.txt', p+'.txt']))
entries={x['idx']:x for x in json.load(open('entries.json'))}
for idx,e in entries.items():
    for u in e['urls']:
        if u in hmap: by_idx.setdefault(idx,[]).append((u,[hmap[u]]))

cache={}
def body(paths):
    key=tuple(paths)
    if key not in cache:
        t=''
        for p in paths:
            if os.path.exists(p): t+='\n'+open(p).read()
        n=norm(t); cache[key]=(n, sq(n))
    return cache[key]

def trim(s): return s.strip().strip(' ,.;:')

def check(bodies, q):
    parts=[x for x in re.split(r'\s*(?:\.\.\.|…)\s*', q) if x.strip()]
    for u,(n,s) in bodies:
        if not n: continue
        if all(norm(x) in n for x in parts): return 'exact', u
        if all(norm(trim(x)) in n for x in parts): return 'trimmed', u
        if all(sq(norm(trim(x))) in s for x in parts): return 'nospace', u
    return None, None

res=[]
for idx in sorted(entries):
    e=entries[idx]
    if not e['quotes']: continue
    docs=by_idx.get(idx,[])
    bodies=[(u,body(ps)) for u,ps in docs]
    have=any(n for _,(n,_) in bodies)
    for q in e['quotes']:
        st,src=check(bodies,q)
        res.append({'idx':idx,'quote':q,'status':st,'src':src,'have':have,'urls':e['urls']})
json.dump(res, open('quote_results.json','w'), indent=0)
import collections
c=collections.Counter(r['status'] or ('NOSRC' if not r['have'] else 'MISS') for r in res)
print(len(res),'quotes:',dict(c))
