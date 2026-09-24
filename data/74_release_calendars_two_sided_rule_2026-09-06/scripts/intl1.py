"""THE PAPER SPREAD ABROAD. The American object is the one-month commercial paper rate over the three-month Treasury
bill; no foreign Treasury-bill series is held, so the portable analogue is the THREE-MONTH INTERBANK RATE LESS THE
OVERNIGHT/CALL RATE — what banks charge each other for three months above what they charge overnight, which is the same
thing the American spread measures. Both legs are held monthly for 49 economies in the OECD short-term file (collection
93). Read the same way as at home: a three-month mean standing above its lowest value of the previous nine months. NO
LINE IS FITTED PER COUNTRY: each country's reading is divided by its own TRAILING robust scale (median absolute
deviation over the previous ten years, causal), and ONE global line k serves every country. Scored against ECRI's July
2021 chronology."""
import os,json,glob,numpy as np,pandas as pd
D93=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','93_intl_money_market_spread_2026-09-06')
E=json.load(open(os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','39_conjunction_intl_2026-09','cloud_v8','intl','ecri_chronology_2021.json')))
out=open('intl1.out','w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n'); out.flush()
P("ECRI chronology keys:",list(E.keys())[:8] if isinstance(E,dict) else type(E))
def ld(p):
    x=pd.read_csv(p); x.columns=[c.strip().lower() for c in x.columns][:len(x.columns)]
    dc=[c for c in x.columns if 'date' in c or c=='time'] or [x.columns[0]]
    vc=[c for c in x.columns if c in ('value','obs_value')] or [x.columns[-1]]
    x[dc[0]]=pd.to_datetime(x[dc[0]],errors='coerce')
    s=pd.to_numeric(x.set_index(dc[0])[vc[0]],errors='coerce').dropna()
    return s[s.index.notna()].sort_index()
CO={}
for f in glob.glob(os.path.join(D93,'data','**','*.csv'),recursive=True):
    b=os.path.basename(f); iso=os.path.basename(os.path.dirname(f))
    kind='IR3TIB' if '.IR3TIB.' in b else ('IRSTCI' if '.IRSTCI.' in b else ('IRLT' if '.IRLT.' in b else None))
    if kind is None: continue
    src='STES' if b.startswith('STES') else 'KEI'
    CO.setdefault(iso,{}).setdefault(kind,{})[src]=f
P(f"economies with files: {len(CO)}")
SP={}
for iso,d in CO.items():
    if 'IR3TIB' not in d or 'IRSTCI' not in d: continue
    a=ld(d['IR3TIB'].get('STES') or d['IR3TIB'].get('KEI')); b=ld(d['IRSTCI'].get('STES') or d['IRSTCI'].get('KEI'))
    idx=a.index.union(b.index); s=(a.reindex(idx).ffill()-b.reindex(idx).ffill()).dropna()
    s=s[s.index>=max(a.index.min(),b.index.min())]
    if len(s)>=180: SP[iso]=s
P(f"economies with BOTH legs and 15+ years: {len(SP)} — {sorted(SP)}")
def obj(s,sm=3,win=9):
    m=s.rolling(sm).mean(); return (m-m.rolling(win).min()).dropna()
def zscale(G,years=10):
    med=G.rolling(12*years,min_periods=60).median()
    mad=(G-med).abs().rolling(12*years,min_periods=60).median()*1.4826
    return (G/mad.replace(0,np.nan)).dropna()
P("\nspread spans:")
for iso in sorted(SP): P(f"   {iso} {SP[iso].index.min().date()} -> {SP[iso].index.max().date()} ({len(SP[iso])} months)")
import pickle; pickle.dump({k:v for k,v in SP.items()},open('cache/intl_spreads.pkl','wb'))
out.close()
