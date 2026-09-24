"""Taiwan, held out: an eleventh official chronology, and a second controlled version of
the Korean experiment.

The National Development Council of the Republic of China has set official reference dates
for fifteen business cycles since 1954.  It states its own concept - "Taiwan's
identification of the reference date of economic cycle is based on the concept of growth
cycles" - and its own evidence: "a set of representative economic indicators composed into
one reference series" drawn from "production, consumption, employment, trade, and
transaction", "compiled into a Diffusion Index that aids in the determination of the
reference date of economic cycle".

The committee's own object is public: the Council's composite coincident index and its
DETRENDED form, 景氣同時指標不含趨勢指數, monthly from January 1982, served through the
DGBAS macro statistics database.  So the South African experiment can be run again, on a
chronology nothing in the rule has seen, with the committee's own detrended object on one
side and a panel of the same economy's monthly indicators on the other.

Nothing about Taiwan entered any choice made in building the rule; the configuration is
the shipped one, unchanged.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
bench.SKIP=set(); bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
TW=[('1955-11','1956-09'),('1964-09','1966-01'),('1968-08','1969-10'),('1974-02','1975-02'),
    ('1980-01','1983-02'),('1984-05','1985-08'),('1989-05','1990-08'),('1995-02','1996-03'),
    ('1997-12','1998-12'),('2000-09','2001-09'),('2004-03','2005-02'),('2008-03','2009-02'),
    ('2011-02','2012-01'),('2014-10','2016-02'),('2022-01','2023-04')]
def col(f,c):
    d=pd.read_csv(f'/home/claude/lab/twn/TWN_{f}.csv',index_col=0,parse_dates=True)
    s=pd.to_numeric(d[c],errors='coerce').dropna()
    return s[s>0] if (s>0).all() else s
bci=pd.read_csv('/home/claude/lab/twn/TWN_bci.csv',index_col=0,parse_dates=True)
co   = pd.to_numeric(bci['景氣同時指標綜合指數(點)'],errors='coerce').dropna()
co_nt= pd.to_numeric(bci['景氣同時指標不含趨勢指數(點)'],errors='coerce').dropna()
CH=[('industrial production',col('ip','總指數')),
    ('manufacturing production',col('ip','製造業')),
    ('employment',col('labour','就業人數(千人)')),
    ('exports',col('trade','USD(百萬美元) / 出口')),
    ('real earnings',col('earnings','工業及服務業')),
    ('tax revenue',col('tax','總計'))]
for nm,s in CH: print(f'   channel {nm:26s} {s.index.min().date()}..{s.index.max().date()}  n={len(s)}')
print(f'   NDC coincident index          {co.index.min().date()}..{co.index.max().date()}')
def rtt(s,lam=500000.0):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]
    t=pd.Series(hp_filter(y.values,lam),index=y.index)
    return np.exp(y-t)*100.0
co_c=rtt(co)
def run(mode):
    hp_=ht=0; ep=[]; et=[]; rows=[]; n=0
    for pk_off,tr_off in TW:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        src = co if mode in ('committee object','committee object, level clauses') else (
              co_nt if mode=="committee's own detrended index" else CH[0][1])
        if mode=='panel':
            use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: continue
        elif src.index.min()>w0 or src.index.max()<trm: continue
        n+=1
        if mode=='committee object':
            tr=ch_trough(co_c,w0,w1,0.0,3,12,abstain=False)
            _u=ch_trough(co_c,w0,w1,0.0,3,12,abstain=False,refine=False)
            pk=ch_peak(co_c,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        elif mode=="committee's own detrended index":
            tr=ch_trough(co_nt,w0,w1,0.0,3,12,abstain=False)
            _u=ch_trough(co_nt,w0,w1,0.0,3,12,abstain=False,refine=False)
            pk=ch_peak(co_nt,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        elif mode=='committee object, level clauses':
            tr=ch_trough(co,w0,w1,0.12,3,12,abstain=False)
            pk=ch_peak(co,w0,tr if tr is not None else w1,0.01,3,abstain=False)
        else:
            b=date_any('Taiwan',use,w0,w1,min_depth=1e9,
                       **{k:v for k,v in K.items() if k!='min_depth'})
            pk,tr=b['peak'],b['trough']
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b2
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    return hp_,ht,n,(np.mean(ep) if ep else float('nan')),(np.mean(et) if et else float('nan')),rows
print()
print(f'{"route":46s} {"peaks":>8s} {"troughs":>8s}  {"MAD p":>6s} {"MAD t":>6s}')
res={}
for m in ("committee's own detrended index",'committee object','committee object, level clauses','panel'):
    r=run(m); res[m]=r
    print(f'{m:46s} {r[0]:3d}/{r[2]:<3d} {r[1]:4d}/{r[2]:<3d}  {r[3]:6.2f} {r[4]:6.2f}')
print()
print("per episode, the committee's own detrended index:")
for x in res["committee's own detrended index"][5]:
    print(f'   peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
print()
print('per episode, the panel:')
for x in res['panel'][5]:
    print(f'   peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')

print()
print('DIAGNOSTIC: the committee detrended index at other lookbacks (shipped averages 9/12/15)')
for L in (9,12,15,18,24,36):
    hp_=ht=0; n=0
    for pk_off,tr_off in TW:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if co_nt.index.min()>w0 or co_nt.index.max()<trm: continue
        n+=1
        tr=ch_trough(co_nt,w0,w1,0.0,3,L,abstain=False)
        _u=ch_trough(co_nt,w0,w1,0.0,3,L,abstain=False,refine=False)
        pk=ch_peak(co_nt,w0,_u if _u is not None else w1,0.0,3,abstain=False,refine=False)
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b2
    print(f'   L={L:2d}: peaks {hp_}/{n}  troughs {ht}/{n}')
print()
print('DIAGNOSTIC: the diffusion route on the Taiwanese panel')
print('   (the Council also names a diffusion index, so the branch is asked)')
hp_=ht=0; n=0
for pk_off,tr_off in TW:
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in CH if s.index.min()<=w0 and s.index.max()>=trm]
    if len(use)<4: continue
    n+=1
    di=hist_di(use,3)
    tr=ch_trough(di,w0,w1,0.30,3,12,abstain=False,where='last')
    pk=ch_peak(di,w0,tr if tr is not None else w1,0.30,3,abstain=False,where='last')
    a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
    hp_+=a; ht+=b2
print(f'   diffusion route: peaks {hp_}/{n}  troughs {ht}/{n}')
print()
print('DIAGNOSTIC: the committee detrended index, band sensitivity')
for bt,bp in [(0.0,0.0),(0.12,0.01),(0.05,0.05)]:
    hp_=ht=0; n=0
    for pk_off,tr_off in TW:
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if co_nt.index.min()>w0 or co_nt.index.max()<trm: continue
        n+=1
        tr=ch_trough(co_nt,w0,w1,bt,3,12,abstain=False)
        pk=ch_peak(co_nt,w0,tr if tr is not None else w1,bp,3,abstain=False)
        a,e1=hit(pk,pk_off,'M'); b2,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b2
    print(f'   bands {bt}/{bp}: peaks {hp_}/{n}  troughs {ht}/{n}')
