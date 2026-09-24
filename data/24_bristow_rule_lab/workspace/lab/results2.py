import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
L=['='*92]
def P(x=''): L.append(x); print(x)

P('='*92)
P('TABLE 1  Every contraction in the nine official chronologies, dated by the concept')
P('         that chronology encodes.  No episode is left undated.')
P('='*92)
P(f'{"chronology":26s} {"concept":10s} {"n":>3s} {"peak":>11s} {"MAD":>6s} {"trough":>11s} {"MAD":>6s}')
tot=[]
for c in ALL:
    r=run_country_concept(c,**K); tot+=r
    s=score(r,'',show=False)
    P(f'{c:26s} {CONCEPT[c]:10s} {s["n"]:3d} {s["hp"]:5d}/{s["n"]:<5d} {s["mp"]:6.2f} {s["ht"]:5d}/{s["n"]:<5d} {s["mt"]:6.2f}')
s=score(tot,'',show=False)
P('-'*92)
P(f'{"all":26s} {"":10s} {s["n"]:3d} {s["hp"]:5d}/{s["n"]:<5d} {s["mp"]:6.2f} {s["ht"]:5d}/{s["n"]:<5d} {s["mt"]:6.2f}')
P(f'{"":26s} {"":10s} {"":3s} {100*s["hp"]/s["n"]:10.0f}% {"":6s} {100*s["ht"]/s["n"]:10.0f}%')
nod=sum(1 for r in tot if r['pk'] is None or r['tr'] is None)
P(f'   contractions with no date: {nod} of {s["n"]}')

P('')
P('='*92)
P('TABLE 2  The six chronologies that date a level')
P('='*92)
cl=[r for r in tot if CONCEPT[r['country']]=='level']
sc=score(cl,'',show=False)
P(f'   53 contractions   peak {sc["hp"]}/{sc["n"]} ({100*sc["hp"]/sc["n"]:.0f}%)  MAD {sc["mp"]:.2f}     trough {sc["ht"]}/{sc["n"]} ({100*sc["ht"]/sc["n"]:.0f}%)  MAD {sc["mt"]:.2f}')

P('')
P('='*92)
P('TABLE 3  Given the evidence the committee itself uses')
P('='*92)
SIX={'industrial production (Federal Reserve)','payroll employment','household employment',
     'real income less transfers','real consumption','real manufacturing and trade sales'}
allnames={n for n,_ in channels('United States')}
keep=bench.SKIP
bench.SKIP=allnames-SIX
us=score(run_country_concept('United States',**K),'',show=False)
bench.SKIP=keep
P(f'   United States, the NBER\'s six coincident indicators   peak {us["hp"]}/12   trough {us["ht"]}/12')
EST='/home/claude/lab/estat'
Q={'Euro area':(EZ_Q,['EA20_gdp_q','EA20_emp_q']),'Spain':(ES_Q,['ES_gdp_q','ES_emp_q']),'France':(FR_Q,['FR_gdp_q'])}
hp=ht=nn=0
for c,(chr_,files) in Q.items():
    chs=[(f,load(f'{EST}/{f}.csv')) for f in files if os.path.exists(f'{EST}/{f}.csv')]
    for pk_off,tr_off in chr_:
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(n_,s_) for n_,s_ in chs if s_.index.min()<=w0 and s_.index.max()>=trm]
        if not use: continue
        tr_d=med([ch_trough(s_,w0,w1,0.12,1,4) for n_,s_ in use]); ends=tr_d if tr_d is not None else w1
        pk_d=med([ch_peak(s_,w0,ends,0.01,1) for n_,s_ in use])
        a,_=hit(pk_d,pk_off,'Q'); b,_=hit(tr_d,tr_off,'Q'); hp+=a; ht+=b; nn+=1
P(f'   Euro area, Spain, France, quarterly GDP and employment   peak {hp}/{nn}   trough {ht}/{nn}')
E='/home/claude/lab/esri'
LEV=['industrial_production','producer_goods_shipments','durable_consumer_goods_shipments',
     'labor_input','investment_goods_shipments','operating_profits','effective_job_offer_rate','exports_volume']
jc=[(n,load(f'{E}/JPN_{n}.csv')) for n in LEV]
di=hist_di(jc,5); dip=di+1.0
jp=jt=jn=0
for pk,tr in JP_M:
    if ts(pk)<pd.Timestamp('1976-01-01'): continue
    w0=ts(pk)-pd.DateOffset(months=12); w1=ts(tr)+pd.DateOffset(months=12)
    t=ch_trough(dip,w0,w1,0.20,5,12,abstain=False,where='last'); ends=t if t is not None else w1
    p=di_peak_first(di,w0,ends,45.,4)
    if p is None: p=di_dates_censored(di,w0,ends,45.,1,1)['peak']
    a,_=hit(p,pk,'M'); b,_=hit(t,tr,'M'); jp+=a; jt+=b; jn+=1
P(f'   Japan, ESRI\'s own eight components and its own diffusion rule   peak {jp}/{jn}   trough {jt}/{jn}')
P(f'   combined   peak {us["hp"]+hp+jp}/{12+nn+jn}   trough {us["ht"]+ht+jt}/{12+nn+jn}')

P('')
P('='*92)
P('TABLE 4  Speed: when a date can be published, United States')
P('='*92)
NB={'1991-03':('1992-12',21),'2001-11':('2003-07',20),'2009-06':('2010-09',15),'2020-04':('2021-07',15)}
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
P(f'{"NBER trough":12s} {"provisional":12s} {"published":10s} {"lag":>4s}   {"final":10s} {"published":10s} {"lag":>4s}   {"NBER said":10s} {"lag":>4s}')
lp=[];lf=[];prev=None
for pk,tr in US_M:
    if tr<'1969': continue
    w0=ts(pk)-pd.DateOffset(months=12)
    r=two_stage(chs,w0,ts(tr),after=prev); prev=ts(tr)
    f=lambda d: d.strftime('%Y-%m') if d is not None else '   --  '
    a=md(r['provisional_at'],ts(tr)) if r['provisional_at'] is not None else None
    b=md(r['final_at'],ts(tr)) if r['final_at'] is not None else None
    nb,nl=NB.get(tr,('',None))
    if a is not None: lp.append(a)
    if b is not None: lf.append(b)
    P(f"{tr:12s} {f(r['provisional_date']):12s} {f(r['provisional_at']):10s} {str(a):>4s}   {f(r['final_date']):10s} {f(r['final_at']):10s} {str(b):>4s}   {nb:10s} {str(nl):>4s}")
P('')
P('='*92)
P('TABLE 5  The cross-channel spread as a calibrated confidence measure')
P('='*92)
rows=[]
for c in ALL:
    cfg=PANELS[c]; ch2=[(nm,s2) for nm,s2 in channels(c) if nm not in bench.SKIP]
    for _e in cfg['chrono']:
        pk_,tr_,fq=ep3(_e,cfg['freq'])
        pkm=ts(pk_) if fq=='M' else q2m(pk_); trm=ts(tr_) if fq=='M' else q2m(tr_)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s2) for nm,s2 in ch2 if s2.index.min()<=w0 and s2.index.max()>=trm]
        if len(use)<2: continue
        d=date_any(c,use,w0,w1,**K)
        a,_=hit(d['peak'],pk_,fq); b,_=hit(d['trough'],tr_,fq)
        rows.append((max(d['spread_peak'] or 0,d['spread_trough'] or 0), a and b))
P(f'{"spread of the channel dates":32s} {"episodes":>9s} {"both ends right":>16s}')
for lo,hi,lab in [(0,6,'tight - 6 months or less'),(7,20,'moderate - 7 to 20 months'),(21,999,'wide - more than 20 months')]:
    g=[r for r in rows if lo<=r[0]<=hi]
    if g: P(f'{lab:32s} {len(g):9d} {sum(1 for x in g if x[1]):9d}/{len(g):<4d} ({100*sum(1 for x in g if x[1])/len(g):.0f}%)')
P('')
P(f'   mean lag to a provisional date {np.mean(lp):.1f} months; to the final date {np.mean(lf):.1f};'
  f' the NBER announced the four it dated at 21, 20, 15 and 15.')
open('/home/claude/lab/results2.out','w').write('\n'.join(L))
