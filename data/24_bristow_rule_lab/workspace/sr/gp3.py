import json,os,re,sys
from colx import norm
def sq(s): return re.sub(r'\s+','',s)
umap={}
for i,u,p in json.load(open('targets.json')): umap.setdefault(u,[]).extend([p+'.col.txt',p+'.txt'])
for u,p in json.load(open('htargets.json')): umap.setdefault(u,[]).append(p+'.txt')
for i,u,p in json.load(open('targets_new.json')): umap.setdefault(u,[]).append(p+'.col.txt')
for u,p in json.load(open('htargets_new.json')): umap.setdefault(u,[]).append(p+'.txt')
entries={x['idx']:x for x in json.load(open('entries2.json'))}
res=json.load(open('qr3.json'))
byi={}
for r in res:
    if r['status'] is None: byi.setdefault(r['idx'],[]).append(r['quote'])
def bodies(i):
    out=[]
    for u in entries[i]['urls']:
        t=''
        for p in umap.get(u,[]):
            if os.path.exists(p):
                try: t+='\n'+open(p).read()
                except: pass
        n=norm(t); out.append((u,n,sq(n)))
    return out
for i in [int(a) for a in sys.argv[1:]]:
    print(f'===== {i}')
    bs=bodies(i)
    for u,n,s in bs: print(f'   src {len(n):>8}  {u[:88]}')
    for q in byi.get(i,[]):
        qn=norm(q.strip(' ,.')); w=qn.split(); qs=sq(qn)
        best=(0,'',None)
        for u,n,s in bs:
            if not n: continue
            lo,hi=0,len(w)
            while lo<hi:
                mid=(lo+hi+1)//2
                if sq(' '.join(w[:mid])) in s: lo=mid
                else: hi=mid-1
            if lo>best[0]: best=(lo,' '.join(w[:lo]),u)
        frac=best[0]/max(1,len(w))
        print(f'   {"PASS" if frac==1 else f"FAIL {best[0]}/{len(w)}"} | {q[:88]}')
        if 0<frac<1:
            for u,n,s in bs:
                k=s.find(sq(best[1]))
                if k>=0:
                    print('        ctx:', s[max(0,k-90):k+230]); break
