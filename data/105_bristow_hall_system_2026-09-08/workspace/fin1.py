"""A financial channel as a confirmer of the low insured-rate line: the Baa-Treasury spread's rise. Read at every U-low crossing."""
from mini import *
from legu_min import s_cur
L=W+'/lab/speed2/data/'
def rd(f):
    d=pd.read_csv(L+f); d.columns=['d','v']; d['d']=pd.to_datetime(d['d']); return d.set_index('d')['v'].astype(float)
baa=rd('BAA.csv'); g10=rd('GS10.csv'); sp=(baa-g10).dropna()
rise6=(sp-sp.rolling(6).min().shift(1)).dropna()   # rise over the prior six months' low
gap=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna()
def leg_gap(line,rearm=0.0,pub=5):
    c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax(ser,p): seg=ser[(ser.index>=p-pd.DateOffset(months=6))&(ser.index<=p+pd.DateOffset(months=4))]; return seg.max() if len(seg) else float('nan')
with open('fin1.out','w') as f:
    f.write("Baa - 10y Treasury spread, rise over its prior six-month low (pp), max inside each U-low (0.25) proposal window; R = recession\n")
    for p,dd in leg_gap(0.25):
        f.write(f"  {p:%Y-%m-%d} {'R    ' if inw(dd) else 'quiet'} spread rise max {wmax(rise6,p):.2f}  level max {wmax(sp,p):.2f}\n")
    q=[wmax(rise6,p) for p,dd in leg_gap(0.25) if not inw(dd)]; r=[wmax(rise6,p) for p,dd in leg_gap(0.25) if inw(dd)]
    f.write(f"quiet max {max(q):.2f}; recession values {sorted(round(x,2) for x in r)}\n")
