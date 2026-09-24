D="/Users/anthonyhall/mnt/Onset Detector Data"
def rd(p): return pd.read_csv(p,index_col=0,parse_dates=True).iloc[:,0].dropna()
UM=rd(D+'/15_sentiment_surveys/monthly/UMCSENT.csv'); TH=rd(D+'/03_payroll_employment/monthly/TEMPHELPS.csv'); BAA=rd(D+'/07_credit/monthly/BAA.csv'); AAA=rd(D+'/07_credit/monthly/AAA.csv'); NF=rd(D+'/05_financial_conditions/weekly/NFCI.csv')
import glob
ism=[f for f in glob.glob(D+'/74_release_calendars_two_sided_rule_2026-09-06/data/fred_ism/*.csv')]; print('ism files',[f.split('/')[-1] for f in ism][:6])
# objects (data month -> value); "in place" = at or beyond the line in any month of the window
OBJ={}
OBJ['sentiment 3mo below 12mo high']=(UM.rolling(3).mean().rolling(12).max().shift(1)-UM.rolling(3).mean()).dropna()
OBJ['temp help 3mo change %']=(-(TH/TH.shift(3)-1)*100).dropna()
sp_=(BAA-AAA); OBJ['Baa-Aaa above 9mo low']=(sp_-sp_.rolling(9).min().shift(1)).dropna()
nfm=NF.resample('MS').mean(); OBJ['NFCI above 12mo low']=(nfm-nfm.rolling(12).min().shift(1)).dropna()
spx=_SPX.dropna(); dd_=(1-spx/spx.rolling(252,min_periods=200).max())*100; OBJ['S&P drawdown from 52wk high %']=dd_.resample('MS').max()
OBJ['starts 3mo below 12mo high, log pts']=((lh.rolling(12).max()-lh.rolling(3).mean())).dropna()
for f in ism:
    s=rd(f); nm=f.split('/')[-1].replace('.csv',''); OBJ['ISM '+nm+' (50 minus)']=(50-s).dropna()
WIN={'TARGET 1990 (Jul 1990)':('1990-05','1990-07'),'TARGET 2008 (Nov-Dec 2007)':('2007-10','2007-12'),'TARGET 2024 (Nov23-Apr24)':('2023-11','2024-04'),
     'trap 1979-04 (Apr-Aug 1979)':('1979-04','1979-08'),'trap 1989-05 (May-Sep 1989)':('1989-05','1989-09'),'trap 2003-04 (Apr-Aug 2003)':('2003-04','2003-08'),'trap 2022-11 (Nov22-Mar23)':('2022-11','2023-03'),'trap 1987-11 (Nov87-Mar88)':('1987-11','1988-03'),'trap 2019-07 (Jul19-Jan20)':('2019-07','2020-01'),'trap 2025-12 (Dec25-Apr26)':('2025-12','2026-04')}
print(f"{'object':44s} "+' | '.join(k[:11] for k in WIN))
for nm,s in OBJ.items():
    row=[]
    for k,(a,b) in WIN.items():
        seg=s[a:b]; row.append(f"{seg.max():6.1f}" if len(seg) else '   n/a')
    print(f"{nm:44s} "+' | '.join(row))
