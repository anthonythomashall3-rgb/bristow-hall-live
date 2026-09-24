from mini import *
from legu_min import leg_U, s_cur
from scipy import stats
PEAKS=[p for p in PK]; TROUGHS=[t for t in TR]
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PEAKS,TROUGHS): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line):
    o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=5, start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool); b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
S=hits(g,0.5); V=hits(vr,0.36); H=hits(PAIR,1.0); P=hits(P1,1.0)
print("CONTROL: v8 confirmer union S|V|H|P, window (6 back,4 fwd), 1960-2026 quiet months:",win_expo([S,V,H,P]))
print("v8's published figure: 8.78% (its quiet set used the 2023-07 episode; here the 13th is Paper 1's 2024-04..08)")
print("\nbranch U (proposer: IUR gap >= 0.50), confirmers V|H|P:")
eV,n=win_expo([V]); eVHP,_=win_expo([V,H,P]); eSVHP,_=win_expo([S,V,H,P])
print(f"  window exposure: V alone {eV:.2f}%, V|H|P {eVHP:.2f}%, S|V|H|P {eSVHP:.2f}%  ({n} quiet months 1960-2026)")
# first factor for U: quiet-month episodes of leg U at 0.50, 1972-2026 (52-week warm-up), on the quiet months of the IUR's own span
idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QM=int(q.sum()); QY=QM/12
U=leg_U(s_cur,0.50); qU=[p for p,d in U if q.reindex([pd.Timestamp(d.year,d.month,1)]).fillna(False).iloc[0]]
print(f"  leg U quiet-month episodes 1972-2026: {len(qU)} in {QM} quiet months ({QY:.1f} quiet years); observed rate 0; 95% upper bound (rule of three) {3/QY*100:.2f}%/yr")
for nm,e in [('V',eV),('V|H|P',eVHP),('S|V|H|P',eSVHP)]:
    hz=3/QY*e/100; print(f"    hazard bound with {nm:8}: {hz*100:.3f}%/yr = one in {1/hz:.0f} years at the 95% bound on the first factor (observed: 0)")
print("\nbranch hub (proposer: Sahm >= 0.50 first print in a quiet month; confirmer: vacancy at line in the six months back):")
idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2); QM2=int(q2.sum()); QY2=QM2/12
# Sahm quiet crossings as episodes (a crossing = first month >=0.5 after a month <0.5), counted in quiet months
eps=[]; armed=True
for m,v in g.items():
    if m<idx2[0]: continue
    if armed and v>=0.5:
        armed=False
        if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m)
    elif not armed and v<0.5: armed=True
print(f"  Sahm quiet crossings 1949-2026: {len(eps)} {[e.strftime('%Y-%m') for e in eps]} in {QM2} quiet months ({QY2:.1f} quiet years): {len(eps)/QY2*100:.2f}%/yr observed, upper bound {stats.chi2.ppf(0.95,2*(len(eps)+1))/2/QY2*100:.2f}%/yr")
eVb,_=win_expo([V],back=7,fwd=1,start='1949-01-01')
print(f"  vacancy (2,6) >= 0.36 back-window exposure (six months back, no forward), quiet months 1949-2026: {eVb:.2f}%")
hz=len(eps)/QY2*eVb/100; hzb=stats.chi2.ppf(0.95,2*(len(eps)+1))/2/QY2*eVb/100
print(f"  hub hazard: {hz*100:.3f}%/yr observed (one in {1/hz:.0f} years); {hzb*100:.3f}%/yr at the upper bound (one in {1/hzb:.0f})")
print("\nfor comparison, v8's first factor (claims legs A B C M U): 3 quiet episodes in 38.5 quiet years = 7.79%/yr; x 8.78% = 0.684%/yr, one in 146")
