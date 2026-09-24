"""TURN-TARGETED SWEEP. 1960 (+91) waits on the vacancy for June 1960, published 30 July 1960; 1969 (+37) waits on the
housing x rate pair for January 1970, published 6 February 1970. For every series in the whole shelf, at every reading
and window, the question is: does it clear EVERY quiet proposal window on the record, and does it stand at its line
inside the turn's own window EARLY ENOUGH to beat the binding confirmer?"""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily11.out','w')"))
import glob
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw(dd)})
def wseg(G,dd,back=6,fwd=4):
    lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0); return G[(G.index>=lo)&(G.index<=hi)]
TARG=[('1960',pd.Timestamp('1960-04-01'),pd.Timestamp('1960-07-30')),('1969',pd.Timestamp('1969-12-01'),pd.Timestamp('1970-02-06')),
      ('1981',pd.Timestamp('1981-07-01'),pd.Timestamp('1981-09-24')),('1953',pd.Timestamp('1953-07-01'),pd.Timestamp('1953-09-30')),
      ('1957',pd.Timestamp('1957-08-01'),pd.Timestamp('1957-10-10')),('2024',pd.Timestamp('2024-04-01'),pd.Timestamp('2024-08-02'))]
files=sorted(glob.glob(os.path.join(C25,'fred_daily','*.csv')))+sorted(glob.glob(os.path.join(C25,'fred_weekly','*.csv')))
files=[f for f in files if not os.path.basename(f).startswith('_')]
import sys
I0=int(sys.argv[1]); files=files[I0:I0+int(sys.argv[2])]
hits={k:[] for k,_,_ in TARG}
for f in files:
    nm=os.path.basename(f)[:-4]
    if nm.endswith(('RECD','RECDM','RECDP','RECPR')) or nm in ('CC','ICSA','IURSA','CCSA','CC4WSA','ICNSA','CCNSA','IURNSA','IC4WSA'): continue
    try:
        x=pd.read_csv(f).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
        s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); s=s[s.index.notna()]
    except Exception: continue
    if len(s)<300: continue
    step=float(np.median(np.diff(s.index.values).astype('timedelta64[D]').astype(int)))
    if step>16 or step<=0: continue
    per=max(1,int(round(step)))
    for wmon in [3,6,12]:
        win=max(4,int(wmon*30/per))
        for kind in ['fall','rise']:
            G=((s.rolling(win).max()-s) if kind=='fall' else (s-s.rolling(win).min())).dropna()
            if len(G)<200: continue
            segs=[float(wseg(G,dd).max()) for dd in QP if len(wseg(G,dd))]
            if not segs: continue
            line=max(segs)*1.02 if max(segs)>0 else 0.01
            for k,dd,bind in TARG:
                w=wseg(G,dd); h=w[w>=line]
                if len(h) and h.index[0]+pd.Timedelta(days=1)<bind:
                    hits[k].append((nm,kind,wmon,round(line,4),str(h.index[0].date()),len(segs),(bind-h.index[0]).days-1))
for k,_,_ in TARG:
    P(f"\n--- {k}: objects that clear every quiet window they cover AND stand at their line early enough ({len(hits[k])}) ---")
    for h in sorted(hits[k],key=lambda h:(-h[5],-h[6]))[:25]: P("   ",h)
out.close()
