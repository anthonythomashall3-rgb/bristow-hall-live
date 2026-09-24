"""The two new series written out: the survey-week insured unemployment rate with its publication date, and the
share of states whose own insured rate stands two tenths above its own fifty-two-week minimum."""
import sys,glob,os
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('export97.out','w')"))
C=os.environ['HOME']+'/mnt/Onset Detector Data/97_survey_week_and_state_breadth_2026-09-07/data'
D=W+'/lab/data/fred_weekly'
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own[own.index<frd.index.min()],frd]).sort_index()
IURW.to_frame('insured_rate_weekly').to_csv(C+'/WEEKLY_INSURED_RATE_SPLICED.csv')
rows={}
for t,v in IURW.items():
    m=pd.Timestamp(t.year,t.month,1); d=abs((t-pd.Timestamp(t.year,t.month,12)).days)
    if m not in rows or d<rows[m][0]: rows[m]=(d,v,t)
idx=sorted(rows)
sv=pd.DataFrame({'month':idx,'survey_week_ending':[rows[m][2] for m in idx],'insured_rate':[rows[m][1] for m in idx]})
sv['published']=sv['survey_week_ending']+pd.Timedelta(days=12)
sv.to_csv(C+'/SURVEY_WEEK_INSURED_RATE.csv',index=False)
cols={}
for f in sorted(glob.glob(D+'/*INSUREDUR.csv')): cols[os.path.basename(f)[:2]]=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].dropna()
ST=pd.DataFrame(cols).sort_index(); MN=ST.rolling(52,min_periods=52).min().shift(1)
br=pd.DataFrame({'share_two_tenths_above_own_minimum':(((ST-MN)>=0.20).sum(axis=1)/ST.notna().sum(axis=1)),
                 'units_reporting':ST.notna().sum(axis=1)}).dropna()
br['published']=br.index+pd.Timedelta(days=19)
br.to_csv(C+'/STATE_BREADTH.csv')
P(f"survey-week rate {len(sv)} months {sv['month'].min():%Y-%m} to {sv['month'].max():%Y-%m}")
P(f"state breadth {len(br)} weeks {br.index.min():%Y-%m-%d} to {br.index.max():%Y-%m-%d}, units {int(br['units_reporting'].iloc[-1])}")
out.close()
