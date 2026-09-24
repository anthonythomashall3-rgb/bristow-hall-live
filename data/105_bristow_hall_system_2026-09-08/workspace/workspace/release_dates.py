"""ITEM 20: real release dates instead of fixed pub_day offsets.  For each of the twelve onset calls, the object that confirmed
it, the month it read, the day the harness assumes it was public, and the day ALFRED says that month's first print appeared."""
exec(open('dominance.py').read().split('rows=[]')[0])
import csv
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
def first_dates(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    dates=[pd.Timestamp(r[0]) for r in rows[1:]]; out={}
    for j in range(1,len(h)):
        col=[rows[1+j0][j] for j0 in range(len(dates))]
        idx=[i for i,v in enumerate(col) if v not in ('','.')]
        if not idx: continue
        m=dates[idx[-1]]
        if m not in out: out[m]=pd.Timestamp(h[j].split('_')[1])
    return pd.Series(out).sort_index()
RD={'UNRATE':first_dates('UNRATE'),'HOUST':first_dates('HOUST'),'AWHMAN':first_dates('AWHMAN'),'NDMANEMP':first_dates('NDMANEMP'),'JTSJOL':first_dates('JTSJOL')}
with contextlib.redirect_stdout(io.StringIO()):
    t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
print(f"{'peak':8}{'call':12}{'leg':4}{'condition':11}{'sahm_month':12}{'assumed':12}{'ALFRED first print':20}{'lag assumed':>12}{'lag actual':>11}")
for o in t:
    if o['kind']!='peak' or o['published']<pd.Timestamp('1948-06-01'): continue
    hit=None
    for i,(p,q) in enumerate(zip(PK,TR)):
        if p-pd.DateOffset(months=6)<=o['date']<=q: hit=i; break
    if hit is None: continue
    cond=o.get('condition'); m=o.get('sahm_month'); actual=None
    if m is not None:
        key={'Sahm':'UNRATE','housing35':'HOUST','pair':'AWHMAN','vacancy':'JTSJOL'}.get(cond)
        if key and m in RD[key].index: actual=RD[key][m]
        if cond=='housing35' and m in RD['UNRATE'].index and actual is not None: actual=max(actual,RD['UNRATE'][m])
        if cond=='pair' and m in RD['NDMANEMP'].index and actual is not None: actual=max(actual,RD['NDMANEMP'][m])
    la=(o['published']-me(PK[hit])).days; lb=None if actual is None else (max(actual,o['claims_published'])-me(PK[hit])).days
    print(f"{PK[hit]:%Y-%m}  {o['published']:%Y-%m-%d}  {o['leg']:3} {str(cond):11}{'' if m is None else f'{m:%Y-%m}':12}{o['published']:%Y-%m-%d}  {'n/a (pre-vintage or claims date)' if actual is None else f'{actual:%Y-%m-%d}':20}{la:12d}{'' if lb is None else lb:>11}")
