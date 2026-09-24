import json,os,re,sys
from colx import norm
def sq(s): return re.sub(r'\s+','',s)
targets=json.load(open('targets.json')); ht=json.load(open('htargets.json'))
tm={}
for i,url,p in targets: tm.setdefault(url,[p+'.col.txt',p+'.txt'])
hm={url:[p+'.txt'] for url,p in ht}
entries={x['idx']:x for x in json.load(open('entries.json'))}
def bodies(i):
    out=[]
    for url in entries[i]['urls']:
        t=''
        for p in (tm.get(url) or hm.get(url) or []):
            if os.path.exists(p): t+='\n'+open(p).read()
        n=norm(t); out.append((url,n,sq(n)))
    return out
def report(i, quotes):
    bs=bodies(i)
    print(f'===== entry {i}')
    for q in quotes:
        qn=norm(q.strip(' ,.')); qs=sq(qn); w=qn.split()
        best=(0,None,None)
        for url,n,s in bs:
            if not n: continue
            if qn in n or qs in s: best=(1.0,url,'FULL'); break
            # longest prefix
            lo,hi=0,len(w)
            while lo<hi:
                mid=(lo+hi+1)//2
                if sq(' '.join(w[:mid])) in s: lo=mid
                else: hi=mid-1
            if lo/len(w)>best[0]: best=(lo/len(w),url,' '.join(w[:lo]))
        tag='PASS' if best[0]==1.0 else f'FAIL cov={best[0]:.2f}'
        print(f'  {tag} | {q[:92]}')
        if best[0]<1.0 and best[2]:
            print(f'        longest prefix found: "{best[2][:120]}"')
            # show context after
            for url,n,s in bs:
                k=s.find(sq(best[2])) if best[2] else -1
                if k>=0:
                    print(f'        source ctx: ...{n[max(0,n.find(best[2].split()[0]) ):][:250]}...')
                    break
if __name__=='__main__':
    u=json.load(open('unver.json'))['subst']
    want=set(int(a) for a in sys.argv[1:])
    byi={}
    for x in u: byi.setdefault(x['idx'],[]).append(x['quote'])
    for i in sorted(byi):
        if want and i not in want: continue
        report(i, byi[i])
