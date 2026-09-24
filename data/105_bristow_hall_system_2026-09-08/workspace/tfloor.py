"""THE TROUGH-SIDE SPEED FLOOR, MEASURED. Before another closer is built, the arithmetic is worth settling: what is the
earliest date at which ANY object the rule owns could have shown that the labour market had turned? For each trough the
earliest publication date of every candidate piece of recovery evidence is printed, so the floor is measured rather
than asserted."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('tfloor.out','w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
CL=ICfp.dropna().rolling(4).mean().dropna()
CC=pd.read_csv(D+'/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna().rolling(4).mean().dropna()
def pubm(d): return lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=d-1)
def first_rise(ser,pf,tr,pct,look=12):
    mn=ser.rolling(look,min_periods=look).min(); rel_=((ser/mn-1)*100).dropna()
    seg=rel_[(rel_.index>=tr)&(rel_.index<=tr+pd.DateOffset(months=12))]
    h=seg[seg>=pct]
    return (pf(h.index[0]),h.index[0]) if len(h) else (None,None)
def first_fall_weeks(ser,tr,k):
    """the first week by which the four-week mean has fallen for k consecutive weeks, published five days later"""
    s=ser[(ser.index>=tr-pd.DateOffset(months=1))&(ser.index<=tr+pd.DateOffset(months=12))]
    run=0; prev=None
    for t,v in s.items():
        if prev is not None and v<prev: run+=1
        else: run=0
        prev=v
        if run>=k: return t+pd.Timedelta(days=5),t
    return None,None
def first_drop_pct(ser,tr,pct):
    s=ser[(ser.index>=tr-pd.DateOffset(months=6))&(ser.index<=tr+pd.DateOffset(months=12))]
    mx=s.cummax(); rel_=(1-s/mx)*100
    seg=rel_[rel_.index>=tr]
    h=seg[seg>=pct]
    return (h.index[0]+pd.Timedelta(days=5),h.index[0]) if len(h) else (None,None)
P(f"{'trough':8s} {'shipped':>8s} | {'hours+1%':>10s} {'starts+1%':>10s} {'vacancy+1%':>11s} {'claims 3 down':>14s} {'claims -2%':>11s} {'contclaims -3%':>15s} | {'earliest':>9s}")
rows=[]
for i in range(13):
    tr=TR[i]; e=me(tr)
    cells=[]
    for nm,f in [('hours',lambda: first_rise(AW,pubm(5),tr,1.0)),('starts',lambda: first_rise(LH,pubm(17),tr,1.0)),
                 ('vac',lambda: first_rise(VR,(lambda m: VPUB[m] if m in VPUB.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)),tr,1.0)),
                 ('cl3',lambda: first_fall_weeks(CL,tr,3)),('cl2pc',lambda: first_drop_pct(CL,tr,2.0)),('cc3pc',lambda: first_drop_pct(CC,tr,3.0))]:
        try: p_,m_=f()
        except Exception: p_,m_=None,None
        cells.append((nm,p_))
    lags=[(nm,(p_-e).days) for nm,p_ in cells if p_ is not None]
    best=min([l for _,l in lags]) if lags else None
    shipped={0:137,1:6,2:67,3:67,4:52,5:67,6:37,7:51,8:97,9:37,10:23,11:37,12:96}[i]
    rows.append((i,best))
    P(f"{tr:%Y-%m}  {shipped:>8d} | "+" ".join(f"{(dict(lags).get(nm,'-')):>10}" for nm in ['hours','starts','vac','cl3','cl2pc','cc3pc'])+f" | {str(best):>9}")
ok=[b for _,b in rows if b is not None]
P(f"\n   the floor: median {np.median(ok):.0f} days, mean {np.mean(ok):.1f}, worst {max(ok)}, within the month {sum(1 for x in ok if 0<=x<=31)}/{len(ok)}")
P(f"   from 1961 (the instrument's own sample): within the month {sum(1 for i,b in rows if i>=4 and b is not None and 0<=b<=31)}/9")
out.close()
