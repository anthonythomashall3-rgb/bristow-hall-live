# verify_paper.py - A VERIFIER ROW FOR EVERY NUMBER THE EXECUTIVE SUMMARIES PRINT (v3.26; the four versions in
# scripts/two_pager/, 10 September 2026). Each row recomputes the number from the archived inputs and the walk's own
# objects (walk46's preamble, the w46 diary and walk-end lines) and prints PASS or FAIL against the printed value.
# Writes RECORD-PAPER-v326-<date>.md beside the collection's other records. Exits 1 on any FAIL.
# Run in the workspace: PYTHONPATH=. python3 s2/verify_paper.py
import sys,pickle,io,contextlib,os,hashlib,datetime as _dt
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb')); pg=pickle.load(open('cache/w46_prog.pkl','rb')); CH=pg['chosen']
ROWS=[]
def row(name,got,exp,tol=0):
    ok=(abs(float(got)-float(exp))<=tol) if isinstance(exp,(int,float)) and not isinstance(exp,bool) else (got==exp)
    ROWS.append((name,got,exp,ok)); print(('PASS' if ok else 'FAIL'),name,'got',got,'expected',exp)
MO=30.4375; fd=lambda m:pd.Timestamp(m+'-01'); me=lambda m:fd(m)+pd.offsets.MonthEnd(0)
# ---- 1. the diary (the walk's own record, on one clock) ----
LOG=pg['log']; opens=[(pd.Timestamp(p),d,br) for p,k,d,br in LOG if k=='OPEN' and pd.Timestamp(p)>=pd.Timestamp('1962-01-01')]
closes=[(pd.Timestamp(p),d,br) for p,k,d,br in LOG if k=='CLOSE' and pd.Timestamp(p)>=pd.Timestamp('1962-01-01')]
OPEN=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-09-19','2001-03-29','2007-12-24','2020-03-19','2024-06-07']
CLOSE=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26']
row('open days (Table 1)',[p.date().isoformat() for p,_,_ in opens],OPEN)
row('close days (Table 1)',[p.date().isoformat() for p,_,_ in closes],CLOSE)
row('proposers of the nine opens',[br for _,_,br in opens],['L','V','L','L','W','U','B','K','X'])
NB=[('1969-12','1970-11','1971-06-30','1971-06-30'),('1973-11','1975-03','1976-03-31','1976-12-02'),('1980-01','1980-07','1980-06-03','1981-07-08'),
    ('1981-07','1982-11','1982-01-06','1983-07-08'),('1990-07','1991-03','1991-04-25','1992-12-22'),('2001-03','2001-11','2001-11-26','2003-07-17'),
    ('2007-12','2009-06','2008-12-01','2010-09-20'),('2020-02','2020-04','2020-06-08','2021-07-19'),('2024-04','2024-08',None,None)]
pe=[(pd.Timestamp(OPEN[i])-me(NB[i][0])).days for i in range(9)]; te=[(pd.Timestamp(CLOSE[i])-me(NB[i][1])).days for i in range(9)]
row('days from the peak month end',pe,[-86,-74,-63,-155,50,-2,-7,19,38]); row('median peak days',np.median(pe),-7); row('median trough days',np.median(te),7)
row('peak calls before the month end (six of nine)',sum(1 for x in pe if x<0),6); row('closes within 26 days (eight of nine)',sum(1 for x in te if abs(x)<=26),8)
row('peak month named exactly (2001, 2007)',[NB[i][0] for i in range(9) if OPEN[i][:7]==NB[i][0]],['2001-03','2007-12'])
row('peak month beside (2020)',[NB[i][0] for i in range(9) if abs((fd(OPEN[i][:7]).year-fd(NB[i][0]).year)*12+fd(OPEN[i][:7]).month-fd(NB[i][0]).month)==1],['2020-02'])
row('trough month exact (four)',sum(1 for i in range(9) if CLOSE[i][:7]==NB[i][1]),4)
row('trough month beside (four)',sum(1 for i in range(9) if abs((fd(CLOSE[i][:7]).year-fd(NB[i][1]).year)*12+fd(CLOSE[i][:7]).month-fd(NB[i][1]).month)==1),4)
r=[(pd.Timestamp(OPEN[i])-fd(NB[i][0])).days/MO for i in range(8)]; rt=[(pd.Timestamp(CLOSE[i])-fd(NB[i][1])).days/MO for i in range(8)]
n=[(pd.Timestamp(NB[i][2])-fd(NB[i][0])).days/MO for i in range(8)]; nt=[(pd.Timestamp(NB[i][3])-fd(NB[i][1])).days/MO for i in range(8)]
row('median months, rule at the peak (-0.2)',round(np.median(r),1),-0.2); row('median months, rule at the trough (1.0)',round(np.median(rt),1),1.0)
row('median months, committee at the peak (9.3)',round(np.median(n),1),9.3); row('median months, committee at the trough (15.6)',round(np.median(nt),1),15.6)
for k,v in [(7,4.2),(2,5.1),(6,12.0),(0,18.9),(1,28.9)]: row(f'announcement lag, peak {NB[k][0]}',round(n[k],1),v)
for k,v in [(5,20.5),(4,21.7),(6,15.6),(7,15.6)]: row(f'announcement lag, trough {NB[k][1]}',round(nt[k],1),v)
row('peak announced in or after the trough month (five of eight)',sum(1 for i in range(8) if pd.Timestamp(NB[i][2])>=fd(NB[i][1])),5)
row('four early peak calls, two to five months',sorted([(fd(OPEN[i][:7]).year-fd(NB[i][0]).year)*12+fd(OPEN[i][:7]).month-fd(NB[i][0]).month for i in range(9) if OPEN[i][:7]<NB[i][0]]),[-5,-2,-2,-2])
row('late calls two months after (1990, 2024)',[NB[i][0] for i in range(9) if (fd(OPEN[i][:7]).year-fd(NB[i][0]).year)*12+fd(OPEN[i][:7]).month-fd(NB[i][0]).month==2],['1990-07','2024-04'])
row('closes in the trough month (1980, 1982, 2001, 2009)',[NB[i][1] for i in range(9) if CLOSE[i][:7]==NB[i][1]],['1980-07','1982-11','2001-11','2009-06'])
row('1975 close two months after',(fd(CLOSE[1][:7]).year-fd(NB[1][1]).year)*12+fd(CLOSE[1][:7]).month-fd(NB[1][1]).month,2)
row('1990 later by seven weeks (from Aug 3, 1990)',round((pd.Timestamp('1990-09-19')-pd.Timestamp('1990-08-03')).days/7),7)
row('2024 later by five weeks (from May 3, 2024)',round((pd.Timestamp('2024-06-07')-pd.Timestamp('2024-05-03')).days/7),5)
row('Dec 24, 2007 to the Stimulus Act, days',(pd.Timestamp('2008-02-13')-pd.Timestamp('2007-12-24')).days,51)
row('Mar 19, 2020 to the CARES Act, days',(pd.Timestamp('2020-03-27')-pd.Timestamp('2020-03-19')).days,8)
# ---- 2. the walk: lines, moves, cuts ----
cuts=sorted(CH); row('cuts (sixty-five)',len(cuts),65)
first=CH[cuts[0]]; row('1962 start: low 0.35, ic 60, spr 1.1, look 52, cD 8, hback 12',[first['low'],first['ic'],first['spr'],first['look'],first['cD'],first['hback']],[0.35,60,1.1,52,8,12])
moves={}; prev=None
for c in cuts:
    if prev is not None:
        d={k:(prev[k],CH[c][k]) for k in CH[c] if prev.get(k)!=CH[c][k]}
        if d: moves[c.year]=d
    prev=CH[c]
row('the six moves',sorted(moves),[1972,1977,1981,1982,1984,2002])
row('1972: low .35->.30, spr 1.1->.9, hback 12->9',moves.get(1972),{'low':(0.35,0.3),'spr':(1.1,0.9),'hback':(12,9)})
row('1977: cD 8->6',moves.get(1977),{'cD':(8,6)}); row('1981: low .30->.20',moves.get(1981),{'low':(0.3,0.2)})
row('1982: hback 9->12, cs 15->20',moves.get(1982),{'hback':(9,12),'cs':(15,20)}); row('1984: both back',moves.get(1984),{'hback':(12,9),'cs':(20,15)}); row('2002: ic 60->40',moves.get(2002),{'ic':(60,40)})
row('walk-end lines (Table 2)',{k:pw[k] for k in ('u45','low','wline','wline2','ic','bshare','sahm','vl','hrs','nd','starts','half','hline','spr','kc','cD','cn','cs','hback','look')},
    {'u45':0.45,'low':0.2,'wline':0.4,'wline2':0.6,'ic':40,'bshare':0.6,'sahm':0.3667,'vl':0.2,'hrs':2.0,'nd':1.2,'starts':29,'half':4,'hline':1.0,'spr':0.9,'kc':(35,20),'cD':6,'cn':3,'cs':15,'hback':9,'look':52})
row('ALPHA (85 per cent of the five-year median)',ALPHA,0.85); row('co-signer line 0.2',COS_THR,0.2); row('bands 0.2 / 15',[U_BAND,IC_BAND],[0.2,15])
# ---- 3. the calls' numbers ----
_ic=ICfp.dropna(); w=pd.Timestamp('2020-03-14'); row('claims week ending Mar 14, 2020 (281,000)',int(_ic[w]),281000); row('claims week ending Mar 21, 2020 (3,283,000)',int(_ic[pd.Timestamp('2020-03-21')]),3283000)
low4=_ic.rolling(4).mean().rolling(52,min_periods=52).min().shift(1); med=_ic.rolling(4).mean().rolling(MED_W,min_periods=156).median().shift(1); base=np.maximum(low4,ALPHA*med)
row('Mar 14, 2020 week above base, per cent (37)',round(float((_ic[w]/base[w]-1)*100)),37); row('S&P under its 20-day high at the close before Mar 19, 2020 (29)',round(crash_on(pd.Timestamp('2020-03-19'))),29)
row('release day of the Mar 14, 2020 week',rel_ic(w).date().isoformat(),'2020-03-19')
# the sudden stop's weeks: thirteen 35 per cent weeks 1962-2026, seven outside a recession, the market at most 5.5 per cent off
rel_=((_ic/base-1)*100).dropna(); rel_=rel_[rel_.index>=pd.Timestamp('1962-01-01')]
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))   # the scorer's own window (score13): six months before the peak month to the trough month
# the sudden stop's own arming: a week 35 per cent over the base while armed; re-armed when claims return to the base
eps_=[]; armed=True
for t,v in rel_.items():
    if armed and v>=35-EPS: eps_.append(t); armed=False
    elif not armed and v<=EPS: armed=True
outside=[t for t in eps_ if not in_rec(t)]
row('35 per cent weeks 1962-2026 (thirteen)',len(eps_),13); row('of them outside a recession (seven)',len(outside),7)
row('market at most 5.5 per cent off on those (max)',round(max(crash_on(rel_ic(t)) for t in outside),1),5.5,0.05)
# August 2022: 44 per cent above the 52-week low, 31 above the base, the low 22 per cent under the five-year median
m4=_ic.rolling(4).mean(); t22=m4[(m4.index>='2022-07-01')&(m4.index<='2022-09-01')]
lowonly=(m4/low4-1)*100; onbase=(m4/base-1)*100; under=(1-low4/med)*100
tt=onbase[(onbase.index>='2022-07-01')&(onbase.index<='2022-09-01')].idxmax()
row('Aug 2022 claims above the 52-week low, per cent (44)',round(float(lowonly[tt])),44); row('Aug 2022 claims above the base, per cent (31)',round(float(onbase[tt])),31)
row('the low under the five-year median, per cent (22)',round(float(under[tt])),22)
# November 2024 job openings: first print 8.10 million, revised file 7.57 million
_o=alfred_first('JTSJOL') if 'alfred_first' in dir() else None
try:
    fp=pd.read_csv('cache/alfred_first_JTSJOL.csv',index_col=0,parse_dates=True).iloc[:,0]
    row('Nov 2024 openings, first print (8.10 million)',round(float(fp[pd.Timestamp('2024-11-01')])/1000,2),8.10,0.005)
except Exception as e: row('Nov 2024 openings, first print (8.10 million)','no file',8.10)
try:
    cur=VINT['JTSJOL'][sorted(VINT['JTSJOL'])[-1]]; row('Nov 2024 openings, latest vintage (7.57 million)',round(float(cur[pd.Timestamp('2024-11-01')])/1000,2),7.57,0.01)
except Exception as e: row('Nov 2024 openings, latest vintage (7.57 million)','no vintage',7.57)
# 1984: February 1984 starts first print 2,197 and 2,262 as revised by 19 September 1984; 27.4 log points; 0.945 of the line
Mh=VINT['HOUST']; vds=sorted(Mh); feb=pd.Timestamp('1984-02-01')
first_feb=[Mh[v][feb] for v in vds if feb in Mh[v].index][0]; sep19=[v for v in vds if v<=pd.Timestamp('1984-09-19')][-1]; s=Mh[sep19]
row('Feb 1984 starts, first print (2,197)',int(round(first_feb)),2197); row('Feb 1984 starts as of 19 Sep 1984 (2,262)',int(round(s[feb])),2262)
L=np.log(s)*100; hh=(L.rolling(12).max()-L.rolling(3).mean()); row('Aug 1984 starts below the 12-month high as of 19 Sep 1984, log points (27.4)',round(float(hh[pd.Timestamp('1984-08-01')]),1),27.4,0.05)
row('0.945 of the line',round(float(hh[pd.Timestamp('1984-08-01')])/29,3),0.945,0.0005)
# frozen 1948-2026 at the walk-end lines: thirteen and nothing else; the four pre-1962 months
r13,t13=build_v(pw)
row('frozen 1948-2026: recessions called',len(r13['lags_p']),13); row('frozen: calls outside a recession',len(r13['other']),0)
pre=[(x['published'].strftime('%Y-%m'),x['kind']) for x in t13 if x['published']<pd.Timestamp('1962-01-01')]
row('pre-1962 opens (Oct 1948, Oct 1953, Sep 1957, Jul 1960)',[p for p,k in pre if k=='peak'],['1948-10','1953-10','1957-09','1960-07'])
row('pre-1962 closes (Mar 1950, Jun 1954, Jul 1958, May 1961)',[p for p,k in pre if k=='trough'],['1950-03','1954-06','1958-07','1961-05'])
# the closer: the S&P 500 stood the required distance above its 26-week low in all nine closes; standing closed
row('standing closed since Sep 26, 2024',[p.date().isoformat() for p,_,_ in closes][-1],'2024-09-26')
row('no call after Sep 26, 2024',len([p for p,k,d,br in LOG if pd.Timestamp(p)>pd.Timestamp('2024-09-26')]),0)
# ---- 4. the data audit's counts, from the audit's own output (AUDIT-v321, 8 Sep 2026) where it exists ----
try:
    au=open('out/audit/summary.txt').read()
    for lab,val in [('3,113 weeks of initial claims','3113'),('2,904 of the insured rate','2904'),('797 months of the unemployment rate','797'),('787 of housing starts','787'),('777 of hours and employment','777')]:
        row(lab+' (audit output)',val in au,True)
except Exception:
    print('NOTE data-audit counts (3,113 / 2,904 / 797 / 787 / 777 / four weeks) are quoted from AUDIT-v321-2026-09-08.md; out/audit/summary.txt not found')
# ---- write the record ----
ok=all(x[3] for x in ROWS); today=_dt.date.today().isoformat()
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
L_=[f"# The executive summaries, verified — v3.26, {today}",'',f"Walk `walk46.py`; diary `cache/w46_prog.pkl` (sha256 {sha('cache/w46_prog.pkl')}); walk-end lines `cache/w46_carry.pkl` (sha256 {sha('cache/w46_carry.pkl')}); this script sha256 {sha('s2/verify_paper.py')}; the texts `scripts/two_pager/paper1/2/3/5_text.js`.",'',
    '| row | got | expected | |','|---|---|---|---|']+[f"| {n} | {g} | {e} | {'PASS' if k else 'FAIL'} |" for n,g,e,k in ROWS]+['',f"{sum(1 for x in ROWS if x[3])} of {len(ROWS)} rows pass."]
open(f'../RECORD-PAPER-v326-{today}.md','w').write('\n'.join(L_))
print(f"{sum(1 for x in ROWS if x[3])}/{len(ROWS)} PASS -> ../RECORD-PAPER-v326-{today}.md"); sys.exit(0 if ok else 1)
