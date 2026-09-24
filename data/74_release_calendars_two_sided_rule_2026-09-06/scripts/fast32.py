"""SHELF SWEEP of every monthly first-print series held in 27_realtime_vintages (ALFRED, 135 series) as the demand half of the low branch's
pair, in place of housing starts: demand reading D = 12-month max minus 2-month mean (log points x100 for level series; points for rates),
paired in real time (latest published reading of each half, on ALFRED first-release dates) with the unemployment rate four tenths above its
12-month low. For each series the construction-grade line is the largest quiet reading inside any low-branch proposal window (both vintages,
plus the Fieldhouse-era windows), and the record is the first firing inside the 1973, 1981, 1990 and 2007 windows against the current calls
(4 Jan 1974, 2 Oct 1981, 19 Sep 1990, 20 Feb 2008 / 20 Mar 2008 fp)."""
from mini import *
from legu_min import s_cur, spl
import csv, os, warnings; warnings.filterwarnings('ignore')
exec(open('fast30.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast30.out','w')","out=open('fast32.out','w')"))
from relcal import release_calendar
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
QP=sorted(set([dd for p,dd in leg_gapx(s_cur,0.25,rearm='window') if not inw(dd)]+[dd for p,dd in leg_gapx(spl,0.25,rearm='window') if not inw(dd)]+[dd for p,dd in FH25 if not inw(dd)]))
RW={1973:(pd.Timestamp('1973-05-01'),pd.Timestamp('1975-03-01')),1981:(pd.Timestamp('1981-01-01'),pd.Timestamp('1982-11-01')),1990:(pd.Timestamp('1990-01-01'),pd.Timestamp('1991-03-01')),2007:(pd.Timestamp('2007-06-01'),pd.Timestamp('2009-06-01'))}
CUR={1973:pd.Timestamp('1974-01-04'),1981:pd.Timestamp('1981-10-02'),1990:pd.Timestamp('1990-09-19'),2007:pd.Timestamp('2008-02-20')}
PROP={1973:pd.Timestamp('1973-12-27'),1981:pd.Timestamp('1981-09-24'),1990:pd.Timestamp('1990-08-09'),2007:pd.Timestamp('2008-01-10')}
def rt_reading(dem,reld):
    """real-time combined reading: at every release of either half, R = D(latest) if rate4(latest)>=1 else 0; keyed by the later data month"""
    ev=[(reld[m],'D',m) for m in dem.index if m in reld.index]+[(relU[m],'U',m) for m in rate4.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; R=[]
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        dv=dem.get(lastD,np.nan); rv=rate4.get(lastU,np.nan)
        if np.isnan(dv) or np.isnan(rv): continue
        R.append((d,max(lastD,lastU),dv if rv>=1.0 else 0.0))
    return R
res=[]
names=sorted(f.replace('_all_vintages.csv','') for f in os.listdir(AL))
for nm in names:
    if nm in ('UNRATE','ICSA','CCSA','SAHMCURRENT','SAHMREALTIME','USREC','RECPROUSM156N','GDPNOW','MORTGAGE30US','FEDFUNDS','GS10','GS2','TB3MS','AAA','BAA','KCFSI','STLFSI4'): continue
    try:
        fp=first_prints(nm); cal=release_calendar(nm); reld=cal['first_release']; reld=reld[reld.index>=cal.index[0]+pd.DateOffset(months=13)]
        if len(fp)<120: continue
        step=(fp.index[1:]-fp.index[:-1]).days.min()
        if step>45 or step<25: continue    # monthly only
        pos=(fp>0).all() and fp.abs().median()>20
        l=np.log(fp)*100 if pos else fp.astype(float)
        D=(l.rolling(12).max()-l.rolling(2).mean()).dropna()
        R=rt_reading(D,reld)
        if not R: continue
        # quiet maximum inside low-branch proposal windows (dated month -6 .. +4)
        Q=0.0; Qm=None
        for d,key,v in R:
            if any(q-pd.DateOffset(months=6)<=key<=q+pd.DateOffset(months=4) for q in QP) and v>Q: Q=v; Qm=key
        X=Q*1.02 if Q>0 else 0.01
        row=dict(series=nm,unit='log' if pos else 'pts',quiet_max=round(Q,2),quiet_at=Qm.strftime('%Y-%m') if Qm is not None else '',line=round(X,2))
        gain=0
        for y,(a,b) in RW.items():
            f=[d for d,key,v in R if a<=key<=b and v>=X]
            if f:
                fd=min(f); call=max(fd,PROP[y]); row[str(y)]=f"{call:%Y-%m-%d}"+("*" if call<CUR[y] else ""); gain+=(call<CUR[y])
            else: row[str(y)]='-'
        row['gain']=gain; res.append(row)
    except Exception as e:
        P(f"skip {nm}: {e}"); continue
df=pd.DataFrame(res).sort_values(['gain','quiet_max'],ascending=[False,True])
P(df.to_string(index=False))
df.to_csv('cache/shelf_sweep_lowbranch.csv',index=False)
out.close()
