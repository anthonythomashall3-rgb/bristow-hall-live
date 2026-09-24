"""Japan: the committee's own ten components (ESRI's current coincident set, on disk from 1975)
as the diffusion panel, ESRI's phase convention, versus the shipped broad panel."""
import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, pandas as pd, itertools
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
ESRI_NAMES={'ESRI industrial production','producer goods shipments','durable consumer goods shipments','labor input','investment goods shipments','operating profits','effective job offer rate','exports volume'}
def load_yoy():
    out=[]
    for f,nm in (('retail_sales_yoy','retail sales yoy'),('wholesale_sales_yoy','wholesale sales yoy')):
        s=pd.read_csv(f'/home/claude/lab/esri/JPN_{f}.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
        out.append((nm,s))
    return out
cfg=PANELS['Japan']; chs_all=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
esri8=[(nm,s) for nm,s in chs_all if nm in ESRI_NAMES]; esri10=esri8+load_yoy()
def run(tag, panel, conv, line=45.0, run_p=4, band=0.30):
    bench.PHASE_CONV=conv; bench._PH.clear()
    ep=[];et=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq']); pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in panel if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<5:
            use=[(nm,s) for nm,s in chs_all if s.index.min()<=w0 and s.index.max()>=trm] or chs_all
        d=date_diffusion_panel(use,w0,w1,line=line,run_p=run_p,band=band)
        base=date_any('Japan',use,w0,w1,**K)
        pk=d['peak'] if d['peak'] is not None else base['peak']; tr=d['trough'] if d['trough'] is not None else base['trough']
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M'); ep.append(e1); et.append(e2)
    g=lambda e,t: sum(1 for x in e if x is not None and abs(x)<=t)
    E=[x for x in ep if x is not None]; T=[x for x in et if x is not None]
    print(f"{tag:44s} peaks {g(ep,0):2d}/{g(ep,1):2d}/{g(ep,3):2d} of {len(E)} bias {sum(E)/len(E):+.2f} | troughs {g(et,0):2d}/{g(et,1):2d}/{g(et,3):2d} of {len(T)} bias {sum(T)/len(T):+.2f}  P {ep} T {et}",flush=True)
run('shipped: broad panel, tool conv', chs_all, 'tool')
run('broad panel, esri conv', chs_all, 'esri')
run('ESRI 8 components, tool conv', esri8, 'tool')
run('ESRI 8 components, esri conv', esri8, 'esri')
run('ESRI 10 components, tool conv', esri10, 'tool')
run('ESRI 10 components, esri conv', esri10, 'esri')
for line,rp,band in itertools.product((45.,50.),(1,4),(0.30,0.0)):
    run(f'ESRI 10, esri conv, line {line} run {rp} band {band}', esri10, 'esri', line, rp, band)

print('\n=== ESRI\'s own rule (last month at or above the line before the minimum = peak; last month at or below after it = trough), hist_di on the panel')
def run2(tag, panel, conv, line=50.0, n=3):
    bench.PHASE_CONV=conv; bench._PH.clear()
    ep=[];et=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq']); pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in panel if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<5:
            use=[(nm,s) for nm,s in chs_all if s.index.min()<=w0 and s.index.max()>=trm] or chs_all
        di=hist_di(use,n)
        d=di_dates(di,w0,w1,line)
        base=date_any('Japan',use,w0,w1,**K)
        pk=d['peak'] if d['peak'] is not None else base['peak']; tr=d['trough'] if d['trough'] is not None else base['trough']
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M'); ep.append(e1); et.append(e2)
    g=lambda e,t: sum(1 for x in e if x is not None and abs(x)<=t)
    E=[x for x in ep if x is not None]; T=[x for x in et if x is not None]
    print(f"{tag:44s} peaks {g(ep,0):2d}/{g(ep,1):2d}/{g(ep,3):2d} of {len(E)} bias {sum(E)/len(E):+.2f} | troughs {g(et,0):2d}/{g(et,1):2d}/{g(et,3):2d} of {len(T)} bias {sum(T)/len(T):+.2f}  P {ep} T {et}",flush=True)
for conv in ('tool','esri'):
    for line in (50.0,45.0):
        run2(f'broad panel, {conv} conv, ESRI rule line {line}', chs_all, conv, line)
        run2(f'ESRI 10, {conv} conv, ESRI rule line {line}', esri10, conv, line)
        run2(f'ESRI 8, {conv} conv, ESRI rule line {line}', esri8, conv, line)
