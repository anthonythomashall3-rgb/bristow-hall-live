"""A WEEKLY insured unemployment rate before 1971, built from the Department's own weekly state continued-claims counts (collection 59,
1945-1983) so that the pre-1971 branches can run on a twelve-day clock instead of the Fieldhouse monthly series' tenth-of-the-following-month.
Construction: sum the reporting states each week; scale by the share of a fixed base those states cover (so a week with 44 reporting states is
comparable with one with 49); seasonally adjust in real time (week-of-year medians on a trailing seven-year window, refitted each December, so
no factor uses data not yet published); then divide by the implied covered employment, which is the Fieldhouse monthly insured rate's own
denominator (monthly seasonally adjusted continued claims over that rate), interpolated to weeks. No new line, no new source."""
from mini import *
out=open('preweek.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
CC=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09/weekly_cc_1945_1983.csv'),index_col=0,parse_dates=True)
CC=CC.drop(columns=[c for c in CC.columns if c in ('PR','VI')])
P("weekly state continued claims:",CC.index.min().date(),"->",CC.index.max().date(),CC.shape)
base=CC.loc['1960':'1969'].mean()                      # a fixed base share per state
share=(CC.notna()*base).sum(axis=1)/base.sum()
raw=CC.sum(axis=1,skipna=True)/share.replace(0,np.nan)
raw=raw[share>=0.60].dropna()
P("coverage-adjusted weekly national continued claims:",len(raw),"weeks with >=60% of the base covered; span",raw.index.min().date(),raw.index.max().date())
lg=np.log(raw)
def sa_rt(x):
    """real-time week-of-year seasonal factors: for each week, the median log deviation from a 53-week centred mean over the previous seven
    years only, refitted every December"""
    trend=lg.rolling(53,center=True,min_periods=40).mean(); dev=(lg-trend).dropna()
    outv={}
    for t in lg.index:
        hist=dev[dev.index<pd.Timestamp(t.year,1,1)]           # only years already complete
        hist=hist[hist.index>=pd.Timestamp(t.year-7,1,1)]
        if len(hist)<100: continue
        w=t.isocalendar()[1]; sub=hist[[d.isocalendar()[1]==w for d in hist.index]]
        if len(sub)==0: continue
        outv[t]=lg[t]-float(sub.median())
    return pd.Series(outv).sort_index()
sa=sa_rt(lg); P("real-time seasonally adjusted weekly log continued claims:",len(sa),sa.index.min().date(),"->",sa.index.max().date())
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna()
mo=np.exp(sa).resample('MS').mean()
den=(mo/fh.reindex(mo.index)).dropna()                 # implied covered employment, monthly
denw=den.reindex(sa.index.union(den.index)).interpolate(limit_direction='both').reindex(sa.index)
rate=(np.exp(sa)/denw).dropna()
P("weekly insured rate (own build) vs the Fieldhouse monthly rate, monthly means: correlation",round(float(rate.resample('MS').mean().corr(fh.reindex(rate.resample('MS').mean().index))),4))
cmp=pd.concat([rate.resample('MS').mean().rename('own'),fh.rename('FH')],axis=1).dropna()
P("  1948-1970 mean absolute difference",round(float((cmp['own']-cmp['FH']).abs()['1948':'1970'].mean()),4),"points; sample",[(m.strftime('%Y-%m'),round(a,2),round(b,2)) for m,(a,b) in cmp[['own','FH']]['1953-06':'1953-11'].iterrows()])
rate.to_csv('cache/weekly_iur_prewar.csv',header=['iur_weekly_own'])
P("saved cache/weekly_iur_prewar.csv")

out.close()
