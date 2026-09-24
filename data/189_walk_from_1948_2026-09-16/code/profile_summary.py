import sys, os, io, contextlib, time, cProfile, pstats
os.chdir('/home/claude/ws'); sys.path.insert(0,'/home/claude/ws')
src=open('walk90.py').read()
head=src.split("# ---- the walk itself")[0] if "# ---- the walk itself" in src else src
# walk90's structure: the head defines everything up to the walk loop, but the loop lives in the exec'd tail of walk39.
# We exec the whole file with the walk loop disabled by giving an empty year range.
sys.argv=['walk90.py','2027','2026','wprof']
t0=time.time()
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(compile(src,'walk90','exec'))
print('preamble %.0f s'%(time.time()-t0), flush=True)
import pickle
SUM.clear()
P0=dict(BASE15)
variants=[('base',dict(P0)),('AYGJF',dict(P0,newlegs='AYGJF')),('AYGJFc',dict(P0,newlegs='AYGJFc')),('sahm.45',dict(P0,sahm=0.45)),('cs20',dict(P0,cs=20))]
pr=cProfile.Profile()
for nm,p in variants:
    t=time.time(); pr.enable(); s=summary(p); pr.disable(); print(nm,'%.1f s'%(time.time()-t), 'lags',s['lags'], flush=True)
st=pstats.Stats(pr); st.sort_stats('cumulative').print_stats(45)
st.sort_stats('tottime').print_stats(25)
