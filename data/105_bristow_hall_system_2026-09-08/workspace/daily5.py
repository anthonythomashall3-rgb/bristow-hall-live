"""THE WHOLE DAILY AND WEEKLY SHELF (collection 25: 11,481 daily + 3,631 weekly FRED series, every observation, plus the
non-FRED daily sources) swept as an extra CONFIRMER, mechanically and with no series named in advance. Same screen as
daily2.py: the reading is the fall from a trailing maximum and the rise from a trailing minimum; the line is set
construction-grade, just above the highest reading inside the window of any QUIET proposal; a candidate survives only if
it clears every quiet window it covers and still fires inside at least three recession windows."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily5_%s.out'%sys.argv[1],'w')"))
import glob, pickle, time, sys
I0=int(sys.argv[1]); NN=int(sys.argv[2])
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
files=sorted(glob.glob(os.path.join(C25,'fred_daily','*.csv')))+sorted(glob.glob(os.path.join(C25,'fred_weekly','*.csv')))+sorted(glob.glob(os.path.join(C25,'fred_biweekly','*.csv')))
files=[f for f in files if not os.path.basename(f).startswith('_')]
P("collection 25 daily/weekly/biweekly files:",len(files))
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
P("quiet proposal months a confirmer must not cover:",len(QP))
BAD=('RECD','RECDM','RECDP','RECPR')
def wseg(G,dd,back=6,fwd=4):
    lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0)
    return G[(G.index>=lo)&(G.index<=hi)]
def sweep(nm,s):
    out=[]
    if len(s)<500: return out
    step=float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int)))
    if step>16 or step<=0: return out
    per=max(1,int(round(step)))
    for wmon in [3,6,12]:
        win=max(4,int(wmon*30/per))
        for kind in ['fall','rise']:
            G=((s.rolling(win).max()-s) if kind=='fall' else (s-s.rolling(win).min())).dropna()
            if len(G)<300: continue
            segs=[float(wseg(G,dd).max()) for dd in QP if len(wseg(G,dd))]
            if not segs: continue
            qmax=max(segs); nq=len(segs)
            line=qmax*1.02 if qmax>0 else 0.01
            rec=[float(wseg(G,PK[i]).max()) if len(wseg(G,PK[i])) else np.nan for i in range(13)]
            n_ok=sum(1 for r in rec if not np.isnan(r) and r>=line)
            if n_ok>=3: out.append((nm,kind,wmon,win,round(line,6),n_ok,round(qmax,6),nq,str(G.index.min().date())))
    return out
files=files[I0:I0+NN]
cands=[]; t0=time.time(); n=0
for f in files:
    nm=os.path.basename(f)[:-4]; n+=1
    if any(nm.endswith(b) for b in BAD): continue
    try:
        x=pd.read_csv(f)
        if x.shape[1]<2: continue
        x=x.iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
        s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
        s=s[s.index.notna()]
    except Exception: continue
    cands+=sweep(nm,s)
    if n%1000==0: P(f"   {n} files, {len(cands)} configurations, {time.time()-t0:.0f}s"); out.flush()
if I0==0:
    for nm,f in [('SP500','other_daily/sp500_daily_yahoo.csv'),('ADS','other_daily/ads_index_current.csv'),('OFRFSI','other_daily/ofr_fsi.csv')]:
        p=os.path.join(C25,f)
        if not os.path.exists(p): P(f"   {nm}: not held"); continue
        x=pd.read_csv(p); x.columns=[c.strip().lower() for c in x.columns]
        dc=[c for c in x.columns if c in ('date','d','index','observation_date')] or [x.columns[0]]
        vc=[c for c in x.columns if c in ('close','adj close','value','ads_index','ofr fsi','fsi')] or [x.columns[1]]
        x[dc[0]]=pd.to_datetime(x[dc[0]],errors='coerce',utc=True).dt.tz_localize(None)
        s=pd.to_numeric(x.set_index(dc[0])[vc[0]],errors='coerce').dropna()
        if nm=='SP500': s=np.log(s)*100
        P(f"   {nm} ({vc[0]}): {s.index.min().date()} -> {s.index.max().date()}, {len(s)} obs")
        cands+=sweep(nm,s)
P("\nconfigurations that clear every quiet window they cover and fire in three or more recessions:",len(cands))
for c in sorted(cands,key=lambda c:(-c[5],c[0]))[:400]: P("   ",c)
pickle.dump(cands,open('cache/daily5_cands_%s.pkl'%sys.argv[1],'wb'))
P("\nelapsed",round(time.time()-t0),"s")
out.close()
