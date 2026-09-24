import sys; sys.path.insert(0,'/home/claude/lab')
import urllib.request, os, pandas as pd
from final_rule import drawdown, channel_date
def vintage(sid,v):
    os.makedirs('vint',exist_ok=True); p=f'vint/{sid}_{v}.csv'
    if not os.path.exists(p):
        urllib.request.urlretrieve(f'https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&vintage_date={v}',p)
    d=pd.read_csv(p); d.columns=['d','v']; d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    return d.dropna().set_index('d')['v'].astype(float)
def episodes(s,thr=2.0):
    out=[];cur=[]
    for d,v in s.dropna().items():
        if v>=thr: cur.append(d)
        elif cur: out.append(cur);cur=[]
    if cur: out.append(cur)
    return out
def standalone_date(v, band=0.02, thr=2.0):
    """no official dates at all: detect the episode on the vintage, date inside it"""
    ip=vintage('INDPRO',v)
    E=episodes(drawdown(ip),thr)
    if not E: return None,None
    e=E[-1]                                   # the most recent episode in this vintage
    w0,w1=e[0], min(e[-1]+pd.DateOffset(months=12), ip.index.max())
    ds=[]
    for sid in ('INDPRO','PAYEMS'):
        try: x=vintage(sid,v)
        except Exception: continue
        d=channel_date(x,w0,w1,band)
        if d is not None: ds.append(d)
    if not ds: return None,(w0,w1)
    ds=sorted(ds); return (ds[(len(ds)-1)//2] if len(ds)%2==0 else ds[len(ds)//2]),(w0,w1)
TR={'1991-03':'1990-07','2001-11':'2001-03','2009-06':'2007-12','2020-04':'2020-02'}
ANN={'1991-03':'1992-12-22','2001-11':'2003-07-17','2009-06':'2010-09-20','2020-04':'2021-07-19'}
print(f"{'trough':9s} {'vintage':11s} {'episode':22s} {'rule':9s} {'gap':>4s}")
for tr in TR:
    t=pd.Timestamp(tr+'-01')
    for k in (3,6,9,12):
        v=(t+pd.DateOffset(months=k)).strftime('%Y-%m-%d')
        try: d,w=standalone_date(v)
        except Exception as ex: print(f'{tr:9s} {v:11s} vintage unavailable'); continue
        if d is None: print(f'{tr:9s} {v:11s} no episode detected'); continue
        gap=(d.year-t.year)*12+(d.month-t.month)
        print(f'{tr:9s} {v:11s} {w[0].strftime("%Y-%m")}..{w[1].strftime("%Y-%m"):9s} {d.strftime("%Y-%m"):9s} {gap:>+4d}')
    print(f'          NBER announced this trough on {ANN[tr]}')
