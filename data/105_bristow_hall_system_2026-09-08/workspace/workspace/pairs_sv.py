"""A pair of the two SHIPPED confirmers at LOWER lines: Sahm's gap (first prints) at x AND the vacancy fast form at y in the
same month.  Free if the confirming union's window exposure stays 8.78%; then what it buys.  (5 September 2026)"""
exec(open('dominance.py').read().split('rows=[]')[0])
print(f"base v8: exposure {win_expo([S,V,H,HS['P']],7,5)[0]:.2f}%")
def rec(sec_extra):
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']]+sec_extra,horizon_months=4,back_months=6)
    return record([(o['published'],o['date']) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')])
base=rec([]); print('v8 record', base[:4])
sg=g if hasattr(g,'rolling') else None
print(f"{'x (Sahm)':>9}{'y (vac)':>9}{'expo':>8}{'called':>7}{'other':>6}{'median':>8}{'worst':>7}  lags")
for x in [0.20,0.25,0.30,0.35,0.40,0.45]:
    for y in [0.12,0.15,0.20,0.25,0.30]:
        pr=pd.concat([sahm/x,vac/y],axis=1).min(axis=1).dropna()
        e=win_expo([S,V,H,HS['P'],hits(pr,1.0)],7,5)[0]
        r=rec([dict(name='sv_pair',gap=pr,line=1.0,pub_day=30)])
        flag='FREE' if abs(e-8.78)<0.02 else ''
        print(f"{x:9.2f}{y:9.2f}{e:8.2f}{r[0]:7d}{r[1]:6d}{r[2]:8.1f}{r[3]:7.0f}  {flag}")
