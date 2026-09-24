import json,os,re
from vq import norm
res=json.load(open('quote_results.json'))
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
    if p not in cache: cache[p]=norm(open(p).read()) if os.path.exists(p) else ''
    return cache[p]
out=[]
for r in res:
    if r['status']: continue
    docs=by_idx.get(r['idx'],[])
    bodies=[(u,body(p)) for u,p in docs]
    q=norm(r['quote']); w=q.split()
    # scan all 5-grams; report best coverage
    best=0; where=None
    for u,b in bodies:
        if not b: continue
        hits=sum(1 for k in range(0,max(1,len(w)-4)) if ' '.join(w[k:k+5]) in b)
        tot=max(1,len(w)-4)
        if hits/tot>best: best=hits/tot; where=u
    out.append({'idx':r['idx'],'quote':r['quote'],'cover':round(best,2),'src':where,
                'nsrc':len([1 for _,b in bodies if b]),'urls':r['urls']})
json.dump(out,open('miss_triage.json','w'),indent=0)
import collections
buckets=collections.Counter()
for o in out:
    c=o['cover']
    buckets['zero' if c==0 else ('low<0.3' if c<0.3 else ('mid<0.8' if c<0.8 else 'high>=0.8'))]+=1
print(len(out),'misses:',dict(buckets))
