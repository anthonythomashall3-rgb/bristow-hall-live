"""ESRI's own rule, verbatim (Cabinet Office, 用語の解説):
"ヒストリカルDIが50%ラインを下から上に切る直前の月が景気の谷、上から下に切る直前の月が
景気の山に対応する。"  -- the month immediately before the historical DI cuts the 50 percent
line from below is the trough; the month immediately before it cuts from above is the peak."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, itertools
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)

def esri_dates(di, w0, w1, line=50.0, run=0):
    """Peak: last month with DI >= line before the first sustained fall below it.
       Trough: last month with DI <= line before the first sustained rise above it."""
    d=di[w0:w1].dropna()
    if len(d)<4: return (None,None)
    v=d.values; idx=d.index; n=len(v)
    def sustained(i, cond):
        c=0; j=i
        while j<n and cond(v[j]): c+=1; j+=1
        return c>=max(run,1)
    pk=None
    for i in range(n-1):
        if v[i]>=line and v[i+1]<line and sustained(i+1, lambda x: x<line):
            pk=idx[i]; break
    lo=int(np.argmin(v))
    tr=None
    for i in range(lo, n-1):
        if v[i]<=line and v[i+1]>line and sustained(i+1, lambda x: x>line):
            tr=idx[i]; break
    return (pk,tr)

cfg=PANELS['Japan']; chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
EPS=[]
for _e in cfg['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
    EPS.append((pk_off,tr_off,w0,w1,use))

best=[]
for line,run,n_di in itertools.product((45.,50.,55.),(0,1,2,3,4,5),(1,3,5,7)):
    hp=ht=0; ep=[]; et=[]; rows=[]
    for pk_off,tr_off,w0,w1,use in EPS:
        di=hist_di(use,n_di)
        pk,tr=(None,None) if di is None else esri_dates(di,w0,w1,line,run)
        if pk is None or tr is None:
            b=date_any('Japan',use,w0,w1,**K)
            pk=pk if pk is not None else b['peak']; tr=tr if tr is not None else b['trough']
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp+=a; ht+=b2
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    best.append((hp+ht,hp,ht,sum(1 for x in ep if x<=2)+sum(1 for x in et if x<=2),
                 np.mean(ep),np.mean(et),line,run,n_di,rows))
best.sort(key=lambda r:(-r[0],-r[3],r[4]+r[5]))
for r in best[:12]:
    print(f'tot={r[0]:2d} P{r[1]:2d} T{r[2]:2d} w2={r[3]:2d} MAD {r[4]:.2f}/{r[5]:.2f}  line={r[6]} run={r[7]} n_di={r[8]}')
print()
print('best detail (line,run,n_di =',best[0][6],best[0][7],best[0][8],')')
for x in best[0][9]: print('   ',x)
