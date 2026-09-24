"""Canonical benchmark for the Bristow Rule.

One module: panel definitions, the rule with every parameter exposed, and the
scoring harness against the nine official chronologies.  Nothing here reads an
official date except the scorer.
"""
import sys, os, glob, math
sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np

KEI='/home/claude/lab/kei'
LAB='/home/claude/lab'
A20='/home/claude/a20'
FRED='/home/claude/archive/data/fred'
EST='/home/claude/lab/estat'
ESRI='/home/claude/lab/esri'
SPLICED='/home/claude/lab/spliced'
NBERM='/home/claude/lab/nber/data'
INSEE='/home/claude/lab/insee'

# ----------------------------------------------------------------- loading
def load(path):
    d=pd.read_csv(path); d.columns=['d','v']
    d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    s=d.dropna().set_index('d')['v'].astype(float)
    s=s[~s.index.duplicated(keep='last')].sort_index()
    return s

def pro(path, kind='level'):
    """Return a pro-cyclical, strictly positive series."""
    s=load(path)
    if kind=='rate':            # unemployment rate in percent -> 100 - u
        return 100.0-s
    if kind=='balance':         # survey balance in percentage points -> shifted positive
        return s+100.0
    return s

# ----------------------------------------------------------------- chronologies
def ts(s): return pd.Timestamp(s+'-01')
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def qtr(d): return (d.year,(d.month-1)//3+1)
def qdiff(a,b): return (a[0]-b[0])*4+(a[1]-b[1])
def q2m(q): y,qq=q; return pd.Timestamp(year=y,month=2+3*(qq-1),day=1)

US_M=[('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
      ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
      ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
# The NBER's own interwar chronology, all five contractions its monthly panel reaches.
# The first three were added after the configuration was fixed by leave-one-chronology-out
# on the other eighty, so they are a held-out test rather than part of the calibration.
USIW_M=[('1920-01','1921-07'),('1923-05','1924-07'),('1926-10','1927-11'),
        ('1929-08','1933-03'),('1937-05','1938-06')]
CA_M=[('1929-04','1933-02'),('1937-11','1938-06'),('1947-08','1948-03'),('1951-04','1951-12'),
      ('1953-07','1954-07'),('1957-03','1958-01'),('1960-03','1961-03'),('1974-10','1975-03'),
      ('1981-06','1982-10'),('1990-03','1992-05'),('2008-10','2009-05'),('2020-02','2020-04')]
JP_M=[('1951-06','1951-10'),('1954-01','1954-11'),('1957-06','1958-06'),('1961-12','1962-10'),
      ('1964-10','1965-10'),('1970-07','1971-12'),('1973-11','1975-03'),('1977-01','1977-10'),
      ('1980-02','1983-02'),('1985-06','1986-11'),('1991-02','1993-10'),('1997-05','1999-01'),
      ('2000-11','2002-01'),('2008-02','2009-03'),('2012-03','2012-11'),('2018-10','2020-05')]
# Statistics Korea, "최근 경기순환기의 기준순환일 설정", table 우리나라 기준순환일 및 국면지속기간:
# eleven completed contractions, cycles 1-11.
KR_M=[('1974-02','1975-06'),('1979-02','1980-09'),('1984-02','1985-09'),('1988-01','1989-07'),
      ('1992-01','1993-01'),('1996-03','1998-08'),('2000-08','2001-07'),('2002-12','2005-04'),
      ('2008-01','2009-02'),('2011-08','2013-03'),('2017-09','2020-05')]
BR_M=[('1980-10','1983-02'),('1987-02','1988-10'),('1989-06','1991-12'),('1994-12','1995-09'),
      ('1997-10','1999-02'),('2000-12','2001-09'),('2002-10','2003-06'),('2008-07','2009-01')]
EZ_Q=[((1974,3),(1975,1)),((1980,1),(1982,3)),((1992,1),(1993,3)),((2008,1),(2009,2)),
      ((2011,3),(2013,1)),((2019,4),(2020,2))]
ES_Q=[((1974,4),(1975,2)),((1978,3),(1979,2)),((1992,1),(1993,3)),((2008,2),(2009,4)),
      ((2010,4),(2013,2)),((2019,4),(2020,2))]
FR_Q=[((1974,3),(1975,3)),((1980,1),(1980,4)),((1992,1),(1993,1)),((2008,1),(2009,2)),
      ((2019,4),(2020,2))]
BR_Q=[((2014,2),(2016,4)),((2019,4),(2020,2))]
# CODACE dates the early cycles monthly and the recent ones quarterly; one country,
# one panel, with the frequency carried on each episode.
BR_ALL=[(p,t,'M') for p,t in BR_M]+[(p,t,'Q') for p,t in BR_Q]

# ----------------------------------------------------------------- panels
def P(*items): return [x for x in items if x is not None]
def ex(path, kind='level', name=None):
    return (name or os.path.basename(path), path, kind) if os.path.exists(path) else None

KEI_CH=[('PRVM_BTE','industrial production','level'),
        ('PRVM_C','manufacturing production','level'),
        ('PRVM_F','construction production','level'),
        ('TOVM_G47','retail volume','level'),
        ('EMP__T','employment','level'),
        ('TOCAPA_G45','car registrations','level'),
        ('UNEMP__T','unemployment','rate'),
        ('EX__T','exports','nominal'),
        ('IM__T','imports','nominal')]

EST_CH=[('ip_capital','capital goods production'),
        ('ip_intermed','intermediate goods production'),
        ('ip_durable','consumer durables production'),
        ('construction','construction output'),
        ('services','services turnover')]

def estat(geo, keep=('ip_capital','ip_intermed','ip_durable','construction')):
    out=[]
    for f,nm in EST_CH:
        if f not in keep: continue
        p=f'{EST}/{geo}_{f}.csv'
        if os.path.exists(p): out.append((nm,p,'level'))
    return out

ESRI_CH=[('industrial_production','ESRI industrial production'),
         ('producer_goods_shipments','producer goods shipments'),
         ('durable_consumer_goods_shipments','durable consumer goods shipments'),
         ('labor_input','labor input'),
         ('investment_goods_shipments','investment goods shipments'),
         ('operating_profits','operating profits'),
         ('effective_job_offer_rate','effective job offer rate'),
         ('exports_volume','exports volume')]

def esri():
    """The eight level components of the Cabinet Office's coincident index, 1975-."""
    out=[]
    for f,nm in ESRI_CH:
        p=f'{ESRI}/JPN_{f}.csv'
        if os.path.exists(p): out.append((nm,p,'level'))
    return out

IMFPI='/home/claude/lab/imf'
IMF_CH=[('IND_SA_IX','IMF industrial production'),
        ('IND_IX','IMF industrial production'),
        ('C_IX','IMF manufacturing production'),
        ('B_IX','IMF mining production'),
        ('D_IX','IMF utilities production'),
        ('F_IX','IMF construction production')]

def imf(area, keep=('IND_SA_IX','IND_IX')):
    """IMF Production Indexes (STA, dataflow PI 2.0.0).  IND_SA_IX preferred;
    IND_IX only if the seasonally adjusted form is absent."""
    out=[]; have=set()
    for f,nm in IMF_CH:
        if f not in keep: continue
        if nm in have: continue
        p=f'{IMFPI}/{area}_{f}.csv'
        if os.path.exists(p): out.append((nm,p,'level')); have.add(nm)
    return out

def kei(area, extra=(), skip=(), rs=False):
    """Every OECD Key Economic Indicator channel that exists for this economy."""
    out=[]
    for f,nm,kind in KEI_CH:
        if nm in skip: continue
        p=f'{KEI}/{area}_{f}.csv'
        if os.path.exists(p): out.append((nm,p,kind))
    if rs and os.path.exists(f'{KEI}/{area}_RS__T.csv'):
        out.append(('monthly reference GDP', f'{KEI}/{area}_RS__T.csv','level'))
    return out+[x for x in extra if x]

US_NAT=[ex(f'{FRED}/INDPRO.csv',name='industrial production (Federal Reserve)'),
        ex(f'{FRED}/PAYEMS.csv',name='payroll employment'),
        ex(f'{A20}/CE16OV.csv',name='household employment'),
        ex(f'{A20}/W875RX1.csv',name='real income less transfers'),
        ex(f'{LAB}/cand/DPCERA3M086SBEA.csv',name='real consumption'),
        ex(f'{A20}/CMRMTSPL.csv',name='real manufacturing and trade sales')]

PANELS={
 'United States': dict(chrono=US_M, freq='M', src='NBER',
    ch=kei('USA', extra=US_NAT, skip={'unemployment','industrial production',
                                       'manufacturing production','employment'})+
       [ex(f'{FRED}/UNRATE.csv','rate',name='unemployment')]),
 # The interwar panel is the NBER's own four coincident concepts for the period -
 # activity, sales, employment and income - taken from the NBER Macrohistory
 # database, the historical analogue of the six series the committee cites today.
 'United States (interwar)': dict(chrono=USIW_M, freq='M', src='NBER', ch=P(
    ex(f'{FRED}/INDPRO.csv',name='industrial production'),
    ex(f'{NBERM}/m01001.csv',name='business activity index'),
    ex(f'{NBERM}/m06002b.csv',name='department store sales'),
    ex(f'{NBERM}/m08010b.csv',name='manufacturing employment'),
    ex(f'{NBERM}/m08069b.csv',name='manufacturing payrolls'),
    ex('/home/claude/archive/data/robustness/M0892AUSM156SNBR.csv','rate',name='unemployment'))),
 'Canada': dict(chrono=CA_M, freq='M', src='C.D. Howe BCC',
    ch=[('industrial production',f'{KEI}/CANX_PRVM_BTE.csv','level'),
        ('manufacturing production',f'{KEI}/CANX_PRVM_C.csv','level'),
        ('durable manufacturing',f'{KEI}/CANX_DURABLE.csv','level')]+
       kei('CAN', rs=True, skip={'industrial production','manufacturing production'},
           extra=[ex(f'{KEI}/CAN_GDPM__T.csv',name='monthly GDP')])),
 'Japan': dict(chrono=JP_M, freq='M', src='ESRI',
    ch=[(nm,(f'{SPLICED}/JPN_ip.csv' if nm=='industrial production' else p_),k)
        for nm,p_,k in kei('JPN', rs=True)]+esri()),
 'Korea': dict(chrono=KR_M, freq='M', src='KOSTAT',
    ch=[(nm,{'industrial production':f'{SPLICED}/KOR_ip.csv',
             'manufacturing production':f'{SPLICED}/KOR_mfg.csv'}.get(nm,p_),k)
        for nm,p_,k in kei('KOR', rs=True)]),
 'Brazil': dict(chrono=BR_ALL, freq='M', src='CODACE',
    ch=kei('BRA', rs=True, extra=[ex(f'{LAB}/cand/BRA_IBCBR.csv',name='monthly GDP proxy')])),
 'Euro area': dict(chrono=EZ_Q, freq='Q', src='CEPR-EABCN',
    ch=kei('EAX')+estat('EA20')+[('unemployment',f'{KEI}/EA20_UNEMP__T.csv','rate')]+
       [(f'{a} production',f'{KEI}/{a}_PRVM_BTE.csv','level')
        for a in ('DEU','FRA','ITA','NLD','BEL','ESP')
        if os.path.exists(f'{KEI}/{a}_PRVM_BTE.csv')]+
       [(f'{a} retail',f'{KEI}/{a}_TOVM_G47.csv','level')
        for a in ('DEU','BEL','FIN','AUT')
        if os.path.exists(f'{KEI}/{a}_TOVM_G47.csv')]),
 'Spain': dict(chrono=ES_Q, freq='Q', src='SBCDC (AEE)',
    ch=[(nm,(f'{SPLICED}/ESP_ip.csv' if nm=='industrial production' else p_),k)
        for nm,p_,k in kei('ESP', rs=True)]+estat('ES')),
 # INSEE's monthly household consumption of goods in chained volumes (1980-) is the
 # real-sales concept the French panel otherwise lacks; the OECD publishes no retail
 # volume for France before 1975.
 'France': dict(chrono=FR_Q, freq='Q', src='CDCEF (AFSE)',
    ch=kei('FRA', rs=True)+estat('FR')+P(ex(f'{INSEE}/FR_conso_biens.csv',name='real consumption'))),
}

_cache={}; KIND={}
def channels(country):
    if country in _cache: return _cache[country]
    out=[]; kk={}
    for nm,path,kind in PANELS[country]['ch']:
        try:
            out.append((nm, pro(path,kind))); kk[nm]=kind
        except Exception as e: print(f'  ! {country} {nm}: {e}')
    _cache[country]=out; KIND[country]=kk
    return out

def quantity(country, chs=None):
    """The volume channels: what an aggregate activity index may be built from.
    Rates carry no quantity information and nominal series carry price movements."""
    chs = chs if chs is not None else channels(country)
    kk = KIND.get(country, {})
    return [(nm,s) for nm,s in chs if kk.get(nm,'level')=='level']

# ----------------------------------------------------------------- the rule
_MA={}
def ma(x, n):
    # Every cache below keys on id(), the object's memory address, and therefore
    # also stores the object itself.  Holding the reference keeps the address alive
    # for as long as the entry exists; without it a temporary series can be freed
    # and a later one allocated at the same address, so the cache would answer a
    # question it was never asked and the result would depend on the order in which
    # the caller happened to build its intermediates.
    k=(id(x),n); e=_MA.get(k)
    if e is not None and e[0] is x: return e[1]
    r=x.rolling(n).mean(); _MA[k]=(x,r); return r

HORIZONS=(-3,0,3)    # months either side of L over which the statistic is averaged

_DEV={}
def dev(x, L=12, n=3):
    """Generalized deviation statistic, percent below the trailing rolling max.

    The twelve-month lookback was always an arbitrary choice, and a turning point a
    twelve-month window sees clearly can be faint to a nine- or fifteen-month one.
    The statistic is therefore averaged over three lookbacks, a quarter either side
    of L.  Paper 1's own D is the single-horizon member of this family; averaging
    costs no hits and cuts the mean trough error from 1.70 months to 1.65.  Chosen
    out of sample: leaving each chronology out in turn, the other eight pick this
    spread eight times in nine."""
    k=(id(x),L,n); e=_DEV.get(k)
    if e is not None and e[0] is x: return e[1]
    m=ma(x,n); parts=[]
    for h in HORIZONS:
        w=L+h
        if w<2: continue
        mx=m.shift(1).rolling(w).max()
        parts.append((mx-m)/mx*100.0)
    r=parts[0] if len(parts)==1 else pd.concat(parts,axis=1).mean(axis=1)
    _DEV[k]=(x,r); return r

_TA={}
def prep(level, n=3, tadj=False, win=120, minp=60):
    if not tadj: return level
    k=(id(level), n, win, minp); e=_TA.get(k)
    if e is not None and e[0] is level: return e[1]
    r=trend_adjust(level, win, minp, n); _TA[k]=(level,r); return r

PLATEAU_T='mid'      # where in the flat bottom the trough sits: 'mid' or 'last'
PLATEAU_P='mid'      # where in the flat top the peak sits (same construction)

def _plateau_pick(on, where):
    """Which month of the within-band run is the turning point.

    'last' is the reading ESRI publishes for a diffusion index and the one the rule
    used through version 12.  It cannot be earlier than the extreme itself, so on a
    level it is biased late - by half a month at troughs and half at peaks on this
    sample.  'mid' takes the centre of the flat region instead, which is unbiased by
    construction and lets the band be set wide enough to find the whole plateau.
    Chosen out of sample: leaving each chronology out in turn, the other eight pick
    the centre with a twelve-percent band eight times in nine.
    """
    if len(on)==0: return None
    return on.index[-1] if where=='last' else on.index[len(on)//2]

def ch_trough(level, w0, w1, band=0.02, n=3, L=12, tadj=False, win=120, minp=60, abstain=None,
              where=None):
    _ab = ABSTAIN if abstain is None else abstain
    where = PLATEAU_T if where is None else where
    level=prep(level,n,tadj,win,minp)
    d=dev(level,L,n)[w0:w1].dropna()
    if len(d)==0: return None
    d_peak=d.idxmax()
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return d_peak
    lo=float(m.min()); i=m.idxmin()
    # a channel still at its low in the last month of the window has not turned
    if _ab and i==m.index[-1]: return None
    hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
    amp=max(hi-lo,1e-9)
    on=m[m<=lo+band*amp]
    p=_plateau_pick(on,where)
    return max(d_peak,p) if p is not None else d_peak

ABSTAIN=True
def ch_peak(level, w0, w1, band=0.02, n=3, tadj=False, win=120, minp=60, abstain=None,
            where=None):
    _ab = ABSTAIN if abstain is None else abstain
    where = PLATEAU_P if where is None else where
    level=prep(level,n,tadj,win,minp)
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    # a channel whose high is at either end of the search window has not turned
    # inside it: it carries no information about where the peak is, so it abstains.
    if _ab and (i==m.index[0] or i==m.index[-1]): return None
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp=max(hi-lo,1e-9)
    on=m[m>=hi-band*amp]
    p=_plateau_pick(on,where)
    return p if p is not None else i

def med(dates, q=0.5):
    """Order statistic of the channel dates.  q=0.5 is the median; a higher q dates
    the turn to the later channels, which is what a committee does when it waits for
    employment to confirm output.

    With an even number of channel dates the median falls between two months and
    the rule has to say which.  It takes the LATER of the two, for the same reason
    a higher q is the direction a committee leans: a turn is called once the
    slower-moving channels confirm it, not on the first half of them.  The choice
    is made by ceiling rather than rounding, so it is the same at every q and does
    not alternate with the parity of the panel.  Chosen out of sample: leaving each
    chronology out in turn, the other eight pick the later month nine times in
    nine."""
    ds=sorted(d for d in dates if d is not None)
    if not ds: return None
    if len(ds)==1: return ds[0]
    i=int(math.ceil(q*(len(ds)-1)-1e-9))
    return ds[min(max(i,0),len(ds)-1)]

def spread_m(dates):
    ds=sorted(d for d in dates if d is not None)
    return None if len(ds)<2 else md(ds[-1],ds[0])

# ----------------------------------------------------------------- composite detector
_CD={}
def composite_dev(chs, L=12, n=3, minch=2, q=0.5):
    _k=(tuple(sorted((nm,id(s)) for nm,s in chs)),L,n,minch,q); e=_CD.get(_k)
    if e is not None and all(a is b for a,b in zip(e[0],[s for _,s in chs])):
        return e[1]
    r=_composite_dev(chs,L,n,minch,q); _CD[_k]=([s for _,s in chs],r); return r

def _composite_dev(chs, L=12, n=3, minch=2, q=0.5):
    if not chs: return pd.Series(dtype=float)
    """Cross-channel order statistic of the deviation statistic.  A depth-and-breadth
    detector: at q=0.5 it rises only when half the covered channels are that far down;
    a lower q requires more channels to agree, a higher q fewer."""
    D=pd.concat([dev(s,L,n).rename(nm) for nm,s in chs], axis=1)
    cnt=D.notna().sum(axis=1)
    out=D.quantile(q, axis=1, numeric_only=True) if hasattr(D,'quantile') else D.median(axis=1)
    return out.where(cnt>=minch)

def episodes(stat, thr=2.0, gap=0):
    runs, cur = [], []
    for d,v in stat.dropna().items():
        if v>=thr: cur.append(d)
        elif cur: runs.append(cur); cur=[]
    if cur: runs.append(cur)
    if gap and len(runs)>1:                     # merge runs separated by < gap months
        merged=[runs[0]]
        for r in runs[1:]:
            if md(r[0],merged[-1][-1])<=gap: merged[-1]=merged[-1]+r
            else: merged.append(r)
        runs=merged
    return runs

def depth_pct(chs, w0, w1, n=3):
    """Peak-to-trough fall of the cross-channel median activity index, percent."""
    ds=[]
    for nm,s in chs:
        m=s.rolling(n).mean()[w0:w1].dropna()
        if len(m)<4: continue
        i=m.idxmin()
        hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
        ds.append(100.0*(float(m.min())-hi)/hi)
    if not ds: return None
    ds=sorted(ds); k=len(ds)
    return ds[(k-1)//2] if k%2==0 else ds[k//2]

def date_episode(chs, w0, w1, band_t=0.02, band_p=0.02, n=3, L=12,
                 peak_cap=12, drop_at_peak=(), procyc_only_peak=False):
    """Both ends of one episode.  peak_cap bounds the peak search to `peak_cap`
    months before w1p (the start of the drawdown episode)."""
    tr = med([ch_trough(s,w0,w1,band_t,n,L) for nm,s in chs])
    ends = tr if tr is not None else w1
    pk_ch=[(nm,s) for nm,s in chs if nm not in drop_at_peak]
    if not pk_ch: pk_ch=chs
    p0 = w0
    pk = med([ch_peak(s,p0,ends,band_p,n) for nm,s in pk_ch])
    return dict(peak=pk, trough=tr,
                spread_t=spread_m([ch_trough(s,w0,w1,band_t,n,L) for nm,s in chs]),
                spread_p=spread_m([ch_peak(s,p0,ends,band_p,n) for nm,s in pk_ch]))

# ----------------------------------------------------------------- scoring
def ep3(e, default='M'):
    """Chronology entry -> (peak, trough, frequency of the official date)."""
    return (e[0], e[1], e[2] if len(e)>2 else default)

def hit(pred, off, freq, tol_m=3, tol_q=1):
    if pred is None: return False, None
    if freq=='M':
        e=md(pred,ts(off)); return abs(e)<=tol_m, e
    e=qdiff(qtr(pred),off); return abs(e)<=tol_q, e

def run_country(country, thr=2.0, band_t=0.02, band_p=0.02, n=3, L=12,
                peak_cap=12, tail=12, lead=12, drop_at_peak=(), verbose=False,
                min_depth=2.0, minch=2, gap=0, tadj=False, win=120, minp=60):
    """Bracketed scoring: the window is the official episode widened by lead/tail.
    Dates come from the rule; only the window uses official information."""
    cfg=PANELS[country]; chs=channels(country); freq=cfg['freq']
    rows=[]
    for _e in cfg['chrono']:
        pk_off, tr_off, freq = ep3(_e, cfg['freq'])
        pkm = ts(pk_off) if freq=='M' else q2m(pk_off)
        trm = ts(tr_off) if freq=='M' else q2m(tr_off)
        w0 = pkm - pd.DateOffset(months=lead)
        w1 = trm + pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)==0:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,
                             pk=None,tr=None,ep=None,et=None,hp=False,ht=False,depth=None)); continue
        # peak search may not run back past peak_cap months before the trough-window start
        p0 = max(w0, pkm - pd.DateOffset(months=lead)) if peak_cap is None else None
        d = date_episode_capped(use, w0, w1, pkm, trm, band_t, band_p, n, L, peak_cap,
                                drop_at_peak, tadj, win, minp, qt, qp)
        dep = depth_pct([(nm,prep(s,n,tadj,win,minp)) for nm,s in use], w0, w1, n)
        hp,ep = hit(d['peak'], pk_off, freq)
        ht,et = hit(d['trough'], tr_off, freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=d['peak'],tr=d['trough'],ep=ep,et=et,hp=hp,ht=ht,depth=dep,
                         sp=d['spread_p'],st=d['spread_t']))
    return rows

def date_episode_capped(chs, w0, w1, pkm, trm, band_t, band_p, n, L, peak_cap, drop_at_peak,
                        tadj=False, win=120, minp=60, qt=0.5, qp=0.5):
    dt=[ch_trough(s,w0,w1,band_t,n,L,tadj,win,minp) for nm,s in chs]
    tr = med(dt,qt)
    ends = tr if tr is not None else w1
    pk_ch=[(nm,s) for nm,s in chs if nm not in drop_at_peak] or chs
    comp=composite_dev([(nm,prep(s,n,tadj,win,minp)) for nm,s in chs],L,n,1)[w0:ends].dropna()
    cross=None
    for d,v in comp.items():
        if v>=2.0: cross=d; break
    p_start = w0 if (cross is None or peak_cap is None) else max(w0, cross - pd.DateOffset(months=peak_cap))
    dp=[ch_peak(s,p_start,ends,band_p,n,tadj,win,minp) for nm,s in pk_ch]
    pk = med(dp,qp)
    return dict(peak=pk, trough=tr, spread_t=spread_m(dt), spread_p=spread_m(dp))

def score(rows, label='', show=True):
    n=len([r for r in rows if r['nch']>0])
    hp=sum(r['hp'] for r in rows); ht=sum(r['ht'] for r in rows)
    ep=[abs(r['ep']) for r in rows if r['ep'] is not None]
    et=[abs(r['et']) for r in rows if r['et'] is not None]
    mp=np.mean(ep) if ep else float('nan'); mt=np.mean(et) if et else float('nan')
    if show: print(f'{label:28s} peak {hp:3d}/{n:<3d} MAD {mp:5.2f}   trough {ht:3d}/{n:<3d} MAD {mt:5.2f}')
    return dict(n=n,hp=hp,ht=ht,mp=mp,mt=mt)

ALL=list(PANELS)
def run_all(show_country=True, **kw):
    allrows=[]
    for c in ALL:
        rows=run_country(c, **kw); allrows+=rows
        if show_country: score(rows,'   '+c)
    return allrows, score(allrows,'TOTAL' if show_country else '')

# ----------------------------------------------------------------- trend adjustment
def trend_adjust(x, win=120, minp=60, n=3):
    """Subtract the economy's own trailing growth from the log level.

    g(t) = median monthly log change over the previous `win` months, computed only
    from information dated before t.  The adjusted series is
        yhat(t) = y(t) - cumsum(g(t))
    so a series growing at its own trailing trend is flat in yhat, and the rolling
    maximum of yhat is the level the economy would have reached had trend continued.
    With g = 0 this reduces exactly to the untransformed rule.
    """
    y=np.log(x.rolling(n).mean().clip(lower=1e-9))
    d=y.diff()
    g=d.shift(1).rolling(win, min_periods=minp).median()
    g=g.fillna(0.0)
    return np.exp(y - g.cumsum())

def dev_t(x, L=12, n=3, win=120, minp=60):
    z=trend_adjust(x, win, minp, n)
    mx=z.shift(1).rolling(L).max()
    return (mx-z)/mx*100.0

# ----------------------------------------------------------------- two-regime rule
def run_country2(country, band_t=0.02, band_p=0.02, n=3, L=12, peak_cap=12,
                 tail=12, lead=12, drop_at_peak=(), min_depth=2.0,
                 win=120, minp=60, mode='auto', qt=0.5, qp=0.5):
    """The rule with an automatic regime switch.

    Depth of the episode is measured on the level.  If activity actually fell by
    at least `min_depth` percent the episode is a classical contraction and both
    ends are dated on the level.  If it did not, the episode is a growth-cycle
    event: the same rule is then applied to the trend-adjusted series, where the
    reference is the path the economy would have followed at its own trailing
    growth rate rather than its previous level.
    """
    cfg=PANELS[country]; chs=channels(country); freq=cfg['freq']
    rows=[]
    for _e in cfg['chrono']:
        pk_off, tr_off, freq = ep3(_e, cfg['freq'])
        pkm = ts(pk_off) if freq=='M' else q2m(pk_off)
        trm = ts(tr_off) if freq=='M' else q2m(tr_off)
        w0 = pkm - pd.DateOffset(months=lead); w1 = trm + pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm and nm not in SKIP]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,regime='no data',
                             sp=None,st=None)); continue
        dep_l = depth_q(country, use, w0, w1, n)
        if mode=='level': tadj=False
        elif mode=='trend': tadj=True
        else: tadj = (dep_l is None) or (dep_l > -abs(min_depth))
        d = date_episode_capped(use, w0, w1, pkm, trm, band_t, band_p, n, L, peak_cap,
                                drop_at_peak, tadj, win, minp, qt, qp)
        hp,ep = hit(d['peak'], pk_off, freq); ht,et = hit(d['trough'], tr_off, freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=d['peak'],tr=d['trough'],ep=ep,et=et,hp=hp,ht=ht,depth=dep_l,
                         regime='growth cycle' if tadj else 'classical',
                         sp=d['spread_p'],st=d['spread_t']))
    return rows

def run_all2(show_country=True, **kw):
    allrows=[]
    for c in ALL:
        rows=run_country2(c,**kw); allrows+=rows
        if show_country: score(rows,'   '+c)
    return allrows, score(allrows,'TOTAL' if show_country else '')

# ----------------------------------------------------------------- composite index
_CL={}
def composite_level(chs, n=1, standardize=False, minch=1, exclude=()):
    _k=(tuple(sorted((nm,id(s)) for nm,s in chs)),n,standardize,minch,tuple(sorted(exclude)))
    e=_CL.get(_k)
    if e is not None and all(a is b for a,b in zip(e[0],[s for _,s in chs])):
        return e[1]
    r=_composite_level(chs,n,standardize,minch,exclude)
    _CL[_k]=([s for _,s in chs],r); return r

def _composite_level(chs, n=1, standardize=False, minch=1, exclude=()):
    """Equal-weight coincident activity index from an unbalanced panel.

    Averages the month-on-month log changes of every channel available in both
    months, then chain-links.  Unbalanced starts therefore cost no history and
    introduce no jumps.  With standardize=True each channel's log change is first
    divided by its own standard deviation, which is the Stock-Watson weighting;
    with standardize=False the index is in log points of activity, so its
    peak-to-trough fall is an aggregate depth in percent.
    """
    use=[(nm,s) for nm,s in chs if nm not in exclude]
    if not use: return None
    D=pd.concat([np.log(s.rolling(n).mean().clip(lower=1e-9)).diff().rename(nm) for nm,s in use],axis=1)
    if standardize:
        D=D/D.std()
    cnt=D.notna().sum(axis=1)
    g=D.mean(axis=1, skipna=True).where(cnt>=minch)
    g=g[g.first_valid_index():]
    return np.exp(g.fillna(0.0).cumsum())*100.0

def maxdd(m):
    """Maximum drawdown of a level series, in percent, measured from the running
    maximum inside the window.  Unlike a peak-to-trough fall it does not depend on
    where the window happens to start."""
    if len(m)<4: return None
    run=m.cummax()
    return -float(((run-m)/run).max())*100.0

def depth_comp(chs, w0, w1, n=3, exclude=()):
    ci=composite_level(chs, 1, False, 1, exclude)
    if ci is None: return None
    m=ci.rolling(n).mean()[w0:w1].dropna()
    return maxdd(m)

def depth_q(country, use, w0, w1, n=3):
    """Depth of the episode: maximum drawdown of the equal-weight volume composite."""
    q=quantity(country, use)
    if not q: q=use
    return depth_comp(q, w0, w1, n)

# ----------------------------------------------------------------- diffusion form
from onset import bry_boschan

def phase_series(level, n=3):
    """+1 while the channel is in its own expansion, 0 while in its own contraction.
    Turning points from Bry-Boschan, the method ESRI itself uses on each component."""
    tp=bry_boschan(level, smooth=n)
    if not tp: return None
    idx=level.rolling(n,center=True).mean().dropna().index
    ph=pd.Series(np.nan, index=idx)
    for (d,k) in tp: ph[d] = 0.0 if k=='P' else 1.0
    ph=ph.ffill()
    first=tp[0]
    ph[:first[0]] = 1.0 if first[1]=='P' else 0.0
    return ph

_PH={}
def hist_di(chs, n=3):
    """ESRI's historical diffusion index: the share of coincident series that are in
    their own expansion phase, in percent."""
    cols=[]
    for nm,s in chs:
        k=(nm,id(s),n); e=_PH.get(k)
        if e is None or e[0] is not s:
            e=(s,phase_series(s,n)); _PH[k]=e
        p=e[1]
        if p is not None: cols.append(p.rename(nm))
    if not cols: return None
    P=pd.concat(cols,axis=1)
    cnt=P.notna().sum(axis=1)
    return (P.mean(axis=1,skipna=True)*100.0).where(cnt>=1)

def di_dates(di, w0, w1, line=50.0):
    """ESRI's own rule, which is the Bristow last-month-in-band clause with the band
    fixed at the 50-percent line: the peak is the last month the index stays above
    the line, the trough the last month it stays below it."""
    d=di[w0:w1].dropna()
    if len(d)<4: return dict(peak=None, trough=None)
    lo=d.idxmin()
    above=d[:lo][d[:lo]>=line]
    pk=above.index[-1] if len(above) else None
    below=d[lo:][d[lo:]<=line]
    tr=below.index[-1] if len(below) else None
    return dict(peak=pk, trough=tr)

def run_country_di(country, lead=12, tail=12, n=3, line=50.0, chs_filter=None):
    cfg=PANELS[country]; freq=cfg['freq']
    chs=channels(country)
    if chs_filter: chs=[(nm,s) for nm,s in chs if nm in chs_filter]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if len(use)<2:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        di=hist_di(use,n)
        d=di_dates(di,w0,w1,line) if di is not None else dict(peak=None,trough=None)
        hp,ep=hit(d['peak'],pk_off,freq); ht,et=hit(d['trough'],tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=d['peak'],tr=d['trough'],ep=ep,et=et,hp=hp,ht=ht,depth=None,sp=None,st=None))
    return rows

# ----------------------------------------------------------------- deviation form
def cyc_component(chs, trend=97, center=True, n=3, exclude=()):
    """The cyclical component of the composite coincident index: the index divided
    by its own trend, in percent.  This is the object Statistics Korea dates
    (동행종합지수 순환변동치) and the object a growth-cycle chronology refers to.
    center=False makes the trend one-sided, which is what a real-time user has."""
    ci=composite_level(chs,1,False,1,exclude)
    if ci is None: return None
    m=ci.rolling(n).mean()
    if center: tr=m.rolling(trend, center=True, min_periods=max(12,trend//3)).mean()
    else:      tr=m.rolling(trend, min_periods=max(12,trend//3)).mean()
    return (m/tr*100.0).dropna()

def bristow(level, w0, w1, band=0.02, n=1, L=12, end='trough'):
    """The rule itself, on whatever series it is given."""
    if end=='trough': return ch_trough(level,w0,w1,band,n,L)
    return ch_peak(level,w0,w1,band,n)

def run_country_dev(country, trend=97, center=True, band=0.02, lead=12, tail=12,
                    n=3, L=12, peak_cap=12):
    cfg=PANELS[country]; freq=cfg['freq']; chs=channels(country)
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        q=quantity(country,use)
        if len(q)<2:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        cy=cyc_component(q,trend,center,n)
        if cy is None or len(cy[w0:w1].dropna())<6:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        tr_d=bristow(cy,w0,w1,band,1,L,'trough')
        ends=tr_d if tr_d is not None else w1
        p0=max(w0, ends-pd.DateOffset(months=peak_cap+24))
        pk_d=bristow(cy,p0,ends,band,1,L,'peak')
        hp,ep=hit(pk_d,pk_off,freq); ht,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=hp,ht=ht,depth=None,sp=None,st=None))
    return rows

CLASSICAL=['United States','United States (interwar)','Canada','Brazil',
           'Euro area','Spain','France']
DEVIATION=['Japan','Korea']

def run_country_ci(country, band_t=0.02, band_p=0.02, n=3, L=12, peak_cap=12,
                   lead=12, tail=12, use_all=False):
    """Architecture B: build one composite activity index from the panel and date it,
    instead of dating every channel and taking the median date."""
    cfg=PANELS[country]; freq=cfg['freq']; chs=channels(country)
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        q=use if use_all else quantity(country,use)
        if not q:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        ci=composite_level(q,1,False,1)
        tr_d=ch_trough(ci,w0,w1,band_t,n,L)
        ends=tr_d if tr_d is not None else w1
        d=dev(ci,L,n)[w0:ends].dropna()
        cross=None
        for dt,v in d.items():
            if v>=2.0: cross=dt; break
        p0=w0 if (cross is None or peak_cap is None) else max(w0, cross-pd.DateOffset(months=peak_cap))
        pk_d=ch_peak(ci,p0,ends,band_p,n)
        hp,ep=hit(pk_d,pk_off,freq); ht,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=hp,ht=ht,depth=depth_comp(q,w0,w1,n),sp=None,st=None))
    return rows

# ----------------------------------------------------------------- noise-scaled band
_SD={}
def sigma(level, n=3, win=60):
    """Trailing standard deviation of the month-on-month change in the smoothed level.
    The natural yardstick for 'indistinguishable from the extreme'."""
    k=(id(level),n,win); e=_SD.get(k)
    if e is not None and e[0] is level: return e[1]
    r=ma(level,n).diff().rolling(win, min_periods=24).std()
    _SD[k]=(level,r); return r

def ch_peak_sd(level, w0, w1, kappa=1.0, n=3, win=60):
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return None
    sd=sigma(level,n,win)
    s=sd[:w0].dropna()
    s=float(s.iloc[-1]) if len(s) else float(sd[w0:w1].dropna().median() if len(sd[w0:w1].dropna()) else 0.0)
    if not np.isfinite(s) or s<=0: s=float(m.diff().std() or 1e-9)
    hi=float(m.max()); i=m.idxmax()
    on=m[m>=hi-kappa*s]
    return on.index[-1] if len(on) else i

def ch_trough_sd(level, w0, w1, kappa=1.0, n=3, L=12, win=60):
    d=dev(level,L,n)[w0:w1].dropna()
    if len(d)==0: return None
    d_peak=d.idxmax()
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return d_peak
    sd=sigma(level,n,win); s=sd[:w0].dropna()
    s=float(s.iloc[-1]) if len(s) else float(sd[w0:w1].dropna().median() if len(sd[w0:w1].dropna()) else 0.0)
    if not np.isfinite(s) or s<=0: s=float(m.diff().std() or 1e-9)
    lo=float(m.min())
    on=m[m<=lo+kappa*s]
    return max(d_peak, on.index[-1]) if len(on) else d_peak

def run_country_sd(country, kt=1.0, kp=1.0, n=3, L=12, peak_cap=18, lead=12, tail=12, win=60):
    cfg=PANELS[country]; freq=cfg['freq']; chs=channels(country)
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        dt=[ch_trough_sd(s,w0,w1,kt,n,L,win) for nm,s in use]
        tr_d=med(dt); ends=tr_d if tr_d is not None else w1
        comp=composite_dev(use,L,n,1)[w0:ends].dropna(); cross=None
        for d_,v in comp.items():
            if v>=2.0: cross=d_; break
        p0=w0 if (cross is None or peak_cap is None) else max(w0, cross-pd.DateOffset(months=peak_cap))
        dp=[ch_peak_sd(s,p0,ends,kp,n,win) for nm,s in use]
        pk_d=med(dp)
        hp,ep=hit(pk_d,pk_off,freq); ht,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=hp,ht=ht,depth=depth_q(country,use,w0,w1,n),
                         sp=spread_m(dp),st=spread_m(dt)))
    return rows

def ch_peak_m(level, w0, w1, band=0.02, n=3):
    """True mirror of the trough clause.  The trough clause measures the band as a
    fraction of the amplitude of the decline that is ending; the peak clause must
    therefore measure it as a fraction of the amplitude of the RISE that is ending,
    that is, from the low that precedes the high - not from the low that follows it."""
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmax()
    lo=float(m[:i].min())
    amp=max(hi-lo,1e-9)
    on=m[m>=hi-band*amp]
    return on.index[-1] if len(on) else i

def run_country_m(country, band_t=0.02, band_p=0.02, n=3, L=12, peak_cap=18,
                  lead=12, tail=12, peakfn=None):
    cfg=PANELS[country]; freq=cfg['freq']; chs=channels(country)
    pf=peakfn or ch_peak_m
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        dt=[ch_trough(s,w0,w1,band_t,n,L) for nm,s in use]
        tr_d=med(dt); ends=tr_d if tr_d is not None else w1
        comp=composite_dev(use,L,n,1)[w0:ends].dropna(); cross=None
        for d_,v in comp.items():
            if v>=2.0: cross=d_; break
        p0=w0 if (cross is None or peak_cap is None) else max(w0, cross-pd.DateOffset(months=peak_cap))
        dp=[pf(s,p0,ends,band_p,n) for nm,s in use]
        pk_d=med(dp)
        hp,ep=hit(pk_d,pk_off,freq); ht,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=hp,ht=ht,depth=depth_q(country,use,w0,w1,n),
                         sp=spread_m(dp),st=spread_m(dt)))
    return rows

# ----------------------------------------------------------------- channel ablation
SKIP=set()
SKIP_PEAK=set()
SKIP_TROUGH=set()
def _filter(chs):
    return [(nm,s) for nm,s in chs if nm not in SKIP] or chs

# ----------------------------------------------------------------- admissibility
def snr(level, w0, w1, n=3, win=60):
    """Amplitude of the channel's own swing inside the window, in units of its own
    trailing month-to-month noise.  A channel with no swing cannot date anything."""
    m=ma(level,n)[w0:w1].dropna()
    if len(m)<6: return 0.0
    sd=sigma(level,n,win); s=sd[:w0].dropna()
    s=float(s.iloc[-1]) if len(s) else float(m.diff().std() or np.nan)
    if not np.isfinite(s) or s<=0: return 0.0
    return float(m.max()-m.min())/s

def admissible(chs, w0, w1, tau=6.0, n=3, win=60, keep_min=2):
    ok=[(nm,s) for nm,s in chs if snr(s,w0,w1,n,win)>=tau]
    if len(ok)>=keep_min: return ok
    ranked=sorted(chs, key=lambda t: -snr(t[1],w0,w1,n,win))
    return ranked[:max(keep_min,len(ok))] or chs

def run_country3(country, band_t=0.02, band_p=0.05, n=3, L=12, peak_cap=18,
                 lead=12, tail=12, tau=6.0, win=60, keep_min=2):
    """The rule with a per-channel admissibility test: a channel votes on the date of
    an episode only if the episode moved it by more than tau times its own noise."""
    cfg=PANELS[country]; freq=cfg['freq']; chs=channels(country)
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        cov=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm and nm not in SKIP]
        if not cov:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,used=[])); continue
        use=admissible(cov,w0,w1,tau,n,win,keep_min)
        dt=[ch_trough(s,w0,w1,band_t,n,L) for nm,s in use]
        tr_d=med(dt); ends=tr_d if tr_d is not None else w1
        comp=composite_dev(use,L,n,1)[w0:ends].dropna(); cross=None
        for d_,v in comp.items():
            if v>=2.0: cross=d_; break
        p0=w0 if (cross is None or peak_cap is None) else max(w0, cross-pd.DateOffset(months=peak_cap))
        dp=[ch_peak(s,p0,ends,band_p,n) for nm,s in use]
        pk_d=med(dp)
        hp,ep=hit(pk_d,pk_off,freq); ht,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=hp,ht=ht,depth=depth_q(country,use,w0,w1,n),
                         sp=spread_m(dp),st=spread_m(dt),used=[nm for nm,_ in use]))
    return rows

# ----------------------------------------------------------------- standalone mode
def standalone(country, thr=2.0, band_t=0.01, band_p=0.03, n=3, L=12, peak_cap=12,
               tail=12, minch=2, gap=6, min_len=3, q=0.5):
    """Date every contraction the panel shows, using no official date anywhere.

    Episodes are the runs in which the cross-channel median deviation statistic is at
    or above `thr` percent.  Each episode is then dated at both ends by the rule.
    """
    chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    if not chs: return []
    comp=composite_dev(chs,L,n,minch,q)
    out=[]
    prev_tr=None
    for e in episodes(comp,thr,gap):
        if len(e)<min_len: continue
        w0=e[0]-pd.DateOffset(months=peak_cap); w1=e[-1]+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=e[-1]]
        if len(use)<1: continue
        dt=[ch_trough(s,e[0],w1,band_t,n,L) for nm,s in use]
        tr=med(dt); ends=tr if tr is not None else w1
        p0=w0 if prev_tr is None else max(w0, prev_tr+pd.DateOffset(months=1))
        dp=[ch_peak(s,p0,ends,band_p,n) for nm,s in use]
        pk=med(dp)
        if tr is None: continue
        prev_tr=tr
        out.append(dict(peak=pk, trough=tr, start=e[0], end=e[-1], nch=len(use),
                        depth=depth_q(country,use,p0,w1,n),
                        sp=spread_m(dp), st=spread_m(dt)))
    return out

def match(country, det, tol_m=3, tol_q=1, window=12):
    """Match detected episodes to the official chronology by nearest trough."""
    cfg=PANELS[country]; freq=cfg['freq']
    off=[]
    for _e in cfg['chrono']:
        pk,tr,fq=ep3(_e,cfg['freq'])
        off.append((pk,tr,fq,(ts(tr) if fq=='M' else q2m(tr))))
    rows=[]; used=set()
    for pk_off,tr_off,freq,trm in off:
        best=None
        for i,d in enumerate(det):
            if i in used or d['trough'] is None: continue
            k=abs(md(d['trough'],trm))
            if k<=window and (best is None or k<best[0]): best=(k,i,d)
        if best is None:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,nch=0,found=False)); continue
        used.add(best[1]); d=best[2]
        hp,ep=hit(d['peak'],pk_off,freq); ht,et=hit(d['trough'],tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,pk=d['peak'],tr=d['trough'],
                         ep=ep,et=et,hp=hp,ht=ht,nch=d['nch'],found=True,depth=d['depth']))
    extra=[d for i,d in enumerate(det) if i not in used]
    return rows, extra

# ----------------------------------------------------------------- HP trend
def hp_filter(y, lam=129600.0):
    """Two-sided Hodrick-Prescott trend, lambda = 129600 for monthly data
    (Ravn and Uhlig 2002).  Used only where the object being dated is itself a
    deviation from trend, as in Statistics Korea's 순환변동치."""
    y=np.asarray(y, dtype=float); n=len(y)
    if n<5: return y.copy()
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    I=sp.eye(n, format='csc')
    D=sp.diags([np.ones(n-2), -2*np.ones(n-2), np.ones(n-2)], [0,1,2], shape=(n-2,n), format='csc')
    return spsolve((I + lam*(D.T@D)).tocsc(), y)

STANDARDIZE=False
def cyc_hp(chs, lam=129600.0, n=3, exclude=(), standardize=None):
    st=STANDARDIZE if standardize is None else standardize
    ci=composite_level(chs,1,st,1,exclude)
    if ci is None: return None
    m=np.log(ma(ci,n).dropna())
    tr=hp_filter(m.values, lam)
    return pd.Series(np.exp(m.values-tr)*100.0, index=m.index)

def run_country_hp(country, lam=129600.0, band=0.02, lead=12, tail=12, n=3, L=12, peak_cap=24):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        q=quantity(country,use)
        if len(q)<2:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        cy=cyc_hp(q,lam,n)
        if cy is None or len(cy[w0:w1].dropna())<6:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        tr_d=ch_trough(cy,w0,w1,band,1,L); ends=tr_d if tr_d is not None else w1
        p0=max(w0, ends-pd.DateOffset(months=peak_cap+24))
        pk_d=ch_peak(cy,p0,ends,band,1)
        a,ep=hit(pk_d,pk_off,freq); b,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(q),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None))
    return rows

def norm_med(chs, w0, w1, n=3):
    """Cross-channel median of each channel's level expressed as a fraction of its own
    maximum inside the window.  One series standing for the panel, on a common scale."""
    cols=[]
    for nm,s in chs:
        m=ma(s,n)[w0:w1].dropna()
        if len(m)<4: continue
        cols.append((m/float(m.max())).rename(nm))
    if not cols: return None
    Z=pd.concat(cols,axis=1)
    return Z.median(axis=1,skipna=True).dropna()

def run_country4(country, band_t=0.02, band_p=0.02, n=3, L=12, peak_cap=12,
                 lead=12, tail=12):
    """Architecture D: date the cross-channel median of the normalized panel."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        z=norm_med(use,w0-pd.DateOffset(months=L),w1,n)
        if z is None or len(z)<8:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        tr_d=ch_trough(z,w0,w1,band_t,1,L); ends=tr_d if tr_d is not None else w1
        d=dev(z,L,1)[w0:ends].dropna(); cross=None
        for dd,v in d.items():
            if v>=2.0: cross=dd; break
        p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=peak_cap))
        pk_d=ch_peak(z,p0,ends,band_p,1)
        a,ep=hit(pk_d,pk_off,freq); b,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=a,ht=b,depth=depth_q(country,use,w0,w1,n),sp=None,st=None))
    return rows

# ----------------------------------------------------------------- recognition lag
def realtime_path(chs, w0, true_peak, true_trough, band=0.02, n=3, L=12,
                  horizon=48, stable=3):
    """Re-run the rule month by month on data ending at each date in turn, and report
    the first month at which its answer stops changing.  Run on the final vintage, so
    it isolates the rule's recognition lag from the effect of data revisions."""
    pk_path=[]; tr_path=[]
    for k in range(0, horizon+1):
        Tk=true_trough+pd.DateOffset(months=k)
        dt=[]; 
        for nm,s in chs:
            ss=s[:Tk]
            if len(ss)<L+n+4: continue
            d=ch_trough(ss,w0,Tk,band,n,L)
            if d is not None: dt.append(d)
        tr=med(dt); tr_path.append((Tk,tr))
        dp=[]
        if tr is not None:
            for nm,s in chs:
                ss=s[:Tk]
                d=ch_peak(ss,w0,tr,band,n)
                if d is not None: dp.append(d)
        pk_path.append((Tk, med(dp) if dp else None))
    def first_stable(path):
        final=path[-1][1]
        if final is None: return None, None
        run=0; first=None
        for Tk,d in path:
            if d==final:
                if first is None: first=Tk
                run+=1
                if run>=stable: return first, final
            else: run=0; first=None
        return None, final
    return first_stable(pk_path), first_stable(tr_path)

def settle(chs, w0, true_date, band=0.02, n=3, L=12, end='trough', horizon=48, stable=3):
    """First month T at which the rule, run on data ending at T, gives a date that it
    never afterwards changes.  Computed on the final vintage, so it measures the
    rule's recognition lag and not the effect of data revisions."""
    out=[]
    T=true_date
    for k in range(0, horizon+1):
        Tk=true_date+pd.DateOffset(months=k)
        ds=[]
        for nm,s in chs:
            ss=s[:Tk]
            if len(ss)<L+n+4: continue
            d=ch_trough(ss,w0,Tk,band,n,L) if end=='trough' else ch_peak(ss,w0,Tk,band,n)
            if d is not None: ds.append(d)
        out.append((Tk, med(ds)))
    final=out[-1][1]
    if final is None: return None, None
    run=0; first=None
    for Tk,d in out:
        if d==final:
            if first is None: first=Tk
            run+=1
            if run>=stable: return first, final
        else:
            run=0; first=None
    return None, final

def di_dates_censored(di, w0, w1, line=50.0, run=5, run_t=None):
    """ESRI's rule with Bry-Boschan's minimum-phase censoring: the peak is the last
    month the index stays above the line at the end of a run of at least `run`
    consecutive months above it, and the trough the mirror.  Without the censoring a
    diffusion index that oscillates around the line produces spurious turns."""
    d=di[w0:w1].dropna()
    if len(d)<run+2: return dict(peak=None, trough=None)
    above=(d>=line).astype(int)
    # length of the run ending at each month
    up=[]; c=0
    for v in above.values:
        c=c+1 if v else 0; up.append(c)
    dn=[]; c=0
    for v in above.values:
        c=c+1 if not v else 0; dn.append(c)
    up=pd.Series(up,index=d.index); dn=pd.Series(dn,index=d.index)
    lo=d.idxmin()
    pre=up[:lo]
    pk=None
    for t in reversed(pre.index):
        if pre[t]>=run: pk=t; break
    rt=run if run_t is None else run_t
    post=dn[lo:]
    tr=None
    for t in reversed(post.index):
        if post[t]>=rt: tr=t; break
    return dict(peak=pk, trough=tr)

def run_country_bb(country, smooth=3, lead=12, tail=12, window=5, min_phase=5, min_cycle=15):
    """Bry-Boschan applied to each channel, median of the channel turning points.
    The literature benchmark, scored exactly as the Bristow Rule is scored."""
    from onset import bry_boschan
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    TP={}
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        pks=[]; trs=[]
        for nm,s in use:
            k=(country,nm)
            if k not in TP: TP[k]=bry_boschan(s, smooth, window, min_phase, min_cycle)
            inw=[(d,t) for d,t in TP[k] if w0<=d<=w1]
            m=ma(s,smooth)
            # no official date may enter the choice: take the deepest trough in the
            # window and the highest peak that precedes it.
            q=[d for d,t in inw if t=='T']
            if q:
                tq=min(q, key=lambda d: float(m[d]))
                trs.append(tq)
                p=[d for d,t in inw if t=='P' and d<tq]
            else:
                p=[d for d,t in inw if t=='P']
            if p: pks.append(max(p, key=lambda d: float(m[d])))
        pk_d=med(pks); tr_d=med(trs)
        a,ep=hit(pk_d,pk_off,freq); b,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=spread_m(pks),st=spread_m(trs)))
    return rows

# ----------------------------------------------------------------- anchored form
def ch_trough_anchored(level, pk, w1, band=0.02, n=3, abstain=None):
    """The trough measured from the episode's own peak instead of from a rolling
    twelve-month maximum.

    The rolling window is what makes the original rule fail on contractions longer
    than the window: the maximum slides forward into the contraction itself, and the
    statistic stops registering the accumulated fall.  Once the peak is dated there is
    no need for a rolling window at all - the reference is the peak.  The rule is then
    unbound in time, which is what one wants of a rule that claims to say when a
    contraction ends.
    """
    ab = ABSTAIN if abstain is None else abstain
    m=ma(level,n)[pk:w1].dropna()
    if len(m)<4: return None
    ref=float(m.iloc[0])
    lo=float(m.min()); i=m.idxmin()
    if ab and i==m.index[-1]: return None
    amp=max(ref-lo,1e-9)
    on=m[m<=lo+band*amp]
    return max(i, on.index[-1]) if len(on) else i

def run_country_anchor(country, band_t=0.02, band_p=0.02, n=3, L=12, peak_cap=12,
                       lead=12, tail=12, passes=2):
    """Two-pass rule: date the peak with the rolling form, then re-date the trough
    with the deviation anchored at that peak."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        tr_d=med([ch_trough(s,w0,w1,band_t,n,L) for nm,s in use])
        for _ in range(max(1,passes)):
            ends=tr_d if tr_d is not None else w1
            comp=composite_dev(use,L,n,1)[w0:ends].dropna(); cross=None
            for d_,v in comp.items():
                if v>=2.0: cross=d_; break
            p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=peak_cap))
            dp=[ch_peak(s,p0,ends,band_p,n) for nm,s in use]
            pk_d=med(dp)
            if pk_d is None: break
            dt=[ch_trough_anchored(s,pk_d,w1,band_t,n) for nm,s in use]
            nt=med(dt)
            if nt is None or nt==tr_d: tr_d=nt if nt is not None else tr_d; break
            tr_d=nt
        a,ep=hit(pk_d if 'pk_d' in dir() else None,pk_off,freq)
        b,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=a,ht=b,depth=depth_q(country,use,w0,w1,n),
                         sp=spread_m(dp),st=spread_m(dt)))
    return rows

def to_quarter(s):
    """Quarterly average of a monthly series, stamped at the middle month."""
    q=s.resample('QS').mean().dropna()
    q.index=[pd.Timestamp(year=d.year,month=d.month+1,day=1) for d in q.index]
    return pd.Series(q.values,index=pd.DatetimeIndex(q.index))

def run_country_q(country, band_t=0.02, band_p=0.02, L=4, peak_cap=4,
                  lead=4, tail=4, n=1):
    """Date a quarterly chronology at quarterly frequency: average each monthly
    channel to quarters first, then run the rule with a four-quarter lookback."""
    cfg=PANELS[country]; chs=[(nm,to_quarter(s)) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        if freq!='Q':
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=3*lead); w1=trm+pd.DateOffset(months=3*tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None)); continue
        dt=[ch_trough(s,w0,w1,band_t,n,L) for nm,s in use]
        tr_d=med(dt); ends=tr_d if tr_d is not None else w1
        comp=composite_dev(use,L,n,1)[w0:ends].dropna(); cross=None
        for d_,v in comp.items():
            if v>=2.0: cross=d_; break
        p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=3*peak_cap))
        dp=[ch_peak(s,p0,ends,band_p,n) for nm,s in use]
        pk_d=med(dp)
        a,ep=hit(pk_d,pk_off,freq); b,et=hit(tr_d,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk_d,tr=tr_d,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=spread_m(dp),st=spread_m(dt)))
    return rows

# ----------------------------------------------------------------- always answers
def med_fallback(dates_abstain, dates_all):
    """Prefer the votes of channels that actually turned inside the window; if none
    did, fall back to every channel rather than returning nothing."""
    d=med(dates_abstain)
    return d if d is not None else med(dates_all)

TROUGH_FROM='cycle'
def date_any(country, chs, w0, w1, band_t=0.03, band_p=0.02, n=3, L=12, peak_cap=12,
             min_depth=5.0, max_spread=9, lam=129600.0):
    """Always returns a peak and a trough.  The verdict labels the answer; it never
    withholds one.

      'dated'         a classical contraction, channels in reasonable agreement
      'wide band'     dated, but the channels disagree by more than max_spread months
      'thin panel'    dated from fewer than five channels
      'growth cycle'  no channel fell by min_depth percent, so the level has no
                      turning point to find and the same rule was applied to the
                      cyclical component instead - the date refers to that object

    Every answer is complete.  Where one form yields nothing the other fills in, and
    where both do the extremum of the composite activity index is used.
    """
    q=quantity(country,chs) or chs
    dep=depth_comp(q,w0,w1,n)
    deepest=None
    for nm,s in q:
        m=ma(s,n)[w0:w1].dropna()
        d=maxdd(m)
        if d is not None and (deepest is None or d<deepest): deepest=d
    growth = deepest is None or deepest > -abs(min_depth)

    # --- level form
    _dd=[]
    for _n,_s in chs:
        _m=ma(_s,n)[w0:w1].dropna(); _x=maxdd(_m)
        _dd.append((_n,_s,_x if _x is not None else 0.0))
    _deep=min([x for _,_,x in _dd] or [0.0])
    _ok=[(a_,b_) for a_,b_,x in _dd if _deep>=-1e-9 or x<= 0.4*_deep] or chs
    ch_t=[(nm,s) for nm,s in _ok if nm not in SKIP_TROUGH] or _ok
    ch_p=[(nm,s) for nm,s in chs if nm not in SKIP_PEAK] or chs
    dt_a=[ch_trough(s,w0,w1,band_t,n,L,abstain=True) for nm,s in ch_t]
    dt_b=[ch_trough(s,w0,w1,band_t,n,L,abstain=False) for nm,s in ch_t]
    l_tr=med_fallback(dt_a,dt_b)
    end=l_tr if l_tr is not None else w1
    comp=composite_dev(chs,L,n,1)[w0:end].dropna(); cross=None
    for d_,v in comp.items():
        if v>=2.0: cross=d_; break
    p0=w0 if (cross is None or peak_cap is None) else max(w0,cross-pd.DateOffset(months=peak_cap))
    dp_a=[ch_peak(s,p0,end,band_p,n,abstain=True) for nm,s in ch_p]
    dp_b=[ch_peak(s,p0,end,band_p,n,abstain=False) for nm,s in ch_p]
    l_pk=med_fallback(dp_a,dp_b)

    # --- cyclical form
    #
    # A growth-cycle committee dates a DETRENDED aggregate activity index, not a
    # panel of levels.  Two instances of that object, in order of preference:
    #   (i)  the published ratio-to-trend reference series, when the statistical
    #        system publishes one (OECD measure RS, adjustment RT);
    #   (ii) otherwise the Hodrick-Prescott cyclical component of the panel's
    #        own quantity composite.
    # A detrended series oscillates about its trend and has a sharp extremum, so
    # the flat-bottom band that clause (b) needs on a level is set to zero here.
    g_pk=g_tr=None
    ref=None
    for _nm,_s in chs:
        if _nm=='monthly reference GDP': ref=_s; break
    if ref is not None and len(ma(ref,n)[w0:w1].dropna())>=6:
        g_tr=ch_trough(ref,w0,w1,0.0,n,L,abstain=False)
        gend=g_tr if g_tr is not None else w1
        g_pk=ch_peak(ref,w0,gend,band_p,n,abstain=False)
    else:
        cy=cyc_hp(q,lam,n)
        if cy is not None and len(cy[w0:w1].dropna())>=6:
            g_tr=ch_trough(cy,w0,w1,0.0,1,L,abstain=False)
            gend=g_tr if g_tr is not None else w1
            g_pk=ch_peak(cy,w0,gend,band_p,1,abstain=False)

    pk,tr = (g_pk,g_tr) if growth else (l_pk,l_tr)
    if pk is None: pk = l_pk if growth else g_pk
    if tr is None: tr = l_tr if growth else g_tr
    if pk is None or tr is None:                      # last resort: the composite itself
        ci=composite_level(q); m=ma(ci,n)[w0:w1].dropna()
        if len(m)>=4:
            if tr is None: tr=m.idxmin()
            if pk is None:
                pre=m[:tr] if tr is not None else m
                pk=(pre.idxmax() if len(pre)>1 else m.idxmax())
    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk

    sp_t=spread_m([d for d in dt_a if d is not None] or dt_b)
    sp_p=spread_m([d for d in dp_a if d is not None] or dp_b)
    parts=[]
    if growth: parts.append('growth cycle')
    if len(chs)<5: parts.append('thin panel')
    if (sp_t is not None and sp_t>max_spread) or (sp_p is not None and sp_p>max_spread):
        parts.append('wide band')
    return dict(peak=pk,trough=tr,verdict=', '.join(parts) or 'dated',depth=dep,
                deepest=deepest,channels=len(chs),spread_peak=sp_p,spread_trough=sp_t)

def run_country_any(country, lead=12, tail=12, **kw):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.max()>=trm and s.index.min()<=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use: use=chs
        d=date_any(country,use,w0,w1,**kw)
        a,ep=hit(d['peak'],pk_off,freq); b,et=hit(d['trough'],tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=d['peak'],tr=d['trough'],ep=ep,et=et,hp=a,ht=b,
                         depth=d['depth'],sp=d['spread_peak'],st=d['spread_trough'],
                         verdict=d['verdict']))
    return rows

# ----------------------------------------------------------------- concept routing
# What each committee dates, taken from its own published method, not from fit.
CONCEPT={'United States':'level',            # NBER: classical, six coincident series
         'United States (interwar)':'level',
         'Canada':'level',                   # C.D. Howe BCC: classical
         'Brazil':'level',                   # CODACE: NBER-style classical
         'Euro area':'level',                # CEPR-EABCN: classical
         'Spain':'level',                    # SBCDC (AEE): classical
         'France':'level',                   # CDCEF (AFSE): classical
         'Japan':'diffusion',                # ESRI: historical diffusion index, 50% line
         'Korea':'growth'}                   # KOSTAT: coincident index cyclical component

def di_peak_first(di, w0, w1, line=45.0, run=5):
    """The peak on a diffusion index, read as a threshold event.

    A threshold rule says the expansion ends when the index goes below the line
    and stays there.  The peak is therefore the last month above the line before
    the FIRST run of at least `run` consecutive months below it - not the last
    month above the line anywhere before the minimum.  The two differ only in a
    long contraction, where the index can rise back above the line mid-slide; the
    last-touch reading then dates the peak from that rebound, which is a month
    inside the contraction rather than its start.  `run` is Bry and Boschan's
    five-month minimum phase.
    """
    d=di[w0:w1].dropna()
    if len(d)<run+2: return None
    v=(d>=line).values; idx=d.index
    for i in range(len(v)-1):
        if v[i] and not v[i+1]:
            j=i+1; c=0
            while j<len(v) and not v[j]: c+=1; j+=1
            if c>=run: return idx[i]
    return None

def date_diffusion_panel(chs, w0, w1, line=45.0, run=1, band=0.30, n_di=5, n_band=3, L=12, run_p=4):
    """The rule on the panel's own historical diffusion index.

    The two ends take different clauses because the object has different shapes at
    them.  In an expansion a diffusion index sits near its ceiling for years and has
    no identified maximum, so the peak is a threshold event - the last month the index
    stays above the line, which is the rule ESRI publishes.  In a contraction the
    index has a distinct minimum, so the trough is the band clause.
    """
    di=hist_di(chs,n_di)
    if di is None: return dict(peak=None,trough=None)
    # ESRI's published rule is the LAST month the index stays below the line, so
    # the diffusion trough keeps that reading whatever the level clause uses.
    tr=ch_trough(di+1.0,w0,w1,band,n_band,L,abstain=False,where='last')
    end=tr if tr is not None else w1
    # The threshold clause; when the index never crosses the line - a narrow panel
    # gives a coarse index that can sit above it throughout - the peak is left
    # undated here and the caller falls back to the level route.
    pk=di_peak_first(di,w0,end,line,run_p)
    return dict(peak=pk,trough=tr)

# The AFSE's committee dates one series and says so: its reference chronology is a
# non-parametric dating of French quarterly GDP in constant euros, from INSEE, at
# quarterly frequency since 1970.  So France is routed to that series, dated with
# the same two clauses at quarterly frequency (no smoothing, four-quarter lookback).
# The other two quarterly committees are NOT routed this way, and the reason is
# their own documentation rather than their score.  The CEPR-EABCN committee states
# that "domestic production and employment are the primary conceptual measures of
# economic activity, also taking into account industrial production as a monthly
# measure of private production, sales as a measure of retail activity, investment,
# and consumption, as well as data on unemployment."  The Spanish committee states
# that it works from the Quarterly National Accounts with real GDP "particularly
# important" but alongside labour-market and industrial-production indicators.  Both
# read a panel, so both keep the panel.
QGDP={'France':'/home/claude/lab/insee/FR_gdp_q_long.csv'}
_QG={}
def qgdp(country):
    if country not in QGDP: return None
    if country not in _QG:
        p=QGDP[country]
        _QG[country]=load(p) if os.path.exists(p) else None
    return _QG[country]

# The C.D. Howe Institute's Business Cycle Council states that it uses "quarterly GDP
# and employment data as the primary means of identifying probable recessions, before
# turning to more granular monthly data - monthly GDP starting in 1961 or industrial
# production prior to 1961".  So Canada's dates come from monthly GDP where it exists
# and from industrial production before it, in the committee's own words.
def dating_series(country, w0, trm):
    """The single series a committee documents as the one it dates, when there is
    one and it covers the episode.  Returns None when the committee reads a panel."""
    g=qgdp(country)
    if g is not None and g.index.min()<=w0 and g.index.max()>=trm:
        return ('quarterly GDP', g, 1, 4)
    if country=='Canada':
        ch=dict(channels(country))
        gdp=ch.get('monthly GDP'); emp=ch.get('employment')
        if gdp is not None and gdp.index.min()<=w0 and gdp.index.max()>=trm:
            # The same document adds: "Before 1980, employment was often less
            # sensitive to declines in output; after 1980, employment moves more
            # closely with the business cycle."  So employment joins the evidence
            # from 1980 and not before.  The Canadian record makes the case
            # concretely: in 1990-92 monthly GDP bottomed in March 1991, employment
            # in October 1992, and the Council put the trough at May 1992 - between
            # the two and much nearer employment.
            # Adding employment alongside GDP from 1980 was tested and NOT adopted:
            # it cuts Canada's mean trough error from 3.9 months to 3.2 and the
            # sample's from 1.70 to 1.60, but costs two dates that were inside two
            # months and two exact peaks, and the Council's sentence says employment
            # moves with the cycle, not that it dates it.
            return ('monthly GDP', gdp, 3, 12)
        ip=ch.get('industrial production')
        if ip is not None and ip.index.min()<=w0 and ip.index.max()>=trm:
            return ('industrial production', ip, 3, 12)
    return None

def run_country_concept(country, lead=12, tail=12, concept=None, **kw):
    """Date every episode of one chronology using the concept that chronology encodes."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    cpt=concept or CONCEPT.get(country,'level')
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use: use=chs
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,
                             verdict='no data')); continue
        ds=dating_series(country,w0,trm)
        if ds is not None:
            _nm,g,_n,_L=ds
            gs=g if isinstance(g,list) else [g]
            tr=med([ch_trough(x,w0,w1,kw.get('band_t',0.12),_n,_L,abstain=False) for x in gs])
            pk=med([ch_peak(x,w0,tr if tr is not None else w1,kw.get('band_p',0.01),_n,abstain=False) for x in gs])
            if pk is not None and tr is not None:
                a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
                rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                                 pk=pk,tr=tr,ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,
                                 verdict=_nm)); continue
        if cpt=='diffusion':
            d=date_diffusion_panel(use,w0,w1)
            base=date_any(country,use,w0,w1,**kw)
            pk=d['peak'] if d['peak'] is not None else base['peak']
            tr=d['trough'] if d['trough'] is not None else base['trough']
            v='diffusion'
        elif cpt=='growth':
            base=date_any(country,use,w0,w1,min_depth=1e9,**{k:v for k,v in kw.items() if k!='min_depth'})
            pk,tr,v=base['peak'],base['trough'],'growth cycle'
        else:
            base=date_any(country,use,w0,w1,**kw)
            pk,tr,v=base['peak'],base['trough'],base['verdict']
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=pk,tr=tr,ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict=v))
    return rows

# ----------------------------------------------------------------- speed
def two_stage(chs, w0, true_trough, band_t=0.03, n=3, L=12, horizon=36, stable=3,
              pub_lag=1, after=None):
    """When the rule can first say something, and when it stops changing.

    PROVISIONAL is the first month a date can be published at all: clause (a) alone -
    the month the deviation statistic reached its maximum - evaluated on data ending
    at T and released `pub_lag` months later.  It is a real answer, and it is the
    fastest honest one.
    FINAL is the first month the full rule's answer stops changing thereafter.
    """
    if after is not None: w0=max(w0, after+pd.DateOffset(months=1))
    prov=None; prov_date=None; path=[]
    for k in range(0, horizon+1):
        T=true_trough+pd.DateOffset(months=k)
        a=[]; b=[]
        for nm,s in chs:
            ss=s[:T]
            if len(ss)<L+n+4: continue
            d=dev(ss,L,n)[w0:T].dropna()
            if len(d): a.append(d.idxmax())
            t=ch_trough(ss,w0,T,band_t,n,L,abstain=True)
            if t is not None: b.append(t)
        pa=med(a); pb=med(b)
        if prov is None and pa is not None and pa<T:
            prov=T+pd.DateOffset(months=pub_lag); prov_date=pa
        path.append((T, pb if pb is not None else pa))
    final=path[-1][1]; run=0; first=None
    for T,d in path:
        if d==final:
            if first is None: first=T
            run+=1
            if run>=stable: break
        else: run=0; first=None
    fin = None if first is None else first+pd.DateOffset(months=pub_lag)
    return dict(provisional_at=prov, provisional_date=prov_date,
                final_at=fin, final_date=final)

# ----------------------------------------------------------------- estimator ensemble
def date_ensemble(country, chs, w0, w1, mode='median', **kw):
    """Run all three estimators and combine them.

    The concept a committee dates and the estimator used to find it are different
    things.  A diffusion index of a coincident panel is a legitimate estimator of a
    CLASSICAL turning point - that is what a Bry-Boschan diffusion date has always
    been - so the estimator can be chosen on performance while the concept stays a
    property of the question.
    """
    out={}
    kl=dict(kw); kl['min_depth']=0.0
    out['level']=date_any(country,chs,w0,w1,**kl)
    kg=dict(kw); kg['min_depth']=1e9
    out['growth']=date_any(country,chs,w0,w1,**kg)
    try: out['diffusion']=date_diffusion_panel(chs,w0,w1)
    except Exception: out['diffusion']={'peak':None,'trough':None}
    pks=[d.get('peak') for d in out.values() if d.get('peak') is not None]
    trs=[d.get('trough') for d in out.values() if d.get('trough') is not None]
    if mode=='median':
        pk,tr=med(pks),med(trs)
    elif mode=='tightest':
        best=None
        for k in ('level','growth','diffusion'):
            d=out[k]
            if d.get('peak') is None or d.get('trough') is None: continue
            sp=max(d.get('spread_peak') or 0, d.get('spread_trough') or 0)
            if best is None or sp<best[0]: best=(sp,d)
        pk,tr=(best[1]['peak'],best[1]['trough']) if best else (med(pks),med(trs))
    else:
        pk,tr=out[mode]['peak'],out[mode]['trough']
    if pk is None: pk=med(pks)
    if tr is None: tr=med(trs)
    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
    base=out['level']
    return dict(peak=pk,trough=tr,verdict='ensemble',depth=base['depth'],
                channels=len(chs),spread_peak=base['spread_peak'],spread_trough=base['spread_trough'])

def run_country_ens(country, lead=12, tail=12, mode='median', **kw):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,verdict='no data')); continue
        d=date_ensemble(country,use,w0,w1,mode=mode,**kw)
        a,ep=hit(d['peak'],pk_off,freq); b,et=hit(d['trough'],tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=d['peak'],tr=d['trough'],
                         ep=ep,et=et,hp=a,ht=b,depth=d['depth'],sp=d['spread_peak'],st=d['spread_trough'],
                         verdict=d['verdict']))
    return rows

# ----------------------------------------------------------------- jackknife
def jackknife(country, chs, w0, w1, estimator, **kw):
    """Re-date the episode with each channel left out in turn.

    Returns the median of the leave-one-out dates (a bagged date, steadier than the
    full-panel one) and their dispersion in months, which measures how much the answer
    depends on any single channel.  Both are computable at the time the date is made.
    """
    pks=[]; trs=[]
    if len(chs)<3: 
        d=estimator(country,chs,w0,w1,**kw)
        return dict(peak=d.get('peak'),trough=d.get('trough'),disp=None)
    for i in range(len(chs)):
        sub=[c for j,c in enumerate(chs) if j!=i]
        try: d=estimator(country,sub,w0,w1,**kw)
        except Exception: continue
        if d.get('peak') is not None: pks.append(d['peak'])
        if d.get('trough') is not None: trs.append(d['trough'])
    dp=spread_m(pks); dt=spread_m(trs)
    return dict(peak=med(pks),trough=med(trs),
                disp=None if (dp is None and dt is None) else max(dp or 0,dt or 0))

def _est_level(country,chs,w0,w1,**kw):
    k=dict(kw); k['min_depth']=0.0; return date_any(country,chs,w0,w1,**k)
def _est_growth(country,chs,w0,w1,**kw):
    k=dict(kw); k['min_depth']=1e9; return date_any(country,chs,w0,w1,**k)
def _est_diff(country,chs,w0,w1,**kw):
    return date_diffusion_panel(chs,w0,w1)

def date_selfselect(country, chs, w0, w1, bag=True, **kw):
    """Choose the estimator whose answer depends least on any single channel, and
    report its bagged date.  No official information enters the choice."""
    cands=[]
    for nm,est in (('level',_est_level),('growth',_est_growth),('diffusion',_est_diff)):
        try: j=jackknife(country,chs,w0,w1,est,**kw)
        except Exception: continue
        if j['peak'] is None and j['trough'] is None: continue
        full=est(country,chs,w0,w1,**kw)
        cands.append((j['disp'] if j['disp'] is not None else 999, nm, j, full))
    if not cands: return dict(peak=None,trough=None,verdict='no data')
    cands.sort(key=lambda t:t[0])
    disp,nm,j,full=cands[0]
    pk = j['peak'] if bag else full.get('peak')
    tr = j['trough'] if bag else full.get('trough')
    if pk is None: pk=full.get('peak')
    if tr is None: tr=full.get('trough')
    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
    return dict(peak=pk,trough=tr,verdict=f'{nm} (self-selected)',dispersion=disp,
                depth=None,channels=len(chs),spread_peak=None,spread_trough=None)

def run_country_self(country, lead=12, tail=12, bag=True, force=None, **kw):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,verdict='no data')); continue
        if force:
            est={'level':_est_level,'growth':_est_growth,'diffusion':_est_diff}[force]
            j=jackknife(country,use,w0,w1,est,**kw); f=est(country,use,w0,w1,**kw)
            pk=(j['peak'] if bag else f.get('peak')) or f.get('peak')
            tr=(j['trough'] if bag else f.get('trough')) or f.get('trough')
            d=dict(peak=pk,trough=tr,verdict=force)
        else:
            d=date_selfselect(country,use,w0,w1,bag=bag,**kw)
        a,ep=hit(d['peak'],pk_off,freq); b,et=hit(d['trough'],tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=d['peak'],tr=d['trough'],
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict=d['verdict']))
    return rows

# ----------------------------------------------------------------- learned weights
def channel_scores(country, band_t=0.03, band_p=0.02, n=3, L=12, lead=12, tail=12):
    """For each channel, its mean absolute error at each end across this chronology's
    episodes.  Used only leave-one-episode-out, so no episode informs its own weight."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    out={}
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        for nm,s in chs:
            if s.index.min()>w0 or s.index.max()<trm: continue
            t=ch_trough(s,w0,w1,band_t,n,L,abstain=True)
            p=ch_peak(s,w0,t if t is not None else w1,band_p,n,abstain=True)
            k=(nm,str(pk_off))
            out[k]=(None if p is None else abs(md(p,pkm)), None if t is None else abs(md(t,trm)))
    return out

def weighted_median(pairs):
    """pairs: list of (date, weight).  The date at which cumulative weight passes half."""
    pairs=[(d,w) for d,w in pairs if d is not None and w>0]
    if not pairs: return None
    pairs.sort(key=lambda t:t[0])
    tot=sum(w for _,w in pairs); acc=0.0
    for d,w in pairs:
        acc+=w
        if acc>=tot/2: return d
    return pairs[-1][0]

def run_country_learned(country, band_t=0.03, band_p=0.02, n=3, L=12, lead=12, tail=12,
                        power=1.0, floor=1.0):
    """Weight each channel by 1/(mean absolute error + floor) computed on every OTHER
    episode of the same chronology."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    sc=channel_scores(country,band_t,band_p,n,L,lead,tail)
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,verdict='no data')); continue
        pp=[]; tt=[]
        for nm,s in use:
            ep_=[v[0] for (n2,e2),v in sc.items() if n2==nm and e2!=str(pk_off) and v[0] is not None]
            et_=[v[1] for (n2,e2),v in sc.items() if n2==nm and e2!=str(pk_off) and v[1] is not None]
            wp=1.0/((np.mean(ep_) if ep_ else 6.0)+floor)**power
            wt=1.0/((np.mean(et_) if et_ else 6.0)+floor)**power
            t=ch_trough(s,w0,w1,band_t,n,L,abstain=True)
            p=ch_peak(s,w0,t if t is not None else w1,band_p,n,abstain=True)
            pp.append((p,wp)); tt.append((t,wt))
        pk=weighted_median(pp); tr=weighted_median(tt)
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict='learned weights'))
    return rows
