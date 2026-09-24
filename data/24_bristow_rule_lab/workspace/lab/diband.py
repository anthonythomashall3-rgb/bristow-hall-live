import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
import re
src=open('/home/claude/lab/bench.py').read()
import importlib
for b in (0.20,0.30,0.40,0.45,0.55):
    new=src.replace("def date_diffusion_panel(chs, w0, w1, line=45.0, run=1, band=0.30,",
                    f"def date_diffusion_panel(chs, w0, w1, line=45.0, run=1, band={b},")
    open('/home/claude/lab/_db.py','w').write(new)
    import _db; importlib.reload(_db)
    _db.SKIP=bench.SKIP; _db.SKIP_PEAK=set(); _db.SKIP_TROUGH=set(); _db.ABSTAIN=True
    tot=[]
    for c in _db.ALL: tot+=_db.run_country_concept(c,**K)
    a,na,b2,nb,ma_,mb,sa,sb=w2(tot); s=_db.score(tot,'',show=False)
    j=_db.score([r for r in tot if r['country']=='Japan'],'',show=False)
    print(f'diffusion band={b}  within2 {a}+{b2}={a+b2}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  Japan {j["hp"]}/{j["ht"]}')
