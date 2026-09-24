"""MARGIN DIAGNOSTIC (9 September 2026): how far the walk-end lines (v3.22) stand from a false alarm and from a miss.
Each line is moved one grid step looser and one step safer, alone, and the record 1962-2026 is re-scored; then every
line one step looser at once. Uses walk40's objects and its summary cache (copied to m41). Nothing is written to w40.
Run: /opt/homebrew/bin/python3 margin41.py"""
import sys,os,shutil,pickle
sys.argv=['margin41.py','1962','2026','m41']
if not os.path.exists('cache/m41_sum.pkl'): shutil.copy('cache/w40_sum.pkl','cache/m41_sum.pkl')
src=open('walk40.py').read().split('# ---- the walk itself')[0]
exec(src)
GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare','cD') else g) for n,g in GRID]; GD=dict(GRID)
p=pickle.load(open('cache/w40_carry.pkl','rb'))
cut=pd.Timestamp(2026,1,1); ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
def verdict(q):
    v=clean(q,cut,ks,kt); s=summary(q)
    if v is not None: return 'clean; late %d, median %+.0f d, mean %+.0f d; troughs off %d, median |%.0f| d'%(v and obj(v)[0],obj(v)[1],obj(v)[2],obj(v)[3],obj(v)[4])
    fa=[o.strftime('%Y-%m-%d') for o in s['fa'] if o<cut]; miss=[PK[j].strftime('%Y-%m') for j in ks if j not in s['lags']]
    tro=[PK[k].strftime('%Y-%m') for k in kt if k not in s['pair'] or s['pair'][k][1]<-31]
    return 'NOT clean: false alarms %s; missed %s; troughs unclosed or >31 d early %s'%(fa,miss,tro)
print('walk-end configuration:',verdict(p))
LOOSE=[n for n in NAMES if n not in ('hback','cn')]
for n in NAMES:
    gr=GD[n]; i=gr.index(p[n])
    for step,label in ((1,'LOOSER'),(-1,'safer')):
        j=i+step
        if 0<=j<len(gr) and gr[j] is not None:
            q=dict(p); q[n]=gr[j]; print('%-7s %-6s -> %-6s %-6s: %s'%(n,p[n],gr[j],label,verdict(q)))
        else: print('%-7s %-6s %-6s: no grid step'%(n,p[n],label))
q=dict(p)
for n in LOOSE:
    gr=GD[n]; i=gr.index(p[n])
    if i+1<len(gr) and gr[i+1] is not None: q[n]=gr[i+1]
print('ALL lines one step looser at once:',verdict(q))
q=dict(p)
for n in LOOSE:
    gr=GD[n]; i=gr.index(p[n])
    if i-1>=0: q[n]=gr[i-1]
print('ALL lines one step safer at once:',verdict(q))
pickle.dump(SUM,open(SUMF,'wb'))
