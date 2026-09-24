import json, os, subprocess
OUT='/home/claude/lab/estat'; os.makedirs(OUT,exist_ok=True)
BASE='https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
def pull(ds, geo, name, **flt):
    q='&'.join(f'{k}={v}' for k,v in flt.items())
    url=f'{BASE}{ds}?format=JSON&geo={geo}&lang=en&{q}'
    p=subprocess.run(['curl','-sS','--max-time','120','-A','Mozilla/5.0',url],capture_output=True)
    try: d=json.loads(p.stdout.decode('utf-8','replace'))
    except Exception: return None
    if 'value' not in d or not d['value']: print(geo,name,'empty'); return None
    inv={v:k for k,v in d['dimension']['time']['category']['index'].items()}
    ser=sorted((inv[int(k)],v) for k,v in d['value'].items() if v is not None and int(k) in inv)
    if len(ser)<40: print(geo,name,'short',len(ser)); return None
    fn=f'{OUT}/{geo}_{name}.csv'
    with open(fn,'w') as g:
        g.write('date,value\n')
        for t,v in ser:
            y,qq=t.split('-Q'); g.write(f'{y}-{3*(int(qq)-1)+2:02d}-01,{v}\n')
    print(f'{geo} {name}: {ser[0][0]} .. {ser[-1][0]} n={len(ser)}')
    return fn
for g in ['EA20','EA19','ES','FR','IT','DE','NL','BE','PT','EL','FI','AT','IE']:
    pull('namq_10_gdp', g, 'gdp_q', s_adj='SCA', unit='CLV_I10', na_item='B1GQ')
    pull('namq_10_a10_e', g, 'emp_q', s_adj='SCA', unit='THS_PER', na_item='EMP_DC', nace_r2='TOTAL')
