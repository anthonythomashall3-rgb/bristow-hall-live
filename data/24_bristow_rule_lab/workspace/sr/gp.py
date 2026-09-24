import json,os,re,sys,glob
from colx import norm
def sq(s): return re.sub(r'\s+','',s)
targets=json.load(open('targets.json')); ht=json.load(open('htargets.json'))
tm={}
for i,url,p in targets: tm.setdefault(url,p+'.col.txt')
hm={url:p+'.txt' for url,p in ht}
entries={x['idx']:x for x in json.load(open('entries.json'))}
res=json.load(open('quote_results.json'))
byi={}
for x in res:
    if x['status'] is None: byi.setdefault(x['idx'],[]).append(x['quote'])
for idx in [int(a) for a in sys.argv[1:]]:
    print(f'===== {idx}')
    bodies=[]
    for url in entries[idx]['urls']:
        p=tm.get(url) or hm.get(url)
        if p and os.path.exists(p) and os.path.getsize(p)>500:
            n=norm(open(p).read()); bodies.append((url,n,sq(n)))
    for q in byi.get(idx,[]):
        qn=norm(q.strip(' ,.')); qs=sq(qn); w=qn.split()
        hit=None
        for url,n,s in bodies:
            if qn in n or qs in s: hit=url; break
        if hit: print('  PASS |',q[:80]); continue
        # longest prefix across bodies
        best=(0,'')
        for url,n,s in bodies:
            for k in range(len(w),1,-1):
                if sq(' '.join(w[:k])) in s:
                    if k>best[0]: best=(k,' '.join(w[:k]))
                    break
        print(f'  FAIL ({best[0]}/{len(w)} words) |',q[:80])
        if best[0]>=3:
            for url,n,s in bodies:
                i=s.find(sq(best[1]))
                if i>=0:
                    # map back roughly by searching in n
                    j=n.find(best[1][:40])
                    print('     src ctx:', (n[max(0,j-80):j+260] if j>=0 else s[max(0,i-60):i+240])[:330])
                    break
