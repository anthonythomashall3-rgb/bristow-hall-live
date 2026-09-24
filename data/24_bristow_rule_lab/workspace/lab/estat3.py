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

GEOS=['ES','FR','IT','DE','NL','BE','AT','PT','FI','EL','IE','EA19','EA20']
JOBS=[      ('sts_trtu_m','retail_volume', dict(s_adj='SCA',unit='I21',nace_r2='G47',indic_bt='VOL_SLS')),
      ('sts_trtu_m','wholesale',     dict(s_adj='SCA',unit='I21',nace_r2='G46',indic_bt='VOL_SLS')),
      ('sts_trtu_m','motor_trade',   dict(s_adj='SCA',unit='I21',nace_r2='G45',indic_bt='VOL_SLS')),
      ('sts_copr_m','construction',  dict(s_adj='SCA',unit='I21',nace_r2='F',indic_bt='PRD')),
      ('sts_setu_m','services',      dict(s_adj='SCA',unit='I21',nace_r2='H-N_STS',indic_bt='VOL_SLS')),
      ('sts_setu_m','services_broad',dict(s_adj='SCA',unit='I21',nace_r2='G-N_STS',indic_bt='VOL_SLS')),
      ]
if __name__=='__main__':
    for g in GEOS:
        for ds,nm,flt in JOBS:
            try: pull(ds,g,nm,**flt)
            except Exception as e: print(g,nm,'ERR',e)
