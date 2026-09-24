"""§12 item 6: Spain's thin panels, filled from the Banco de España.

Version 17 recorded that Spain's 1974 contraction has two monthly channels and its 1978
contraction three, and that "the gap has to come from the Banco de España's historical
bulletin".  It does, and the bulletin is a free keyless CSV service.

Chapters 18, 23 and 24 of the Boletín Estadístico, downloaded from
www.bde.es/webbe/es/estadisticas/compartido/datos/csv/, carry these monthly series
beginning before 1975 — the first and last observations are as the files themselves report:

    paro registrado (registered unemployment)      D_1JA0D000       1933-07
    cement production                             D_1IE00000       1955-01
    car registrations                             DMVATTUORTO.M    1960-01
    motorcycle registrations                      DMVATMDORTO.M    1964-01
    steel production                              D_1ID10000       1968-01
    steel apparent availability                   D_1KC06000       1968-01
    gasoline consumption (CORES)                  D_1IN1100T       1969-01
    diesel consumption (CORES)                    D_1IN1200T       1969-01
    cement apparent consumption                   D_1KB23000       1970-01

Note on the path: the address given in the Bank's own CSV manual
(www.bde.es/webbde/es/estadis/infoest/series/) is dead and returns an HTML 404 page under
HTTP 200 — a soft 404 that would be read as success by any code checking the status alone.
The live path is /webbe/es/estadisticas/compartido/datos/csv/, and the file names must be
lower case: be2311.csv resolves, BE2311.csv does not.
"""
import sys; sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
SKIP={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=SKIP; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
ES=[((1974,4),(1975,2)),((1978,3),(1979,2)),((1992,1),(1993,3)),((2008,2),(2009,4)),
    ((2010,4),(2013,2)),((2019,4),(2020,2))]
BASE=[(nm,s) for nm,s in channels('Spain') if nm not in SKIP]
def E(n): return load(f'/home/claude/lab/esp/ESP_{n}.csv')
NEW=[('cement production',E('cement_production')),
     ('steel production',E('steel_production')),
     ('steel availability',E('steel_availability')),
     ('gasoline consumption',E('gasoline_consumption')),
     ('diesel consumption',E('diesel_consumption')),
     ('cement consumption',E('cement_consumption')),
     ('vehicle registrations',E('car_registrations'))]
import bristow_rule_v3 as B3
def B_to_q(s): return B3.to_quarter(s)
def run(chs,label):
    hp=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk,tr in ES:
        pkm=q2m(pk); trm=q2m(tr)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        nch=len(use)
        uq=[(nm,B_to_q(s)) for nm,s in use]
        b=date_any('Spain',uq,w0,w1,n=1,L=4,**{k:v for k,v in K.items()})
        a,e1=hit(b['peak'],pk,'Q'); c,e2=hit(b['trough'],tr,'Q')
        hp+=a; ht+=c; n+=1
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk,e1,tr,e2,nch))
    print(f'{label:44s} peaks {hp}/{n}  troughs {ht}/{n}   MAD {np.mean(ep):.2f}/{np.mean(et):.2f}')
    for x in rows:
        print(f'   {x[0]} err {str(x[1]):>5s}   {x[2]} err {str(x[3]):>5s}   channels {x[4]}')
    return hp,ht
VOL=[c for c in NEW if c[0] in ('cement production','steel production',
     'gasoline consumption','diesel consumption')]
CONS=[c for c in NEW if c[0] in ('steel availability','cement consumption')]
run(BASE,'the shipped Spanish panel')
print()
run(BASE+VOL,'plus the four Banco de España PRODUCTION volumes')
print()
run(BASE+VOL+CONS,'plus availability and apparent consumption too')
print()
run(BASE+NEW,'plus vehicle registrations as well (already in the skip list)')
