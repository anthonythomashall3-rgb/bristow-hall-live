"""The Philadelphia Fed's daily business-conditions index as a ruling, and to the day (3 September 2026).

Anthony asked whether the Fed dates recession starts to the day.  First-hand: FRED's daily recession
series (USRECD, USRECDM, USRECDP) are the NBER's monthly dates turned into days by three conventions
(peak through the month before the trough; midpoints; peak through trough) - the FRED blog of June
2022 says so and nothing there is dated independently.  The one Federal Reserve object that IS daily
is the Aruoba-Diebold-Scotti business conditions index (Philadelphia Fed, daily from 1 March 1960;
file ads_index_most_current_vintage.xlsx, fetched 3 September 2026, SHA-256 in
MANIFEST_ads_2026-09-03.sha256).  ADS is a mean-zero growth-type index, not a level, so it is read
three ways:

  BB on monthly ADS    Bry-Boschan (the tool's, smooth 3) on the monthly mean - the reading a
                       growth-cycle committee would take
  level clause         the rule's own level clause on the CUMULATED index - a level whose drawdowns
                       are the index's negative stretches (exp of the running sum; the clauses'
                       dates do not depend on the scale) - in the shipped windows, refinement in force
  to the day           the same cumulated level on the daily series: the day it peaks before each
                       contraction and the day it bottoms

Each is scored against the committee's month (and the day, against the committee's month as a
range).  Errors in months, rule minus committee.  Output ads_ruling.log.  A comparator under Rule 11
and a candidate tenth ruling for memo section 8e; nothing in the tool is chosen on it.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude')
import numpy as np, pandas as pd, bristow_rule_v3 as B
NBER=[('1960-04','1961-02'),('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
      ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
x=pd.read_excel('/home/claude/lab/cmp/ads/ads_index_most_current_vintage.xlsx')
x['Date']=pd.to_datetime(x['Date'].astype(str).str.replace(':','-'),format='%Y-%m-%d')
ads=x.set_index('Date')['ADS_Index'].astype(float)
monthly=ads.resample('MS').mean()
cum_m=np.exp(monthly.cumsum()/100.0)            # a level: scale is immaterial to the clauses' dates
cum_d=np.exp(ads.cumsum()/3000.0)
bb=B.bry_boschan(monthly,smooth=3)
def nearest(tp,kind,ref,tol=12):
    c=[d for d,k in tp if k==kind and abs(md(d,ref))<=tol]
    return min(c,key=lambda d:abs(md(d,ref))) if c else None
print(f'ADS daily {ads.index.min():%Y-%m-%d} to {ads.index.max():%Y-%m-%d}, {len(ads)} days; monthly means {monthly.index.min():%Y-%m} to {monthly.index.max():%Y-%m}')
print('\nepisode           BB on monthly ADS        level clause on cumulated ADS      to the day (cumulated daily level)')
print('peak     trough   peak(err)   trough(err)  peak(err)   trough(err)          peak day     trough day')
E={'bb':{'P':[],'T':[]},'lv':{'P':[],'T':[]},'day':{'P':[],'T':[]}}
other=[d for d,k in bb if not any(abs(md(d,pd.Timestamp(p+'-01')))<=12 and k=='P' or abs(md(d,pd.Timestamp(t+'-01')))<=12 and k=='T' for p,t in NBER)]
for p,t in NBER:
    pk=pd.Timestamp(p+'-01'); tr=pd.Timestamp(t+'-01')
    bp=nearest(bb,'P',pk); bt=nearest(bb,'T',tr)
    w0=pk-pd.DateOffset(months=12); w1=tr+pd.DateOffset(months=12)
    lt=B.channel_trough(cum_m,w0,w1,0.12,3,12,False); lp=B.channel_peak(cum_m,w0,lt if lt is not None else w1,0.01,3,False)
    dseg=cum_d[w0:w1]; dtr=dseg.idxmin(); dpk=dseg[:dtr].idxmax()
    f=lambda d,r:'  -        ' if d is None else f'{d:%Y-%m}({md(d,r):+d})'.ljust(11)
    for k,(a,b_) in {'bb':(bp,bt),'lv':(lp,lt),'day':(pd.Timestamp(dpk.year,dpk.month,1),pd.Timestamp(dtr.year,dtr.month,1))}.items():
        if a is not None: E[k]['P'].append(md(a,pk))
        if b_ is not None: E[k]['T'].append(md(b_,tr))
    print(f'{p}  {t}   {f(bp,pk)} {f(bt,tr)}  {f(lp,pk)} {f(lt,tr)}          {dpk:%Y-%m-%d}   {dtr:%Y-%m-%d}')
def cnt(e): return f'n {len(e)} exact {sum(v==0 for v in e)} w1 {sum(abs(v)<=1 for v in e)} w3 {sum(abs(v)<=3 for v in e)} mae {np.mean(np.abs(e)):.2f}'
for k,lab in (('bb','BB on monthly ADS'),('lv','level clause on cumulated ADS'),('day','the day, scored by its month')):
    print(f'{lab:32s}: peaks {cnt(E[k]["P"])} | troughs {cnt(E[k]["T"])}')
print('BB turns on monthly ADS with no committee counterpart within twelve months:',[f'{d:%Y-%m}{k}' for d,k in bb if not (any(k=="P" and abs(md(d,pd.Timestamp(p+"-01")))<=12 for p,t in NBER) or any(k=="T" and abs(md(d,pd.Timestamp(t+"-01")))<=12 for p,t in NBER))])
print('\n2022 to the data edge: monthly ADS min', f'{monthly["2022":].min():.2f} in {monthly["2022":].idxmin():%Y-%m};', 'BB turns since 2022:',[f'{d:%Y-%m}{k}' for d,k in bb if d>=pd.Timestamp('2022-01-01')],
      '; cumulated level high since 2022', f'{cum_m["2022":].idxmax():%Y-%m}', 'low after it', f'{cum_m[cum_m["2022":].idxmax():].idxmin():%Y-%m}', f'(fall {100*(cum_m[cum_m["2022":].idxmax():].min()/cum_m["2022":].max()-1):+.2f}% of the level, i.e. the index summed {monthly[cum_m["2022":].idxmax():cum_m[cum_m["2022":].idxmax():].idxmin()].sum():+.1f} index-months)')
