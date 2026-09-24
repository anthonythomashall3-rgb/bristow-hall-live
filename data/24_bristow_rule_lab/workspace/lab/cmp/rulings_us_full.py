"""Rule 18 item 4 / Rule 11 for the United States: every American turning point scored against the
committee AND against the median of independent published rulings, so that a date the independent
rulings share with the rule is reported as a divergence from the committee, not as a miss.

Rulings, each read from its own source on 3 September 2026 (Rule 15: first-hand):

  SW10   Stock and Watson, "Estimating Turning Points Using Large Data Sets", NBER WP 16532
         (November 2010), Tables 2 and 3 (pdftotext of Recession Papers/Claude RA/stock_watson_w16532.pdf).
         Table 2 = average-then-date chronologies (Bry-Boschan on the Conference Board, ISD and DFM
         coincident indexes and on three monthly GDP series); Table 3 = date-then-average chronologies
         over 270 disaggregated monthly series (mean, median, mode; standard errors in parentheses).
         SIGN: the tables' note says "NBER minus series", but the paper's own text settles the sign the
         other way - "the date-then-average methods in Table 3 all date the 1969:12 NBER peak as having
         occurred between 1.3 and 2.4 months earlier, so that the peak would be 1969:10" against Table 3
         entries of -2.2/-2.0/-2.3, and "the weighted mode estimator places the 2007:12 peak six months
         earlier" against -6.1; so an entry is (method date - NBER date) in months, negative = earlier.
  CP08   Chauvet and Piger, JBES 26(1) 2008, Tables 1-3 (pdftotext of Claude RA/chauvet_piger_2008.pdf):
         the DFMS model's real-time dates, its final (latest-vintage) dates, and the MHP algorithm's
         real-time dates, four contractions 1980-2001.
  CPH    Chauvet-Hamilton / Piger smoothed recession probabilities, FRED RECPROUSM156N (1967-06 on):
         a recession month is p >= 50; peak = the last month before the run, trough = the last month of
         the run.  The series never reaches 50 in 2001 and splits 1969-70 and 1981-82 (memo section 8e).
  HAM    Hamilton's GDP-based recession indicator, FRED JHDUSRGDPBR (quarterly, 1967-Q4 on): peak = the
         quarter before the run, trough = the last quarter of the run, quarters at their middle month.
  PHI    Bry-Boschan (the tool's) on the Philadelphia Fed coincident index USPHCI, 1979 on.
  BBP    Bry-Boschan on the tool's own United States panel, the median of channel dates (the memo's
         section 9 benchmark); the program's computation, shown apart from the published rulings.
  BBQ    Harding-Pagan on quarterly real GDP (GDPC1), the program's computation: local extrema over
         two quarters each side, alternation, minimum phase two quarters, minimum cycle five.
  OECD   the OECD-based growth-cycle turning points (FRED USARECDM): a different concept, printed for
         the record and left out of the median (memo section 8e treats it the same way).
  RR19   Romer and Romer, "NBER Business Cycle Dating: Retrospect and Prospect" (December 2019), section
         IV.D and Table 1: quarter-level verdicts on four episodes from their two-regime model and the
         slack series - the start of the 1973-75 recession ("cast particular doubt on the first quarter",
         1973Q4, i.e. later), 1990 ("supportive of moving the start one quarter earlier"), 2001 ("the
         two-regime model prefers 2001Q3 to 2001Q2"; the other variables disagree), 2007-09 (the data
         "cast doubt on the classification of 2008Q1 as part of the recession").  Text evidence only.

The independent median at each end is taken over the PUBLISHED monthly rulings that reach it
(SW10 Table 2 columns, SW10 Table 3 median, CP08 DFMS real-time and final, CP08 MHP, CPH, PHI).
The rule's dates are the shipped tool's on the shipped panel, exactly as tool_check.py and
monthly_ends_all.py produce them (refinement clause in force).
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd
import bristow_rule_v3 as B
import bench
from bench import PANELS, channels, ep3, ts, quantity, dating_series, md
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
HERE='/home/claude/lab/cmp'
NBER=[('1948-11','1949-10'),('1953-07','1954-05'),('1957-08','1958-04'),('1960-04','1961-02'),
      ('1969-12','1970-11'),('1973-11','1975-03'),('1980-01','1980-07'),('1981-07','1982-11'),
      ('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]
def T(s): return pd.Timestamp(s+'-01')

# ---------- the rule, shipped ----------
def rule_dates():
    c='United States'; cfg=PANELS[c]
    chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    out={}
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        vol=quantity(c,use) or use
        r=B.date_turning_points(use,w0,w1,volume_channels=vol,concept='level',lam=500000.0,
                                band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12,
                                dating_series=dating_series(c,w0,trm))
        out[pk_off[:7]]=(md(r['peak'],pkm) if r['peak'] is not None else None,
                         md(r['trough'],trm) if r['trough'] is not None else None)
    return out

# ---------- published rulings, transcribed (method minus NBER, months) ----------
# Stock-Watson 2010 Table 2: rows 1960:4 P ... 2009:6 T; columns CI-TCB, CI-ISD, CI-DFM, GDP(E), GDP(I), GDP(Avg)
SW_T2={ # (peak, trough) per contraction; None = the series has no Bry-Boschan turn there ("-")
 '1960-04':{'TCB':(-2,0),'ISD':(0,0),'DFM':(None,0),'GDPE':(-1,-2),'GDPI':(-2,-2),'GDPA':(-1,-2)},
 '1969-12':{'TCB':(-2,0),'ISD':(-2,0),'DFM':(-4,0),'GDPE':(-4,-10),'GDPI':(None,None),'GDPA':(-4,0)},
 '1973-11':{'TCB':(0,1),'ISD':(0,1),'DFM':(0,1),'GDPE':(1,0),'GDPI':(0,-1),'GDPA':(1,0)},
 '1980-01':{'TCB':(0,0),'ISD':(0,0),'DFM':(-10,0),'GDPE':(None,None),'GDPI':(0,-1),'GDPA':(None,None)},
 '1981-07':{'TCB':(0,0),'ISD':(1,0),'DFM':(0,0),'GDPE':(2,-6),'GDPI':(1,0),'GDPA':(2,-3)},
 '1990-07':{'TCB':(-1,0),'ISD':(-1,0),'DFM':(0,0),'GDPE':(0,0),'GDPI':(0,-2),'GDPA':(0,-2)},
 '2001-03':{'TCB':(-6,4),'ISD':(-6,0),'DFM':(-6,0),'GDPE':(None,None),'GDPI':(0,-1),'GDPA':(None,None)},
 '2007-12':{'TCB':(-1,0),'ISD':(0,0),'DFM':(0,0),'GDPE':(1,0),'GDPI':(-12,1),'GDPA':(0,0)},
}
# Stock-Watson 2010 Table 3, "No adjustments": (mean, median, mode) and their standard errors, per end
SW_T3={
 '1960-04':{'P':((-1.8,-2.0,-1.4),(0.6,0.7,0.5)),'T':((-0.3,0.0,-0.5),(0.4,0.6,0.7))},
 '1969-12':{'P':((-2.2,-2.0,-2.3),(0.7,0.6,0.4)),'T':((1.2,0.0,-0.2),(0.6,0.7,0.4))},
 '1973-11':{'P':((1.3,2.0,1.6),(0.6,0.6,0.3)),'T':((1.0,0.0,0.4),(0.3,0.3,0.3))},
 '1980-01':{'P':((-1.8,-1.0,-0.3),(0.7,0.8,0.4)),'T':((-0.9,0.0,-0.5),(0.5,0.4,0.2))},
 '1981-07':{'P':((-0.7,0.0,-0.1),(0.5,0.5,0.3)),'T':((-0.6,0.0,1.1),(0.6,0.6,0.4))},
 '1990-07':{'P':((-0.8,0.0,0.3),(0.6,0.7,0.5)),'T':((2.1,1.0,0.4),(0.5,0.4,0.3))},
 '2001-03':{'P':((-3.7,-3.0,-2.2),(0.5,0.6,0.3)),'T':((0.2,1.0,0.6),(0.5,0.5,0.2))},
 '2007-12':{'P':((-1.0,-1.0,-6.1),(0.5,0.9,0.5)),'T':((1.7,1.0,-0.1),(0.3,0.5,0.2))},
}
# Chauvet-Piger 2008, Tables 1-3 (dates as printed; errors computed here as method minus NBER)
CP08={ # contraction: {ruling: (peak date, trough date)}
 '1980-01':{'DFMS_rt':('1980-01','1980-06'),'DFMS_final':('1980-01','1980-06'),'MHP_rt':('1979-07','1980-07')},
 '1981-07':{'DFMS_rt':('1981-08','1982-10'),'DFMS_final':('1981-07','1982-11'),'MHP_rt':('1981-05','1982-10')},
 '1990-07':{'DFMS_rt':('1990-07','1991-03'),'DFMS_final':('1990-08','1991-03'),'MHP_rt':('1990-07','1991-07')},
 '2001-03':{'DFMS_rt':('2001-01','2001-11'),'DFMS_final':('2000-11','2001-11'),'MHP_rt':('2000-09','2001-10')},
}
RR19={'1973-11':'start later (doubt on 1973Q4)','1990-07':'start one quarter earlier (1990Q2)',
      '2001-03':'model prefers 2001Q3; other series say 2001Q2','2007-12':'doubt on 2008Q1 (later start)'}

# ---------- computed rulings ----------
def fred(name):
    d=pd.read_csv(f'{HERE}/{name}.csv'); d.columns=['d','v']; d['d']=pd.to_datetime(d.d)
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().set_index('d')['v']
def runs(flag):
    out=[]; on=False; start=None; idx=flag.index; v=flag.values
    for i in range(len(v)):
        if v[i] and not on: on=True; start=i
        elif not v[i] and on: on=False; out.append((idx[start-1] if start>0 else idx[start], idx[i-1]))
    if on: out.append((idx[start-1], idx[-1]))
    return out
def nearest_pair(pairs, ref, tol=9):
    best=None
    for p,t in pairs:
        e=md(p,ref[0])
        if abs(e)<=tol and (best is None or abs(e)<abs(best[0])): best=(e,md(t,ref[1]))
    return best
def pairs_from_tp(tp):
    out=[]
    for i in range(len(tp)-1):
        if tp[i][1]=='P' and tp[i+1][1]=='T': out.append((tp[i][0],tp[i+1][0]))
    return out
def bbq_quarterly(g, k=2, min_phase=2, min_cycle=5):
    """Harding-Pagan BBQ on a quarterly series: local max/min over k quarters each side,
    alternation, minimum phase, minimum cycle; returns [(quarter start, 'P'/'T')]."""
    v=g.values; idx=g.index; tp=[]
    for i in range(k,len(v)-k):
        w=v[i-k:i+k+1]
        if v[i]==w.max() and (w<v[i]).sum()==2*k: tp.append((i,'P'))
        elif v[i]==w.min() and (w>v[i]).sum()==2*k: tp.append((i,'T'))
    def alternate(tp):
        out=[]
        for i,kd in tp:
            if out and out[-1][1]==kd:
                j,_=out[-1]
                keep = (i if (v[i]>v[j] if kd=='P' else v[i]<v[j]) else j)
                out[-1]=(keep,kd)
            else: out.append((i,kd))
        return out
    tp=alternate(tp)
    changed=True
    while changed and len(tp)>1:
        changed=False
        for a in range(len(tp)-1):
            if tp[a+1][0]-tp[a][0]<min_phase: del tp[a:a+2]; changed=True; break
        if not changed:
            for a in range(len(tp)-2):
                if tp[a+2][0]-tp[a][0]<min_cycle: del tp[a+1:a+3]; changed=True; break
        tp=alternate(tp)
    return [(idx[i],kd) for i,kd in tp]

cph=fred('RECPROUSM156N'); cph_pairs=runs(cph>=50.0)
ham=fred('JHDUSRGDPBR'); ham_pairs=[(pd.Timestamp(p.year,p.month+1,1),pd.Timestamp(t.year,t.month+1,1)) for p,t in runs(ham>=1)]
phi=fred('USPHCI'); phi_pairs=pairs_from_tp(B.bry_boschan(phi.astype(float),smooth=3))
oecd=fred('USARECDM'); oecd_m=oecd.resample('MS').first(); oecd_pairs=runs(oecd_m>=1)
gdp=pd.read_csv('/home/claude/a20/GDPC1.csv'); gdp.columns=['d','v']; gdp['d']=pd.to_datetime(gdp.d); gdp=gdp.set_index('d')['v'].astype(float)
bbq_tp=bbq_quarterly(gdp); bbq_pairs=[(pd.Timestamp(p.year,p.month+1,1),pd.Timestamp(t.year,t.month+1,1)) for p,t in pairs_from_tp(bbq_tp)]
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
def bb_panel(pkm,trm,smooth=3):
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12); ps=[];tsx=[]
    for nm,s in chs:
        if s.index.min()>w0 or s.index.max()<w1: continue
        tp=B.bry_boschan(s[w0-pd.DateOffset(months=24):w1+pd.DateOffset(months=24)].astype(float),smooth=smooth)
        pp=[d for d,k in tp if k=='P' and w0<=d<=w1]; tt=[d for d,k in tp if k=='T' and w0<=d<=w1]
        if pp: ps.append(min(pp,key=lambda d:abs(md(d,pkm))))
        if tt: tsx.append(min(tt,key=lambda d:abs(md(d,trm))))
    return ((md(B._median(ps),pkm) if ps else None),(md(B._median(tsx),trm) if tsx else None))

if __name__=='__main__':
    R=rule_dates()
    rows=[]
    for pk,tr in NBER:
        ref=(T(pk),T(tr)); k=pk
        pub={}   # published monthly rulings: name -> (peak err, trough err)
        if k in SW_T2:
            for col,(pe,te) in SW_T2[k].items(): pub[f'SW10 {col}']=(pe,te)
            mp,mt=SW_T3[k]['P'][0][1],SW_T3[k]['T'][0][1]; pub['SW10 DTA median']=(mp,mt)
        if k in CP08:
            for nm,(pd_,td_) in CP08[k].items(): pub[f'CP08 {nm}']=(md(T(pd_),ref[0]),md(T(td_),ref[1]))
        c=nearest_pair(cph_pairs,ref);   pub['CPH p>=50']=c if c else (None,None)
        ph=nearest_pair(phi_pairs,ref);  pub['PHI BB']=ph if ph else (None,None)
        h=nearest_pair(ham_pairs,ref);   own={'HAM (quarters)':h if h else (None,None)}
        q=nearest_pair(bbq_pairs,ref);   own['BBQ GDP (quarters)']=q if q else (None,None)
        own['BB panel']=bb_panel(ref[0],ref[1])
        o=nearest_pair(oecd_pairs,ref);  own['OECD growth cycle']=o if o else (None,None)
        pe=[v[0] for v in pub.values() if v[0] is not None]; te=[v[1] for v in pub.values() if v[1] is not None]
        medp=float(np.median(pe)) if pe else None; medt=float(np.median(te)) if te else None
        rows.append(dict(pk=pk,tr=tr,rule=R[k],pub=pub,own=own,medp=medp,medt=medt,n_p=len(pe),n_t=len(te),rr=RR19.get(k)))
    # ---- print ----
    def f(x):
        if x is None: return '  -'
        return f'{int(x):+d}' if float(x).is_integer() else f'{x:+.1f}'
    g=lambda x: '   -' if x is None else f'{x:+.1f}'
    print('Every American end: the rule, the committee, and the independent rulings (months, method minus NBER)')
    print(f"{'contraction':14s} {'rule P/T':>9s} | {'indep. median P/T (n)':>24s} | {'rule-median P/T':>16s} | published rulings that reach it")
    for r in rows:
        rp,rt=r['rule']; s=f"{r['pk']}/{r['tr'][2:]}  {f(rp)}/{f(rt)}   | {g(r['medp'])}/{g(r['medt'])} ({r['n_p']},{r['n_t']})".ljust(52)
        dp='-' if (r['medp'] is None or rp is None) else f"{rp-r['medp']:+.1f}"
        dt='-' if (r['medt'] is None or rt is None) else f"{rt-r['medt']:+.1f}"
        s+=f" | {dp}/{dt}".ljust(20)
        s+=' | '+'; '.join(f"{n} {f(v[0])}/{f(v[1])}" for n,v in r['pub'].items() if v[0] is not None or v[1] is not None)
        print(s)
        s2='    program computations, apart: '+'; '.join(f"{n} {f(v[0])}/{f(v[1])}" for n,v in r['own'].items())
        if r['rr']: s2+=f"   | RR19: {r['rr']}"
        print(s2)
    # ---- scores ----
    def agree(errs,label):
        e=[x for x in errs if x is not None]; n=len(e)
        if n==0: print(f'{label:52s} n 0'); return
        a=np.array(e,dtype=float)
        print(f'{label:52s} n {n:2d}  exact {int((np.abs(a)==0).sum()):2d}  w1 {int((np.abs(a)<=1).sum()):2d}  w3 {int((np.abs(a)<=3).sum()):2d}  mae {np.abs(a).mean():.2f}')
    print('\nAgreement with the committee, the ends each ruling reaches:')
    agree([r['rule'][0] for r in rows],'the rule, peaks (12)'); agree([r['rule'][1] for r in rows],'the rule, troughs (12)')
    names=sorted({n for r in rows for n in r['pub']})
    for n in names:
        agree([r['pub'][n][0] for r in rows if n in r['pub']],f'{n}, peaks'); agree([r['pub'][n][1] for r in rows if n in r['pub']],f'{n}, troughs')
    for n in ['HAM (quarters)','BBQ GDP (quarters)','BB panel','OECD growth cycle']:
        agree([r['own'][n][0] for r in rows],f'{n}, peaks'); agree([r['own'][n][1] for r in rows],f'{n}, troughs')
    # the rule on the same ends as each published ruling
    print('\nThe rule against the committee on the SAME ends each published ruling reaches (like-for-like):')
    for n in names:
        ends=[r for r in rows if n in r['pub'] and r['pub'][n][0] is not None]
        agree([r['rule'][0] for r in ends],f'rule where {n} has a peak');
        ends=[r for r in rows if n in r['pub'] and r['pub'][n][1] is not None]
        agree([r['rule'][1] for r in ends],f'rule where {n} has a trough')
    print('\nThe rule against the independent median, and which side of the committee the median sits on:')
    print(f"{'contraction':14s} {'rule-NBER':>10s} {'median-NBER':>12s} {'rule-median':>12s}  reading")
    dv=[]
    for r in rows:
        for end,i in (('peak',0),('trough',1)):
            e=r['rule'][i]; m=r['medp'] if i==0 else r['medt']
            if m is None: continue
            if e==0: kind='exact vs committee'
            elif abs(e-m)<=1.0 and abs(m)>=1.0 and np.sign(m)==np.sign(e): kind='DIVERGENCE: the independent median sits on the rule\'s side of the committee'
            elif abs(e-m)<=1.0: kind='within a month of the median'
            elif abs(e)<=1: kind='within a month of the committee, off the median'
            else: kind='off both'
            dv.append(kind)
            print(f"{r['pk']}/{r['tr'][2:]} {end:6s} {e:+10d} {m:+12.1f} {e-m:+12.1f}  {kind}")
    import collections; print('\ncounts:',dict(collections.Counter(dv)))
    import json; json.dump(rows,open(f'{HERE}/rulings_us_full.json','w'),default=str,indent=1)
