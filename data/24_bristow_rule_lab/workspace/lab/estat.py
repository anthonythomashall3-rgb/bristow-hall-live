"""Eurostat monthly short-term business statistics."""
import json, os, subprocess, sys
OUT='/home/claude/lab/estat'; os.makedirs(OUT, exist_ok=True)
BASE='https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'

def pull(ds, geo, name, **flt):
    q='&'.join(f'{k}={v}' for k,v in flt.items())
    url=f'{BASE}{ds}?format=JSON&geo={geo}&lang=en&{q}'
    p=subprocess.run(['curl','-sS','--max-time','120','-A','Mozilla/5.0',url],capture_output=True)
    try: d=json.loads(p.stdout.decode('utf-8','replace'))
    except Exception: return None
    if 'value' not in d or not d['value']: return None
    tm=d['dimension']['time']['category']['index']
    inv={v:k for k,v in tm.items()}
    vals=d['value']
    ser=[]
    for k,v in vals.items():
        t=inv.get(int(k))
        if t and v is not None: ser.append((t,v))
    ser.sort()
    if len(ser)<120: return None
    fn=f'{OUT}/{geo}_{name}.csv'
    with open(fn,'w') as g:
        g.write('date,value\n')
        for t,v in ser: g.write(f'{t}-01,{v}\n')
    print(f'{geo} {name}: {ser[0][0]} .. {ser[-1][0]}  n={len(ser)} -> {fn}')
    return fn

GEOS=['ES','FR','IT','DE','NL','BE','AT','PT','FI','EL','IE','EA19','EA20','EU27_2020']
JOBS=[('sts_inpr_m','ip_total',      dict(s_adj='SCA',unit='I21',nace_r2='B-D')),
      ('sts_inpr_m','ip_capital',    dict(s_adj='SCA',unit='I21',nace_r2='MIG_CAG')),
      ('sts_inpr_m','ip_intermed',   dict(s_adj='SCA',unit='I21',nace_r2='MIG_ING')),
      ('sts_inpr_m','ip_consumer',   dict(s_adj='SCA',unit='I21',nace_r2='MIG_COG')),
      ('sts_inpr_m','ip_durable',    dict(s_adj='SCA',unit='I21',nace_r2='MIG_DCOG')),
      ('sts_inpr_m','ip_nondurable', dict(s_adj='SCA',unit='I21',nace_r2='MIG_NDCOG')),
      ('sts_trtu_m','retail_volume', dict(s_adj='SCA',unit='I21',nace_r2='G47',indic_bt='TOVV')),
      ('sts_copr_m','construction',  dict(s_adj='SCA',unit='I21',nace_r2='F',indic_bt='PROD')),
      ('sts_setu_m','services',      dict(s_adj='SCA',unit='I21',nace_r2='H-N_STS',indic_bt='NETTUR')),
      ]
if __name__=='__main__':
    for g in GEOS:
        for ds,nm,flt in JOBS:
            try: pull(ds,g,nm,**flt)
            except Exception as e: print(g,nm,'ERR',e)
