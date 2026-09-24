import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations'}; bench.ABSTAIN=True
best=[]
for q in [0.4,0.5,0.6,0.7,0.8]:
 for thr in [0.5,1.0,1.5,2.0,3.0]:
  for gap in [0,6,12]:
   for win in [12,18]:
    allr=[]; nx=0
    for c in CLASSICAL:
        det=standalone(c,thr=thr,q=q,gap=gap)
        rows,extra=match(c,det,window=win); allr+=rows; nx+=len(extra)
    n=len(allr); f=sum(1 for r in allr if r['found'])
    hp=sum(r['hp'] for r in allr); ht=sum(r['ht'] for r in allr)
    best.append((f+hp+ht-nx, q,thr,gap,win,f,hp,ht,n,nx))
best.sort(reverse=True)
print(f'{"q":>4s} {"thr":>4s} {"gap":>4s} {"win":>4s}  {"matched":>9s} {"peak":>9s} {"trough":>9s} {"extra":>6s}')
for b in best[:16]:
    print(f'{b[1]:4.1f} {b[2]:4.1f} {b[3]:4d} {b[4]:4d}  {b[5]:4d}/{b[8]:<4d} {b[6]:4d}/{b[8]:<4d} {b[7]:4d}/{b[8]:<4d} {b[9]:6d}')
