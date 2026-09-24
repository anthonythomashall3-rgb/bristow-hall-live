"""ITEM 6: fast weekly ACTIVITY objects (EIA petroleum products supplied 1991 on; Treasury withheld taxes 2005 on) as PAIRS with a
labour stock at a lower line, priced on window exposure.  A pair is free if the union stays at 8.78%.  (5 September 2026)"""
exec(open('dominance.py').read().split('rows=[]')[0])
D25=os.path.expanduser("~/mnt/")+'Onset Detector Data/25_fred_daily_weekly/'
def wk(f):
    d=pd.read_csv(D25+f); d.columns=['date','v']; d['date']=pd.to_datetime(d['date']); return pd.to_numeric(d.set_index('date')['v'],errors='coerce').dropna()
EIA={'products_total':wk('other_weekly/eia_WRPUPUS2.csv'),'gasoline':wk('other_weekly/eia_WGFUPUS2.csv'),'distillate':wk('other_weekly/eia_WDIUPUS2.csv')}
wt=pd.read_csv(D25+'other_daily/US_daily_withheld_taxes.csv'); wt.columns=['date','v']; wt['date']=pd.to_datetime(wt['date']); wt=wt.set_index('date')['v'].astype(float)
WT=wt.resample('W-FRI').sum()
def monthly_gap(s, sm=4, look=26):
    x=np.log(s.rolling(sm).mean())*100; gap=(x.rolling(look).max()-x)      # fall from the 26-week max, log points
    return gap.resample('MS').last()
OBJ={k:monthly_gap(v) for k,v in EIA.items()}
x=np.log(WT.rolling(13).sum())*100; OBJ['withheld_yoy_fall']=(-(x-x.shift(52))).resample('MS').last()
def rec(sec_extra):
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']]+sec_extra,horizon_months=4,back_months=6)
    return record([(o['published'],o['date']) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')])
print('v8', rec([])[:4])
print(f"{'object':20}{'line':>6}{'gate':>10}{'gline':>6}{'expo':>7}{'called':>7}{'other':>6}{'median':>7}{'worst':>6}")
for nm,o in OBJ.items():
    for line in [2,3,5,8]:
        for gate,gs in [('sahm',sahm),('vac',vac)]:
            for gl in ([0.2,0.3] if gate=='sahm' else [0.2,0.25,0.3]):
                pr=pd.concat([o/line,gs/gl],axis=1).min(axis=1,skipna=False).dropna()
                e=win_expo([S,V,H,HS['P'],hits(pr,1.0)],7,5)[0]
                r=rec([dict(name='wpair',gap=pr,line=1.0,pub_day=7)])
                if abs(e-8.78)<0.02 and (r[2]<28.5 or r[3]<90): print(f"{nm:20}{line:6.0f}{gate:>10}{gl:6.2f}{e:7.2f}{r[0]:7d}{r[1]:6d}{r[2]:7.1f}{r[3]:6.0f}  FREE & FASTER")
                elif abs(e-8.78)<0.02: pass
                else: print(f"{nm:20}{line:6.0f}{gate:>10}{gl:6.2f}{e:7.2f}{r[0]:7d}{r[1]:6d}{r[2]:7.1f}{r[3]:6.0f}")
print('done')
