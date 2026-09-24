import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np

bench.SKIP={'exports','imports','car registrations','unemployment'}
bench.ABSTAIN=True
CFG=dict(min_depth=0.0, n=3, L=12, band_t=0.03, band_p=0.02, peak_cap=12, lead=12, tail=12)

print('='*86)
print('TABLE 1  The rule against the six classical chronologies, monthly coincident panels')
print('='*86)
print(f'{"":26s} {"episodes":>8s} {"peak":>10s} {"MAD":>6s} {"trough":>10s} {"MAD":>6s}')
tot=[]
for c in CLASSICAL:
    r=run_country2(c,**CFG); tot+=r
    s=score(r,'',show=False)
    print(f'{c:26s} {s["n"]:8d} {s["hp"]:5d}/{s["n"]:<4d} {s["mp"]:6.2f} {s["ht"]:5d}/{s["n"]:<4d} {s["mt"]:6.2f}')
s=score(tot,'',show=False)
print('-'*86)
print(f'{"all":26s} {s["n"]:8d} {s["hp"]:5d}/{s["n"]:<4d} {s["mp"]:6.2f} {s["ht"]:5d}/{s["n"]:<4d} {s["mt"]:6.2f}')
print(f'{"":26s} {"":8s} {100*s["hp"]/s["n"]:9.0f}% {"":6s} {100*s["ht"]/s["n"]:9.0f}%')

print()
print('='*86)
print('TABLE 2  Accuracy against the width of the panel')
print('='*86)
rows=[r for r in tot if r['nch']>0]
print(f'{"channels":>10s} {"episodes":>9s} {"peak":>12s} {"trough":>12s} {"MAD p":>7s} {"MAD t":>7s}')
for lo,hi,lab in [(1,2,'1-2'),(3,4,'3-4'),(5,6,'5-6'),(7,99,'7 or more')]:
    g=[r for r in rows if lo<=r['nch']<=hi]
    if not g: continue
    hp=sum(r['hp'] for r in g); ht=sum(r['ht'] for r in g); n=len(g)
    mp=np.mean([abs(r['ep']) for r in g if r['ep'] is not None])
    mt=np.mean([abs(r['et']) for r in g if r['et'] is not None])
    print(f'{lab:>10s} {n:9d} {hp:6d}/{n:<5d} {ht:6d}/{n:<5d} {mp:7.2f} {mt:7.2f}')

print()
print('='*86)
print('TABLE 3  The rule given the evidence the committee itself uses')
print('='*86)
SIX={'industrial production (Federal Reserve)','payroll employment','household employment',
     'real income less transfers','real consumption','real manufacturing and trade sales'}
_all={n for n,_ in channels('United States')}
bench.SKIP=_all-SIX
us=run_country2('United States',**CFG)
s=score(us,'',show=False)
bench.SKIP={'exports','imports','car registrations','unemployment'}
print(f'  United States, the NBER\'s six coincident indicators')
print(f'     peak {s["hp"]}/{s["n"]}  MAD {s["mp"]:.2f}      trough {s["ht"]}/{s["n"]}  MAD {s["mt"]:.2f}')
EST='/home/claude/lab/estat'
Q={'Euro area':(EZ_Q,['EA20_gdp_q','EA20_emp_q']),'Spain':(ES_Q,['ES_gdp_q','ES_emp_q']),
   'France':(FR_Q,['FR_gdp_q'])}
hp=ht=nn=0; det=[]
for c,(chr_,files) in Q.items():
    chs=[(f,load(f'{EST}/{f}.csv')) for f in files if os.path.exists(f'{EST}/{f}.csv')]
    for pk_off,tr_off in chr_:
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(n_,s_) for n_,s_ in chs if s_.index.min()<=w0 and s_.index.max()>=trm]
        if not use: continue
        tr_d=med([ch_trough(s_,w0,w1,0.03,1,4) for n_,s_ in use])
        ends=tr_d if tr_d is not None else w1
        pk_d=med([ch_peak(s_,w0,ends,0.02,1) for n_,s_ in use])
        a,ea=hit(pk_d,pk_off,'Q'); b,eb=hit(tr_d,tr_off,'Q')
        hp+=a; ht+=b; nn+=1; det.append((c,pk_off,tr_off,ea,eb))
print(f'  Euro area, Spain and France, quarterly GDP and employment')
print(f'     peak {hp}/{nn}                    trough {ht}/{nn}')
for c,p,t,ea,eb in det:
    print(f'        {c:12s} {str(p):9s} {str(t):9s}  peak {ea:+d}q  trough {eb:+d}q')
print()
print(f'  combined: {s["hp"]+hp}/{s["n"]+nn} peaks and {s["ht"]+ht}/{s["n"]+nn} troughs'
      f'  = {100*(s["hp"]+hp+s["ht"]+ht)/(2*(s["n"]+nn)):.0f}% of turning points')
