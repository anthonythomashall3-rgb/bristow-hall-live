import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
g=load('/home/claude/lab/insee/FR_gdp_q_long.csv')
c=load('/home/claude/lab/insee/FR_conso_tot_q.csv')
print('French quarterly GDP alone, dated with the two clauses (n=1, L=4):')
hp=ht=0
for pk_off,tr_off in FR_Q:
    pkm=q2m(pk_off); trm=q2m(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    tr=ch_trough(g,w0,w1,0.03,1,4,abstain=False)
    pk=ch_peak(g,w0,tr if tr is not None else w1,0.01,1,abstain=False)
    a,_=hit(pk,pk_off,'Q'); b,_=hit(tr,tr_off,'Q'); hp+=a; ht+=b
    f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
    print(f'   {pk_off}->{tr_off}  {f(pk)}/{f(tr)}  {"P" if a else "-"}{"T" if b else "-"}')
print(f'   GDP alone: peak {hp}/5 trough {ht}/5')
print()
print('French quarterly GDP + consumption, median of the two:')
hp=ht=0
for pk_off,tr_off in FR_Q:
    pkm=q2m(pk_off); trm=q2m(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    tr=med([ch_trough(s,w0,w1,0.03,1,4,abstain=False) for s in (g,c)])
    pk=med([ch_peak(s,w0,tr if tr is not None else w1,0.01,1,abstain=False) for s in (g,c)])
    a,_=hit(pk,pk_off,'Q'); b,_=hit(tr,tr_off,'Q'); hp+=a; ht+=b
print(f'   GDP+consumption: peak {hp}/5 trough {ht}/5')
print()
r=run_country_concept('France',**K); s=score(r,'',show=False)
print(f'monthly panel (shipped): peak {s["hp"]}/5 trough {s["ht"]}/5')
