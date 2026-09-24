import re,sys,glob
def parse(fn):
    L=open(fn).read().split('\n'); out={}; sec=None
    for l in L:
        if l.startswith('per episode'): sec=l.strip(); out[sec]=[]; continue
        if sec and l.startswith('   '):
            m=re.findall(r'err\s+(-?\d+)',l) or re.findall(r'\d{4}-\d{2}\s+(-?\d+)',l)
            if len(m)==2: out[sec].append((int(m[0]),int(m[1])))
        elif sec and not l.startswith('   '): sec=None
    return out
def cnt(e): return (sum(x==0 for x in e),sum(abs(x)<=1 for x in e),sum(abs(x)<=3 for x in e),len(e),sum(abs(x) for x in e)/len(e))
tags=[l.split('|')[0] for l in open('/tmp/variants_done.txt') if '|' in l]
SEC={'zaf_full':'per episode, the committee object:','twn_test':"per episode, the committee's own detrended index:",'deu_test':'per episode, the full panel:'}
print(f"{'variant':16s} {'ZAF P':10s} {'ZAF T':10s} {'TWN P':10s} {'TWN T':10s} {'DEU P':10s} {'DEU T':10s} | sum P    sum T    mae P  mae T")
for t in tags:
    row=[];SP=[0,0,0];ST=[0,0,0];mp=[];mt=[]
    for f,sec in SEC.items():
        e=parse(f'/tmp/v_{t}_{f}.txt')[sec]
        p=cnt([x for x,_ in e]); q=cnt([y for _,y in e])
        row.append(f"{p[0]}/{p[1]}/{p[2]}".ljust(10)); row.append(f"{q[0]}/{q[1]}/{q[2]}".ljust(10))
        for i in range(3): SP[i]+=p[i]; ST[i]+=q[i]
        mp+= [x for x,_ in e]; mt+=[y for _,y in e]
    print(f"{t:16s} "+' '.join(row)+f" | {SP[0]}/{SP[1]}/{SP[2]}".ljust(11)+f"{ST[0]}/{ST[1]}/{ST[2]}".ljust(9)+f"{sum(abs(x) for x in mp)/len(mp):.2f}  {sum(abs(x) for x in mt)/len(mt):.2f}")
