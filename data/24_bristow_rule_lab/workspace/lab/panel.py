import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np
from core import load, ma3

def ts(s): return pd.Timestamp(s+'-01')
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def qtr(d): return (d.year, (d.month-1)//3+1)
def qdiff(a,b): return (a[0]-b[0])*4+(a[1]-b[1])

# ---------- statistics ----------
def stat_u(u,L=12,n=3):                 # Sahm form on a counter-cyclical rate
    m=u.rolling(n).mean(); return m-m.shift(1).rolling(L).min()
def stat_x(x,L=12,n=3):                 # drawdown form on a pro-cyclical level
    m=x.rolling(n).mean(); mx=m.shift(1).rolling(L).max(); return (mx-m)/mx*100

# ---------- chronologies ----------
US_M=[('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
      ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
      ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
USIW_M=[('1929-08','1933-03'),('1937-05','1938-06')]
CA_M=[('1929-04','1933-02'),('1937-11','1938-06'),('1947-08','1948-03'),('1951-04','1951-12'),
      ('1953-07','1954-07'),('1957-03','1958-01'),('1960-03','1961-03'),('1974-10','1975-03'),
      ('1981-06','1982-10'),('1990-03','1992-05'),('2008-10','2009-05'),('2020-02','2020-04')]
JP_M=[('1951-06','1951-10'),('1954-01','1954-11'),('1957-06','1958-06'),('1961-12','1962-10'),
      ('1964-10','1965-10'),('1970-07','1971-12'),('1973-11','1975-03'),('1977-01','1977-10'),
      ('1980-02','1983-02'),('1985-06','1986-11'),('1991-02','1993-10'),('1997-05','1999-01'),
      ('2000-11','2002-01'),('2008-02','2009-03'),('2012-03','2012-11'),('2018-10','2020-05')]
# quarterly chronologies, given as (peak quarter, trough quarter)
EZ_Q=[((1974,3),(1975,1)),((1980,1),(1982,3)),((1992,1),(1993,3)),((2008,1),(2009,2)),
      ((2011,3),(2013,1)),((2019,4),(2020,2))]
ES_Q=[((1974,4),(1975,2)),((1978,3),(1979,2)),((1992,1),(1993,3)),((2008,2),(2009,4)),
      ((2010,4),(2013,2)),((2019,4),(2020,2))]
FR_Q=[((1974,3),(1975,3)),((1980,1),(1980,4)),((1992,1),(1993,1)),((2008,1),(2009,2)),
      ((2019,4),(2020,2))]

def q2m(q, which='mid'):
    y,qq=q; m={'first':1,'mid':2,'last':3}[which]+3*(qq-1)
    return pd.Timestamp(year=y,month=m,day=1)

PANELS={
 'United States': dict(chrono=US_M, freq='M', src='NBER', series=[
    ('unemployment', stat_u, '/home/claude/archive/data/fred/UNRATE.csv'),
    ('payrolls',     stat_x, '/home/claude/archive/data/fred/PAYEMS.csv'),
    ('industrial production', stat_x, '/home/claude/lab/USAPROINDMISMEI.csv')]),
 'United States (interwar)': dict(chrono=USIW_M, freq='M', src='NBER', series=[
    ('unemployment', stat_u, '/home/claude/archive/data/robustness/M0892AUSM156SNBR.csv')]),
 'Canada': dict(chrono=CA_M, freq='M', src='C.D. Howe BCC', series=[
    ('unemployment', stat_u, '/home/claude/a20/LRHUTTTTCAM156S.csv'),
    ('employment',   stat_x, '/home/claude/lab/LFEMTTTTCAM647S.csv'),
    ('industrial production', stat_x, '/home/claude/lab/CANPROINDMISMEI.csv')]),
 'Japan': dict(chrono=JP_M, freq='M', src='ESRI', series=[
    ('unemployment', stat_u, '/home/claude/a20/LRHUTTTTJPM156S.csv'),
    ('employment',   stat_x, '/home/claude/lab/LFEMTTTTJPM647S.csv'),
    ('industrial production', stat_x, '/home/claude/lab/JPNPROINDMISMEI.csv')]),
 'Euro area': dict(chrono=EZ_Q, freq='Q', src='CEPR-EABCN', series=[
    ('unemployment', stat_u, '/home/claude/lab/LRHUTTTTEZM156S.csv'),
    ('industrial production', stat_x, '/home/claude/lab/EA19PRINTO01IXOBSAM.csv')]),
 'Spain': dict(chrono=ES_Q, freq='Q', src='SBCDC (AEE)', series=[
    ('unemployment', stat_u, '/home/claude/lab/LRHUTTTTESM156S.csv'),
    ('industrial production', stat_x, '/home/claude/lab/ESPPROINDMISMEI.csv')]),
 'France': dict(chrono=FR_Q, freq='Q', src='CDCEF (AFSE)', series=[
    ('unemployment', stat_u, '/home/claude/lab/LRHUTTTTFRM156S.csv'),
    ('industrial production', stat_x, '/home/claude/lab/FRAPROINDMISMEI.csv')]),
}

def load_panel(cfg):
    out=[]
    for nm,f,p in cfg['series']:
        try: out.append((nm,f(load(p))))
        except Exception as e: print('  ! could not load',nm,p,e)
    return out

def peak_date(stat, w0, w1):
    seg=stat[w0:w1].dropna()
    return seg.idxmax() if len(seg) else None

def wave_date(stat, w0, w1, prom=0.25, sep=6, floor=0.5):
    """Last deterioration wave: the latest prominent local maximum of the statistic
    that still sits high in the episode.  prom and floor are fractions of the window max."""
    seg=stat[w0:w1].dropna()
    if len(seg)==0: return None
    v=seg.values; idx=seg.index; mx=float(v.max())
    if mx<=0: return seg.idxmax()
    cands=[]
    for i in range(len(v)):
        if v[i] < floor*mx: continue
        lo=max(0,i-sep); hi=min(len(v),i+sep+1)
        if v[i] < v[lo:hi].max()-1e-12: continue          # local max within +/- sep months
        cands.append(i)
    if not cands: return seg.idxmax()
    # keep a later candidate only if the statistic retraced by `prom` between the two
    keep=[cands[0]]
    for i in cands[1:]:
        j=keep[-1]
        if i-j < sep: 
            if v[i] > v[j]: keep[-1]=i
            continue
        trough=float(v[j:i+1].min())
        if (min(v[i],v[j]) - trough) >= prom*mx: keep.append(i)
        elif v[i] > v[j]: keep[-1]=i
    return idx[keep[-1]]

def bottom_band(level, w0, w1, alpha=0.10, n=3, procyclical=True):
    """Last month the activity level is still within alpha of its cyclical extreme,
    measured as a fraction of the peak-to-trough amplitude inside the window."""
    m=level.rolling(n).mean()[w0:w1].dropna()
    if len(m)<4: return None
    if procyclical:
        lo=float(m.min()); i=m.idxmin(); hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
        amp=max(hi-lo,1e-9); band=lo+alpha*amp
        ok=m[m<=band]
    else:
        hi=float(m.max()); i=m.idxmax(); lo=float(m[:i].min()) if len(m[:i]) else float(m.min())
        amp=max(hi-lo,1e-9); band=hi-alpha*amp
        ok=m[m>=band]
    return ok.index[-1] if len(ok) else None

# --- economies added in the second expansion ---
KR_M=[('1992-01','1993-01'),('1996-03','1998-08'),('2000-08','2001-07'),('2002-12','2005-04'),
      ('2008-01','2009-02'),('2011-08','2013-03'),('2017-09','2020-05')]          # KOSTAT reference dates
BR_M=[('1980-10','1983-02'),('1987-02','1988-10'),('1989-06','1991-12'),('1994-12','1995-09'),
      ('1997-10','1999-02'),('2000-12','2001-09'),('2002-10','2003-06'),('2008-07','2009-01')]  # CODACE monthly
BR_Q=[((2014,2),(2016,4)),((2019,4),(2020,2))]                                    # CODACE quarterly, later cycles

PANELS['Korea']=dict(chrono=KR_M, freq='M', src='KOSTAT', series=[])
PANELS['Brazil']=dict(chrono=BR_M, freq='M', src='CODACE', series=[])
PANELS['Brazil (recent)']=dict(chrono=BR_Q, freq='Q', src='CODACE', series=[])
