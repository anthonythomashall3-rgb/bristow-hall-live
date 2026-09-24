import sys; sys.path.insert(0,'/home/claude/lab')
import plateau
from plateau import run
from w2 import w2
import bench
from bench import score, ALL
CAND=[('last','last',0.03,0.01),('mid','last',0.03,0.01),('mid','last',0.12,0.02),
      ('mid','mid',0.12,0.01),('mid','last',0.08,0.02),('mid','mid',0.03,0.01)]
res={}
for c_ in CAND:
    tot=run(*c_[:2],band_t=c_[2],band_p=c_[3]); res[c_]=tot
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{str(c_):34s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
# leave one chronology out on the within-two objective
def w2c(rows,c):
    r=[x for x in rows if x['country']==c and not (x['pk'] is None and x['tr'] is None)]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
oos=0; n=0; picks={}
for c in ALL:
    best=max(CAND,key=lambda k: sum(w2c(res[k],o) for o in ALL if o!=c))
    picks[c]=best; oos+=w2c(res[best],c)
    n+=2*len([x for x in res[best] if x['country']==c and not (x['pk'] is None and x['tr'] is None)])
print(f'leave-one-chronology-out within two months: {oos}/{n}')
import collections
print('chosen by the other eight:',collections.Counter(picks.values()))
