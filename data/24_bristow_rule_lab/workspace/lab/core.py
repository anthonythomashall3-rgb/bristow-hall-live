import pandas as pd, numpy as np

def load(path, name=None):
    d=pd.read_csv(path); d.columns=['d','v']
    d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    s=d.dropna().set_index('d')['v'].astype(float)
    s.name=name or path
    return s

def md(a,b): return (a.year-b.year)*12+(a.month-b.month)

# ---------- statistic builders (all take the raw monthly unemployment rate) ----------
def ma3(u): return u.rolling(3).mean()

def sahm(u, L=12):
    m=ma3(u); return m - m.shift(1).rolling(L).min()

def sahm_ratio(u, L=12):
    m=ma3(u); return m/m.shift(1).rolling(L).min() - 1.0

def sahm_z(u, L=12, W=120):
    """Sahm difference divided by the trailing std of the same statistic."""
    s=sahm(u,L); return s/s.rolling(W, min_periods=36).std()

def sahm_relmax(u, L=12, W=120):
    """Sahm difference scaled by the country's own historical peak magnitude."""
    s=sahm(u,L); return s/s.rolling(W, min_periods=36).max().clip(lower=1e-9)

def delta(u,k=3):
    m=ma3(u); return m-m.shift(k)

def anchored(u, start, back=12):
    """floor frozen at the min of the `back` months before `start`."""
    m=ma3(u); base=float(m[:start].tail(back).min()); return m-base
