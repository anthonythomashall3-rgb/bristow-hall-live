"""Join the national prints into weekly national series 1945-1983: initial claims and insured unemployment (State programs, NSA,
as first printed) and the printed insured unemployment rate.  A week's value: the median of its own prints; where prints disagree by
more than 2% the cell is a conflict unless a change-implied print settles it (value - change = the previous week's print).
Validation against FRED ICNSA/CCNSA (1967 on), IURNSA (1971 on) and the Fieldhouse national monthly totals."""
import glob, pandas as pd, numpy as np, re
D=pd.concat([pd.read_csv(f,parse_dates=['week']) for f in sorted(glob.glob('national_prints_v*.csv'))],ignore_index=True)
D['field']=D.field.replace({'cc':'iu'})
def yrs(lab):
    m=re.search(r'_(19\d\d)_(\d\d)',lab)
    if not m: m2=re.search(r'_(19\d\d)',lab); return (int(m2.group(1))-1,int(m2.group(1))+2) if m2 else (1940,1990)   # half-volume labels v34_1979_no27_52 (6 Sep 2026)
    a=int(m.group(1)); b=int(m.group(1)[:2]+m.group(2)); return a-1,b+1
lo=D.volume.map(lambda l:yrs(l)[0]); hi=D.volume.map(lambda l:yrs(l)[1]); D=D[(D.week.dt.year>=lo)&(D.week.dt.year<=hi)]
D=D[(D.week>='1945-01-01')&(D.week<='1983-12-31')]
# the split volumes: issues 1-26 run July-December, 27-50 January-June of the volume's second year
def vol_ok(row):
    lab=row['volume']; y=int(re.search(r'_(19\d\d)',lab).group(1))
    if 'no1_26' in lab: return pd.Timestamp(f'{y}-06-15')<=row['week']<=pd.Timestamp(f'{y+1}-01-15')
    if 'no27_50' in lab: return pd.Timestamp(f'{y+1}-01-01')<=row['week']<=pd.Timestamp(f'{y+1}-07-15')
    if 'no17_26' in lab: return pd.Timestamp(f'{y}-10-01')<=row['week']<=pd.Timestamp(f'{y+1}-04-15')
    return True
D=D[D.apply(vol_ok,axis=1)]
out={}
for field in ('ic','iu','iur'):
    e=D[D.field==field]
    g=e.groupby('week').value.agg(['median','min','max','count'])
    tol=0.02 if field!='iur' else 0.15
    ok=(g['max']-g['min'])<=tol*g['median']
    own=g['median'].where(ok)
    imp=e.dropna(subset=['chg']).copy(); imp['prev']=imp.value-imp.chg; imp['pweek']=imp.week-pd.Timedelta(days=7)
    implied=imp.groupby('pweek').prev.median()
    imy=e.dropna(subset=['chg_yr']).copy(); imy['prev']=imy.value-imy.chg_yr; imy['pweek']=imy.week-pd.Timedelta(days=364)
    implied_yr=imy.groupby('pweek').prev.median()
    P=pd.concat([own.rename('own'),g['median'].rename('raw'),implied.rename('implied'),implied_yr.rename('implied_yr')],axis=1)
    vals=[]
    for wk,r in P.iterrows():
        c=[(x,s) for x,s in ((r['own'],'own'),(r['implied'],'implied'),(r['implied_yr'],'implied_yr')) if pd.notna(x) and x>0]
        if len(c)>=2:
            pairs=[(a,b) for k,a in enumerate(c) for b in c[k+1:] if abs(a[0]-b[0])<=max(3,0.01*max(a[0],b[0]))]
            if pairs: vals.append((wk,pairs[0][0][0],'both')); continue
            if pd.notna(r['own']): vals.append((wk,r['own'],'own-unconfirmed')); continue
            vals.append((wk,np.nan,'conflict')); continue
        if len(c)==1: vals.append((wk,c[0][0],c[0][1]))
        elif pd.notna(r['raw']) and field=='iur': vals.append((wk,r['raw'],'raw'))
    S=pd.DataFrame(vals,columns=['week','value','source']).set_index('week').sort_index()
    # plausibility: a single print must lie within 25% of the rolling median of two-print-confirmed cells (window 13 weeks)
    if field!='iur':
        ref=S.value.where(S.source=='both'); med=ref.rolling(13,center=True,min_periods=3).median().reindex(S.index).interpolate(limit=8,limit_area='inside')
        bad=(S.source!='both')&med.notna()&((S.value/med-1).abs()>0.25); S.loc[bad,'value']=np.nan; S.loc[bad,'source']='implausible'
    out[field]=S
    print(field,'weeks',len(S),'with value',int(S.value.notna().sum()),S.source.value_counts().to_dict())
W=pd.concat([out['ic'].value.rename('ic'),out['iu'].value.rename('iu'),out['iur'].value.rename('iur'),out['ic'].source.rename('ic_source'),out['iu'].source.rename('iu_source')],axis=1).sort_index()
W.to_csv('national_weekly_first_prints_1945_1983.csv')
print('coverage by year (weeks with ic / iu):'); c=W.groupby(W.index.year).agg(ic=('ic','count'),iu=('iu','count'),iur=('iur','count')); print(c.T.to_string())
# validation
R="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/"
def fred(s):
    for p in (R+'25_fred_daily_weekly/fred_weekly/'+s+'.csv',R+'01_labor_unemployment/weekly/'+s+'.csv'):
        try:
            x=pd.read_csv(p); x.columns=['d','v']; x['d']=pd.to_datetime(x['d']); return x.set_index('d')['v'].astype(float)
        except Exception: pass
    return None
for nm,col,fs in (('ICNSA','ic','ICNSA'),('CCNSA','iu','CCNSA'),('IURNSA','iur','IURNSA')):
    f=fred(fs)
    if f is None: print(nm,'not in archive'); continue
    j=pd.concat([W[col],f.rename('fred')],axis=1).dropna()
    if not len(j): print(nm,'no overlap'); continue
    r=np.log(j[col]/j['fred']) if col!='iur' else (j[col]-j['fred'])
    print(f"{nm}: overlap {len(j)} weeks {j.index.min().date()}..{j.index.max().date()}  median {r.median():+.4f}  |dev|>2%(or 0.2pt) share {((r.abs()>0.02) if col!='iur' else (r.abs()>0.2)).mean():.3f}")
d2=pd.read_stata(R+'24_bristow_rule_lab/workspace/lab/fh/src/CBUR Data.dta'); d2['Date']=pd.to_datetime(d2['Date']).dt.to_period('M').dt.to_timestamp()
gg=d2.groupby('Date')[['IC_NSA','CC_NSA']].sum(); w=d2.groupby('Date')['MonthtoWeekWeight'].first(); gg=gg.div(w,axis=0)
m=W[['ic','iu']].groupby(W.index.to_period('M')).mean(); m.index=m.index.to_timestamp()
for col,fc in (('ic','IC_NSA'),('iu','CC_NSA')):
    j=pd.concat([m[col],gg[fc].rename('fh')],axis=1).dropna(); r=np.log(j[col]/j['fh'])
    print(f"vs Fieldhouse national {fc}: months {len(j)} {j.index.min().date()}..{j.index.max().date()} median {r.median():+.3f} |r|>0.1 {(r.abs()>0.1).mean():.3f}; by year >0.1: {(r.abs()>0.1).groupby(r.index.year).mean().round(2).to_dict()}")
