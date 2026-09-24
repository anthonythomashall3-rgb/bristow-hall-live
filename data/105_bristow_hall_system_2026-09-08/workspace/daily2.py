"""EVERY daily and weekly series held in the programme's own store (194 files) swept as an extra CONFIRMER, mechanically.
For each series and each window, the reading is the fall from its trailing maximum and the rise from its trailing minimum; the line is set
construction-grade — just above the highest reading that occurs inside the window of any QUIET proposal — and the configuration is kept only
if it makes no other call on either vintage and buys at least one day. Published the next day."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily2.out','w')"))
import glob
files=sorted(glob.glob(os.path.join(DD,'fred_daily','*.csv'))+glob.glob(os.path.join(DD,'extra','*.csv')))
P("daily/weekly files held:",len(files))
# the quiet proposal months whose windows a confirmer must not cover, and the recession windows it may
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
P("quiet proposal months a confirmer must not cover:",len(QP),[d.strftime('%Y-%m') for d in QP])
def wseg(G,dd,back=6,fwd=4):
    lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0)
    return G[(G.index>=lo)&(G.index<=hi)]
cands=[]
for f in files:
    nm=os.path.basename(f)[:-4]
    try:
        x=pd.read_csv(f); x.columns=['d','v']; x['d']=pd.to_datetime(x['d']); s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
    except Exception: continue
    if len(s)<500: continue
    step=float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int)))
    if step>9: continue
    per=max(1,int(round(step)))
    for wmon in [3,6,12]:
        win=max(4,int(wmon*30/per))
        for kind in ['fall','rise']:
            G=((s.rolling(win).max()-s) if kind=='fall' else (s-s.rolling(win).min())).dropna()
            if len(G)<300: continue
            qmax=max([float(wseg(G,dd).max()) for dd in QP if len(wseg(G,dd))]+[-9e9])
            if qmax<=-9e8: continue
            line=qmax*1.02 if qmax>0 else 0.01
            rec=[float(wseg(G,PK[i]).max()) if len(wseg(G,PK[i])) else np.nan for i in range(13)]
            n_ok=sum(1 for r in rec if not np.isnan(r) and r>=line)
            if n_ok>=3: cands.append((nm,kind,wmon,win,round(line,4),n_ok,round(qmax,4)))
P("candidate confirmers that clear every quiet window and still fire in three or more recessions:",len(cands))
for c in sorted(cands,key=lambda c:-c[5])[:40]: P("   ",c)
import pickle; pickle.dump(cands,open('cache/daily_cands.pkl','wb'))
out.close()
