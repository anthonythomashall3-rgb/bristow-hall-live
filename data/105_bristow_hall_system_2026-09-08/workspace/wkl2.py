"""THE SURVEY-WEEK PROPOSER. The unemployment rate for a month is published on the first Friday of the next; the
insured rate for the week the household survey covers - the week containing the twelfth - is published about twelve
days after that week ends, which is earlier. One reading a month, taken from the survey week, removes the weekly noise
that made the full weekly proposer useless, and keeps the earlier clock. Swept as a proposer against the same confirmers."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('wkl2.out','w')"))
D=W+'/lab/data/fred_weekly'
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
IURW=pd.concat([own[own.index<frd.index.min()],frd]).sort_index()
CC=pd.read_csv(D+'/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
def survey(s):
    """one reading a month: the week whose Saturday-ending date is nearest the survey week containing the twelfth"""
    rows={}
    for t,v in s.items():
        m=pd.Timestamp(t.year,t.month,1)
        tgt=pd.Timestamp(t.year,t.month,12)
        d=abs((t-tgt).days)
        if m not in rows or d<rows[m][0]: rows[m]=(d,v,t)
    idx=sorted(rows); return pd.Series([rows[m][1] for m in idx],index=idx), pd.Series([rows[m][2] for m in idx],index=idx)
SI,SW=survey(IURW); SC,SWC=survey(CC)
P(f"survey-week insured rate: {SI.index.min():%Y-%m} to {SI.index.max():%Y-%m}, {len(SI)} months")
rel_m={m:(rel[m] if m in rel.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)) for m in SI.index}
gain=[(rel_m[m]-(SW[m]+pd.Timedelta(days=12))).days for m in SI.index if m in rel_m]
P(f"days the survey-week reading beats the employment report, median {np.median(gain):.0f}, quartiles {np.percentile(gain,25):.0f} and {np.percentile(gain,75):.0f}, worst {min(gain)}")
def leg_sv(s,sw,line,look=52,pub=12,rearm='window'):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((sw[t]+pd.Timedelta(days=pub),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def leg_svp(s,sw,pct,look=52,pub=12,rearm='window'):
    gap=((s/s.rolling(look,min_periods=look).min().shift(1)-1)*100).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=pct: c.append((sw[t]+pd.Timedelta(days=pub),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<pct and t>=last+pd.DateOffset(months=4): armed=True
    return c
def inwin(dd): return any(pk-pd.DateOffset(months=6)<=dd<=tr for pk,tr in zip(PK,TR))
p=dict(BASE)
G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs); Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
def sweep(nm,mk,lines):
    P(f"\n{nm}\n{'line':>6s} {'rearm':7s} {'props':>6s} {'quiet':>6s} {'quiet calls':>11s}   lag in each recession window from 1969")
    for line in lines:
        for rear in ('zero','window'):
            pr=mk(line,rear); q=[x for x in pr if not inwin(x[1])]
            cf=confirm_w(pr,[Hc,SP,Vc,Hh],'month'); qc=[(a,b) for a,b,c in cf if not inwin(b)]
            firsts=[]
            for pk,tr in zip(PK,TR):
                h=[(a,b) for a,b,c in cf if pk-pd.DateOffset(months=6)<=b<=tr]
                firsts.append(f"{pk:%Y-%m}:{(h[0][0]-me(pk)).days:+d}" if h else f"{pk:%Y-%m}:-")
            P(f"{line:6.2f} {rear:7s} {len(pr):6d} {len(q):6d} {len(qc):11d}   "+" ".join(firsts[4:]))
sweep('survey-week insured rate, points above the trailing minimum',lambda l,r: leg_sv(SI,SW,l,rearm=r),[0.8,0.6,0.5,0.45,0.4,0.35,0.3,0.25,0.2])
sweep('survey-week continued claims, per cent above the trailing minimum',lambda l,r: leg_svp(SC,SWC,l,rearm=r),[25,20,15,12.5,10,7.5,5])
out.close()
