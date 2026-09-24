"""Eurostat monthly short-term business statistics, full history.

sts_inpr_m  industrial production by main industrial grouping
sts_trtu_m  retail trade turnover
sts_copr_m  construction production
"""
import json, os, subprocess, sys
OUT='/home/claude/lab/estat'; os.makedirs(OUT,exist_ok=True)
BASE='https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
def get(ds, params):
    q='&'.join(params)
    url=f'{BASE}{ds}?format=JSON&{q}'
    p=subprocess.run(['curl','-sS','-A','Mozilla/5.0','--max-time','120',url],capture_output=True)
    try: return json.loads(p.stdout.decode('utf-8','replace'))
    except Exception: return None
def series(j, fixed):
    """Return {nace: [(time,value)]} for a JSON-stat cube with one free dim (nace) + time."""
    d=j['dimension']; ids=j['id']; sizes=j['size']; val=j['value']
    idxs={k:{v:i for v,i in d[k]['category']['index'].items()} for k in ids}
    inv={k:{i:v for v,i in idxs[k].items()} for k in ids}
    out={}
    for flat,v in val.items():
        f=int(flat); coord=[]
        for s in reversed(sizes):
            coord.append(f%s); f//=s
        coord=list(reversed(coord))
        rec={k:inv[k][c] for k,c in zip(ids,coord)}
        out.setdefault(rec.get('nace_r2') or rec.get('indic_bt') or '_', []).append((rec['time'],v))
    return {k:sorted(v) for k,v in out.items()}

MIG={'B-D':'industrial production','C':'manufacturing production',
     'MIG_CAG':'capital goods production','MIG_ING':'intermediate goods production',
     'MIG_COG':'consumer goods production','MIG_DCOG':'consumer durables production',
     'MIG_NDCOG':'consumer nondurables production','MIG_NRG':'energy production',
     'F':'construction production','F_CC1':'building construction'}
GEOS=['FR','ES','DE','IT','NL','BE','AT','FI','PT','EL','IE','EA20','EU27_2020','SE','DK']
for g in GEOS:
    ps=['geo='+g,'s_adj=SCA','unit=I21']+['nace_r2='+k for k in ('B-D','C','MIG_CAG','MIG_ING','MIG_COG','MIG_DCOG','MIG_NDCOG','MIG_NRG')]
    j=get('sts_inpr_m',ps)
    if not j or 'value' not in j: print(g,'inpr: none'); continue
    ss=series(j,{})
    made=[]
    for nace,rows in ss.items():
        nm=MIG.get(nace)
        if not nm: continue
        rows=[(t,v) for t,v in rows if v is not None]
        if len(rows)<120: continue
        fn=f'{OUT}/{g}_L_{nace.replace("-","_")}.csv'
        with open(fn,'w') as f:
            f.write('date,value\n')
            for t,v in rows: f.write(f'{t}-01,{v}\n')
        made.append(f'{nace}:{rows[0][0]}..{rows[-1][0]}({len(rows)})')
    print(g,'inpr:', '  '.join(made) if made else 'nothing')
