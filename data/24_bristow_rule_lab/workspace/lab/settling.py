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
def date_at(v,band=0.02,thr=2.0):
    ip=vintage('INDPRO',v); E=episodes(drawdown(ip),thr)
    if not E: return None
    e=E[-1]; w0,w1=e[0], min(e[-1]+pd.DateOffset(months=12), ip.index.max())
    ds=[]
    for sid in ('INDPRO','PAYEMS'):
        d=channel_date(vintage(sid,v),w0,w1,band)
        if d is not None: ds.append(d)
    if not ds: return None
    ds=sorted(ds); return ds[(len(ds)-1)//2] if len(ds)%2==0 else ds[len(ds)//2]
TR={'1991-03':'1992-12-22','2001-11':'2003-07-17','2009-06':'2010-09-20','2020-04':'2021-07-19'}
print('month-by-month real-time record (US, standalone, INDPRO + PAYEMS vintages)\n')
for tr,ann in TR.items():
    t=pd.Timestamp(tr+'-01'); seq=[]
    for k in range(1,25):
        v=(t+pd.DateOffset(months=k)).strftime('%Y-%m-%d')
        try: d=date_at(v)
        except Exception: d=None
        seq.append((k,v,d))
    # settling time: first k after which the date never changes again
    final=[d for k,v,d in seq if d is not None][-1]
    settle=None
    for i,(k,v,d) in enumerate(seq):
        if d is None: continue
        if all(dd==final for kk,vv,dd in seq[i:] if dd is not None):
            settle=k; break
    gap=(final.year-t.year)*12+(final.month-t.month)
    annlag=(pd.Timestamp(ann)-t).days/30.44
    line=' '.join(f'{k}:{(d.strftime("%y-%m") if d is not None else "--")}' for k,v,d in seq[:12])
    print(f'trough {tr}: final date {final.strftime("%Y-%m")} (gap {gap:+d}), settles {settle} months after the trough; NBER announced {annlag:.0f} months after')
    print(f'   first 12 vintages: {line}\n')
