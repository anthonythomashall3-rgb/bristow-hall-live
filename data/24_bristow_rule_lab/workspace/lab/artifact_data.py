"""Data for the Bristow Rule page (report/bristow_rule_page.html): every chronology, every contraction,
every channel the rule read, and the American route's live objects.  Writes report/bristow_data.json.
3 September 2026."""
import sys, json, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B, bench
from bench import PANELS, channels, ep3, ts, q2m, quantity, dating_series, md, load, hit
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
bench.ABSTAIN=True
CONC={'United States':'level','United States (interwar)':'level','Canada':'level','Brazil':'level','Euro area':'level','Spain':'level','France':'level','Japan':'diffusion','Korea':'growth'}
ABOUT={
 'United States':dict(committee='NBER Business Cycle Dating Committee',concept='level',reads='the six monthly series the committee names (production, payrolls, household employment, real income less transfers, real consumption, real manufacturing and trade sales) and retail volume'),
 'United States (interwar)':dict(committee='NBER (interwar)',concept='level',reads="the NBER Macrohistory series for the period: business activity, department store sales, manufacturing employment and payrolls, industrial production, the unemployment rate"),
 'Canada':dict(committee='C.D. Howe Institute Business Cycle Council',concept='level',reads='monthly GDP (the Council\'s own series since 1961), industrial and manufacturing production, employment, retail volume'),
 'Japan':dict(committee='ESRI (Cabinet Office)',concept='diffusion',reads='the historical diffusion index across the coincident components, read with ESRI\'s own fifty-per-cent clause'),
 'Korea':dict(committee='Statistics Korea (KOSTAT)',concept='growth',reads='the cyclical component of the coincident composite - a growth-cycle chronology'),
 'Brazil':dict(committee='CODACE (FGV/IBRE)',concept='level',reads='the monthly GDP proxy (IBC-Br), production, retail volume, employment (PME chained onto PNAD Continua)'),
 'Euro area':dict(committee='CEPR-EABCN Business Cycle Dating Committee',concept='level, quarterly',reads='quarterly GDP first of all, with production, employment and unemployment'),
 'Spain':dict(committee='Spanish Business Cycle Dating Committee (AEE)',concept='level, quarterly',reads='quarterly GDP and the monthly production, sales and energy series'),
 'France':dict(committee='AFSE dating committee',concept='level, quarterly',reads='quarterly GDP, the committee\'s own object'),
 'South Africa':dict(committee='South African Reserve Bank',concept='growth',reads='the Bank\'s coincident business cycle indicator, detrended - a growth-cycle chronology'),
 'Taiwan':dict(committee='National Development Council',concept='growth',reads='the Council\'s own detrended coincident index'),
 'Germany':dict(committee='German Council of Economic Experts (Sachverständigenrat)',concept='level',reads='the four channels the Council names: industrial production, retail volume, real orders received, the unemployment rate'),
 'Mexico':dict(committee='CFCEM (INEGI committee)',concept='level',reads='industrial production, construction, retail volume, exports, imports, unemployment, the IGAE monthly activity index, vehicle production'),
}
HELD=pd.read_csv('/home/claude/lab/cmp/rulings_heldout.csv')
def m(t): return None if t is None or (isinstance(t,float) and np.isnan(t)) else pd.Timestamp(t).strftime('%Y-%m')
def series_window(s,w0,w1,base):
    x=s[w0-pd.DateOffset(months=6):w1+pd.DateOffset(months=6)].dropna()
    if len(x)==0: return None
    x=x[np.isfinite(x.values)]
    if len(x)==0: return None
    b=x.get(base,np.nan)
    if not np.isfinite(b) or b==0:
        pos=x[x>0]
        if len(pos)==0: return None
        b=pos.iloc[0]
    return [[d.strftime('%Y-%m'),round(float(v/b*100.0),2)] for d,v in x.items() if np.isfinite(v/b) and abs(v/b)<1e6]
out={'countries':[]}
for c in PANELS:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    eps=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        useq=[(nm,B.to_quarter(x)) for nm,x in use] if freq=='Q' else use
        vol=quantity(c,useq) or useq
        r=B.date_turning_points(useq,w0,w1,volume_channels=vol,concept=CONC[c],lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,
                                smooth=(1 if freq=='Q' else 3),lookback=(4 if freq=='Q' else 12),dating_series=dating_series(c,w0,trm))
        a,e1=hit(r['peak'],pk_off,freq); b_,e2=hit(r['trough'],tr_off,freq)
        chan=[]
        for nm,s in use:
            cp=B.channel_peak(s,w0,trm,0.01,3,True) if freq=='M' else None
            ct=B.channel_trough(s,w0,w1,0.12,3,12,True) if freq=='M' else None
            chan.append(dict(name=nm,kind=bench.KIND[c].get(nm,'level'),series=series_window(s,w0,w1,pkm),peak=m(cp),trough=m(ct)))
        eps.append(dict(peak=pk_off if freq=='M' else f'{pk_off[0]}-Q{pk_off[1]}',trough=tr_off if freq=='M' else f'{tr_off[0]}-Q{tr_off[1]}',
                        peak_m=pkm.strftime('%Y-%m'),trough_m=trm.strftime('%Y-%m'),freq=freq,
                        rule_peak=m(r['peak']),rule_trough=m(r['trough']),err_peak=e1,err_trough=e2,verdict=r.get('verdict'),channels=chan))
    out['countries'].append(dict(name=c,held_out=False,**ABOUT[c],episodes=eps))
# the four held out: channels from their own loaders, errors from rulings_heldout.csv
from bench import hp_filter
def rtt(s,lam=500000.0):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]; t=pd.Series(hp_filter(y.values,lam),index=y.index); return np.exp(y-t)*100.0
def L(f): return load('/home/claude/lab/kei/'+f)
HO={}
co=load('/home/claude/lab/sarb/ZAF_coincident.csv')
HO['South Africa']=([('coincident indicator, detrended (the committee\'s object)',rtt(co)),('retail volume',L('ZAF_TOVM_G47.csv')),('manufacturing production',L('ZAF_PRVM_C.csv'))],
  [('1946-07','1947-04'),('1948-11','1950-02'),('1951-12','1953-03'),('1955-04','1956-09'),('1958-01','1959-03'),('1960-04','1961-08'),('1965-04','1965-12'),('1967-05','1967-12'),('1970-12','1972-08'),('1974-08','1977-12'),('1981-08','1983-03'),('1984-06','1986-03'),('1989-02','1993-05'),('1996-11','1999-08'),('2007-11','2009-08'),('2013-11','2017-04'),('2019-06','2020-04')])
bci=pd.read_csv('/home/claude/lab/twn/TWN_bci.csv',index_col=0,parse_dates=True)
def tcol(f,c):
    d=pd.read_csv(f'/home/claude/lab/twn/TWN_{f}.csv',index_col=0,parse_dates=True); s=pd.to_numeric(d[c],errors='coerce').dropna(); return s
HO['Taiwan']=([("the Council's detrended coincident index (the committee's object)",pd.to_numeric(bci['景氣同時指標不含趨勢指數(點)'],errors='coerce').dropna()),('industrial production',tcol('ip','總指數')),('employment',tcol('labour','就業人數(千人)')),('exports',tcol('trade','USD(百萬美元) / 出口'))],
  [('1955-11','1956-09'),('1964-09','1966-01'),('1968-08','1969-10'),('1974-02','1975-02'),('1980-01','1983-02'),('1984-05','1985-08'),('1989-05','1990-08'),('1995-02','1996-03'),('1997-12','1998-12'),('2000-09','2001-09'),('2004-03','2005-02'),('2008-03','2009-02'),('2011-02','2012-01'),('2014-10','2016-02'),('2022-01','2023-04')])
NAT='/home/claude/lab/nat/deu'
HO['Germany']=([('industrial production',L('DEU_PRVM_BTE.csv')),('retail volume',L('DEU_TOVM_G47.csv')),('real orders received',load(f'{NAT}/DEU_orders_real_sa.csv')),('unemployment rate (100 - u)',100.0-load(f'{NAT}/DEU_unemployment_rate_sa_spliced.csv'))],
  [('1966-03','1967-05'),('1974-01','1975-07'),('1980-01','1982-11'),('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')])
HO['Mexico']=([('industrial production',L('MEX_PRVM_BTE.csv')),('construction production',L('MEX_PRVM_F.csv')),('retail volume',L('MEX_TOVM_G47.csv')),('IGAE',load('/home/claude/lab/mex/MEX_igae_sa.csv')),('vehicle production',load('/home/claude/lab/mex/MEX_vehicles_sa.csv'))],
  [(None,'1983-06'),('1985-09','1986-12'),('1994-11','1995-05'),('2000-09','2002-01'),('2008-06','2009-05'),('2019-05','2020-05')])
for c,(chs,chrono) in HO.items():
    eps=[]
    for pk_off,tr_off in chrono:
        trm=ts(tr_off); pkm=ts(pk_off) if pk_off else trm-pd.DateOffset(months=18)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        rp=HELD[(HELD.country==c)&(HELD.kind=='P')&(HELD.committee==pk_off)]; rt=HELD[(HELD.country==c)&(HELD.kind=='T')&(HELD.committee==tr_off)]
        e1=None if (pk_off is None or len(rp)==0 or pd.isna(rp.rule_err.iloc[0])) else int(rp.rule_err.iloc[0]); e2=None if (len(rt)==0 or pd.isna(rt.rule_err.iloc[0])) else int(rt.rule_err.iloc[0])
        chan=[dict(name=nm,kind='level',series=series_window(s,w0,w1,pkm),peak=None,trough=None) for nm,s in chs if s.index.min()<=w0]
        eps.append(dict(peak=pk_off,trough=tr_off,peak_m=pkm.strftime('%Y-%m') if pk_off else None,trough_m=trm.strftime('%Y-%m'),freq='M',
                        rule_peak=None if e1 is None else (pkm+pd.DateOffset(months=e1)).strftime('%Y-%m'),rule_trough=None if e2 is None else (trm+pd.DateOffset(months=e2)).strftime('%Y-%m'),
                        err_peak=e1,err_trough=e2,verdict='held out',channels=chan))
    out['countries'].append(dict(name=c,held_out=True,**ABOUT[c],episodes=eps))
# the American route's live objects
Pcl=pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True)
A=B.claims_diffusion(Pcl.rolling(2).mean().dropna(how='all'),36.,8)
Ppay=pd.read_csv('/home/claude/lab/fh/FH_state_payrolls_nsa.csv',index_col=0,parse_dates=True); Ppay=Ppay.loc[:,Ppay.notna().mean()>0.9]
SA=B.seasonal_factors_realtime(Ppay); E=B.claims_diffusion(-(SA.rolling(3).mean().dropna(how='all')),0.75,6)
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
comp=B.composite_deviation(chs,12,3,2).dropna()
NBER=[(ts(ep3(e,'M')[0]).strftime('%Y-%m'),ts(ep3(e,'M')[1]).strftime('%Y-%m')) for e in PANELS['United States']['chrono']]
def ser(s,start='1947-01'):
    s=s[s.index>=pd.Timestamp(start+'-01')]; return [[d.strftime('%Y-%m'),round(float(v),1)] for d,v in s.items() if np.isfinite(v)]
out['us']=dict(nber=NBER,claims_breadth=ser(A),payroll_breadth=ser(E,'1949-01'),composite_D=ser(comp,'1948-01'),
    calls=[('1948-12-10','M','1948-11','confirmed'),('1951-09-20','A','—','unconfirmed'),('1953-09-20','A','1953-07','confirmed'),('1957-08-20','A','1957-08','confirmed'),('1960-02-20','A','1960-04','confirmed'),('1967-04-20','A','—','unconfirmed'),('1970-01-31','B','1969-12','confirmed'),('1974-02-16','B','1973-11','confirmed'),('1980-03-20','A','1980-01','confirmed'),('1981-12-20','A','1981-07','confirmed'),('1990-09-20','A','1990-07','confirmed'),('2001-03-31','B','2001-03','confirmed'),('2007-12-28','C','2007-12','confirmed'),('2020-03-28','C','2020-02','confirmed'),('2023-08-28','C','—','unconfirmed')])
json.dump(out,open('/home/claude/report/bristow_data.json','w'),separators=(',',':'))
import os; print('written', os.path.getsize('/home/claude/report/bristow_data.json')//1024,'KB;', sum(len(c['episodes']) for c in out['countries']),'episodes;', len(out['countries']),'chronologies')
