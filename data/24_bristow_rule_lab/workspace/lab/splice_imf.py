"""Chain the IMF Production Index onto the front of the national/OECD channel.

Where the IMF's Production Indexes (STA dataflow PI) begin earlier than the
channel already in the panel, the IMF series is chained on at the first month
the two overlap, so the level is continuous and the concept is counted once.
A concept whose panel channel already starts at or before the IMF series is
left alone.
"""
import os, pandas as pd
KEI='/home/claude/lab/kei'; IMF='/home/claude/lab/imf'; OUT='/home/claude/lab/spliced'
os.makedirs(OUT,exist_ok=True)
def load(p):
    d=pd.read_csv(p); d.columns=['d','v']
    d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    return d.dropna().set_index('d')['v'].astype(float).sort_index()
def imf_path(area, codes=('IND_SA_IX','IND_IX')):
    for c in codes:
        p=f'{IMF}/{area}_{c}.csv'
        if os.path.exists(p): return p
    return None
JOBS=[  # (area, existing channel file, output name, imf codes)
 ('JPN', f'{KEI}/JPN_PRVM_BTE.csv','JPN_ip',('IND_IX','IND_SA_IX')),
 ('KOR', f'{KEI}/KOR_PRVM_BTE.csv','KOR_ip',('IND_SA_IX','IND_IX')),
 ('ESP', f'{KEI}/ESP_PRVM_BTE.csv','ESP_ip',('IND_IX','IND_SA_IX')),
 ('KOR', f'{KEI}/KOR_PRVM_C.csv',  'KOR_mfg',('C_IX',)),
 ('JPN', f'{KEI}/JPN_PRVM_C.csv',  'JPN_mfg',('C_IX',)),
 ('BRA', f'{KEI}/BRA_PRVM_BTE.csv','BRA_ip',('IND_IX','IND_SA_IX')),
 ('CAN', f'{KEI}/CANX_PRVM_BTE.csv','CAN_ip',('IND_IX','IND_SA_IX')),
 ('USA', '/home/claude/archive/data/fred/INDPRO.csv','USA_ip',('IND_SA_IX','IND_IX')),
]
for area,nat,out,codes in JOBS:
    ip=imf_path(area,codes)
    if not os.path.exists(nat) or ip is None: print(f'{out}: missing'); continue
    a=load(nat); b=load(ip)
    if b.index.min()>=a.index.min():
        print(f'{out}: IMF starts {b.index.min():%Y-%m} >= panel {a.index.min():%Y-%m} - left alone'); continue
    ov=b.index.intersection(a.index)
    if len(ov)==0: print(f'{out}: no overlap - left alone'); continue
    j=ov.min(); k=float(a[j])/float(b[j])
    res=pd.concat([b[:j][:-1]*k, a])
    res=res[~res.index.duplicated(keep='last')].sort_index()
    with open(f'{OUT}/{out}.csv','w') as g:
        g.write('date,value\n')
        for d,v in res.items(): g.write(f'{d:%Y-%m-%d},{v:.6f}\n')
    print(f'{out}: {res.index.min():%Y-%m}..{res.index.max():%Y-%m} n={len(res)}  (IMF {b.index.min():%Y-%m}, panel {a.index.min():%Y-%m}, chained at {j:%Y-%m})')
