"""Rule 17's speed question on zero-lag data: the European Commission's business and consumer
surveys (DG ECFIN, monthly from January 1985, every EU economy, the euro area and the United
Kingdom to 2020), published in the last working days of the month they describe.

Source: the Commission's time-series archives (lab/acq/ecbcs/, fetched 2 September 2026 from
ec.europa.eu/economy_finance/db_indicators/surveys/documents/series/nace2_ecfin_2608/): the
unadjusted industry survey (INDU.<cc>.TOT.COF = confidence indicator; question 1 = production
trend observed in recent months, question 2 = order books, question 5 = production
expectations) and the unadjusted consumer survey (CONS.<cc>.TOT.COF).  Survey balances are
revised only for late replies, so the series as it stands today is close to the series as first
published; the one look-ahead in the Commission's own adjusted series is its seasonal
adjustment (and, for the ESI, a standardisation over the whole sample), so every series here
is adjusted in real time: additive month-of-year factors, medians of the detrended balance over
the seven years strictly before the year adjusted.

Two questions, for each economy and each survey series:
  1. RETROSPECTIVE ALIGNMENT - is the survey's own extremum near the committee's month at all?
     For each committee turn, the month of the adjusted series' extremum inside +/- 12 months
     (peaks: maximum; troughs: minimum), smoothed over three months, and its distance in months.
  2. REAL TIME - a causal turning-point machine run month by month on the adjusted series as it
     would have stood: in expansion, a peak is called when the series has fallen `a` points
     below its running maximum for `r` consecutive months (dated at the maximum, published in
     the month of the call); in contraction, a trough is called when it has risen `a` points
     above its running minimum for `r` months.  No call within `mph` months of the previous
     turn.  Scored against the committee (Germany's Council; the euro area, France and Spain
     as quarter mid-months) and against ECRI's July 2021 table: hits within six months, exact,
     within one month, published within the month (call month <= turning month + 1), and other
     calls.  Grid ceilings, in sample; the zero-false-alarm best is printed separately.
"""
import sys, itertools, json, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
ACQ='/home/claude/lab/acq/ecbcs'
ECRI=json.load(open('/home/claude/lab/cmp/ecri_chronology_2021.json'))
COMMITTEE={ # monthly chronologies (Germany: Council of Economic Experts) and quarterly ones as quarter mid-months
 # (every committee contraction after the survey's January 1985 start; bench.PANELS carries the quarterly chronologies)
 'DE':[('1992-02','1993-07'),('2001-02','2003-06'),('2008-01','2009-04'),('2020-02','2020-04')],
 'EA':[('1992-02','1993-08'),('2008-02','2009-05'),('2011-08','2013-02'),('2019-11','2020-05')],
 'FR':[('1992-02','1993-02'),('2008-02','2009-05'),('2019-11','2020-05')],
 'ES':[('1992-02','1993-08'),('2008-05','2009-11'),('2010-11','2013-05'),('2019-11','2020-05')],
}
ECRI_CC={'DE':'Germany','FR':'France','ES':'Spain','IT':'Italy','UK':'United Kingdom','SE':'Sweden','AT':'Austria','PL':'Poland'}
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def ts(s): return pd.Timestamp(s+'-01')
def load_sheet(f, sheet):
    d=pd.read_excel(f'{ACQ}/{f}',sheet_name=sheet,header=0)
    d=d.rename(columns={d.columns[0]:'t'}); d['t']=pd.to_datetime(d['t']).dt.to_period('M').dt.to_timestamp()
    return d.set_index('t')
_ind=_con=None
def industry():
    global _ind
    if _ind is None: _ind=load_sheet('industry_total_nsa_nace2.xlsx','INDUSTRY MONTHLY')
    return _ind
def consumer():
    global _con
    if _con is None: _con=load_sheet('consumer_total_nsa_nace2.xlsx','CONSUMER MONTHLY')
    return _con
def series(cc, which):
    if which=='industry confidence': s=industry()[f'INDU.{cc}.TOT.COF.B.M']
    elif which=='production trend observed': s=industry()[f'INDU.{cc}.TOT.1.B.M']
    elif which=='order books': s=industry()[f'INDU.{cc}.TOT.2.B.M']
    elif which=='production expectations': s=industry()[f'INDU.{cc}.TOT.5.B.M']
    elif which=='consumer confidence': s=consumer()[f'CONS.{cc}.TOT.COF.B.M']
    elif which=='industry and consumer confidence':
        a=industry()[f'INDU.{cc}.TOT.COF.B.M']; b=consumer()[f'CONS.{cc}.TOT.COF.B.M']
        s=(a+b)/2.0
    else: raise ValueError(which)
    return pd.to_numeric(s,errors='coerce').dropna().astype(float)
def sa_rt(s, win=7):
    """additive real-time month-of-year adjustment: factors for year Y are medians of the
    residual from a 13-month centred mean over years Y-win..Y-1, computed on data through
    December of Y-1 only; the first two years are left unadjusted."""
    out=pd.Series(np.nan,index=s.index)
    for yr in sorted(set(s.index.year)):
        past=s[s.index.year<yr]
        if len(past)<24: out[s.index.year==yr]=s[s.index.year==yr]; continue
        tr=past.rolling(13,center=True,min_periods=7).mean().bfill().ffill(); r=past-tr
        hist=r[r.index.year>=yr-win]; f=hist.groupby(hist.index.month).median(); f=f-f.mean()
        for t in s.index[s.index.year==yr]: out[t]=s[t]-float(f.get(t.month,0.0))
    return out
def align(s, turns, kind, sm=3, w=12):
    x=s.rolling(sm).mean()
    out=[]
    for d in turns:
        seg=x[d-pd.DateOffset(months=w):d+pd.DateOffset(months=w)].dropna()
        if len(seg)<3: out.append((d,None)); continue
        e=seg.idxmax() if kind=='P' else seg.idxmin()
        out.append((d,md(e,d)))
    return out
def machine(s, a, r, mph, sm=1, warm=24):
    """causal turning-point calls on s (already adjusted).  Returns (peaks, troughs) as lists of
    (published month, dated month)."""
    x=s.rolling(sm).mean().dropna(); idx=x.index; v=x.values; n=len(v)
    peaks=[]; troughs=[]
    state='exp'; ext_i=0; since=0; below=0; above=0; last=None
    for i in range(n):
        if i<warm:
            ext_i=i if (state=='exp' and v[i]>=v[ext_i]) or (state=='con' and v[i]<=v[ext_i]) else ext_i
            continue
        if state=='exp':
            if v[i]>=v[ext_i]: ext_i=i; below=0
            else:
                below=below+1 if v[i]<=v[ext_i]-a else 0
                if below>=r and (last is None or md(idx[i],last)>=mph):
                    peaks.append((idx[i],idx[ext_i])); last=idx[ext_i]; state='con'; ext_i=i; above=0
                    # the minimum so far in the fall
                    j=int(np.argmin(v[ext_i-below+1:i+1]))+ext_i-below+1; ext_i=j
        else:
            if v[i]<=v[ext_i]: ext_i=i; above=0
            else:
                above=above+1 if v[i]>=v[ext_i]+a else 0
                if above>=r and (last is None or md(idx[i],last)>=mph):
                    troughs.append((idx[i],idx[ext_i])); last=idx[ext_i]; state='exp'; below=0
                    j=int(np.argmax(v[ext_i:i+1]))+ext_i; ext_i=j
    return peaks,troughs
def score(calls, refs, tol=6):
    got={}; used=set()
    for i,ref in enumerate(refs):
        best=None
        for j,(pub,dt) in enumerate(calls):
            if j in used: continue
            e=md(dt,ref)
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(j,e)
        if best: got[i]=(calls[best[0]][0],calls[best[0]][1],best[1]); used.add(best[0])
    return got,[c for j,c in enumerate(calls) if j not in used]
def fmt(got, refs):
    return {refs[i].strftime('%Y-%m'):(v[1].strftime('%Y-%m'),v[2],'pub '+v[0].strftime('%Y-%m')) for i,v in got.items()}
SERIES=['industry confidence','production trend observed','order books','production expectations','consumer confidence','industry and consumer confidence']
if __name__=='__main__':
    ccs=sys.argv[1:] or ['DE','EA','FR','ES','IT','UK','SE','AT']
    for cc in ccs:
        rulers=[]
        if cc in COMMITTEE:
            rulers.append(('the committee',[ts(p) for p,t in COMMITTEE[cc]],[ts(t) for p,t in COMMITTEE[cc]]))
        if cc in ECRI_CC:
            E=[(k,ts(d)) for k,d in ECRI[ECRI_CC[cc]] if d>='1986-01']
            rulers.append(('ECRI',[d for k,d in E if k=='P'],[d for k,d in E if k=='T']))
        print(f'\n############ {cc}')
        for which in SERIES:
            try: raw=series(cc,which)
            except KeyError: print(f'  {which}: not in the file'); continue
            s=sa_rt(raw).dropna()
            print(f'\n=== {cc} {which}: {s.index.min():%Y-%m}..{s.index.max():%Y-%m}, real-time adjusted')
            for label,P,T in rulers:
                ap=align(s,P,'P'); at=align(s,T,'T')
                print(f'  alignment vs {label}: peaks {[(d.strftime("%Y-%m"),e) for d,e in ap]}')
                print(f'                 {" "*len(label)}  troughs {[(d.strftime("%Y-%m"),e) for d,e in at]}')
            for label,P,T in rulers:
                rows=[]
                for a,r,mph,sm in itertools.product((3.,5.,8.,12.,16.),(1,2,3),(3,6,9),(1,2,3)):
                    pk,tr=machine(s,a,r,mph,sm)
                    gp,op=score(pk,P); gt,ot=score(tr,T)
                    ep=[v[2] for v in gp.values()]; et=[v[2] for v in gt.values()]
                    lp=[md(v[0],P[i]) for i,v in gp.items()]; lt=[md(v[0],T[i]) for i,v in gt.items()]
                    rows.append(dict(hits=len(gp)+len(gt),n=len(P)+len(T),other=len(op)+len(ot),
                        exact=sum(x==0 for x in ep+et),w1=sum(abs(x)<=1 for x in ep+et),w3=sum(abs(x)<=3 for x in ep+et),
                        inM=sum(l<=1 for l in lp+lt),cfg=(a,r,mph,sm),gp=gp,gt=gt,op=op,ot=ot))
                rows.sort(key=lambda d:(d['hits'],-d['other'],d['inM'],d['w3'],d['exact']),reverse=True)
                print(f'  --- real time vs {label} ({len(P)} peaks, {len(T)} troughs): hits / other / exact / w1 / w3 / in-month | (points, run, min phase, smooth)')
                for d in rows[:3]:
                    print(f'    hits {d["hits"]}/{d["n"]} other {d["other"]} exact {d["exact"]} w1 {d["w1"]} w3 {d["w3"]} inMonth {d["inM"]} | {d["cfg"]}')
                    print('       peaks',fmt(d['gp'],P)); print('       troughs',fmt(d['gt'],T))
                    if d['op'] or d['ot']: print('       other:',[('P',p.strftime('%Y-%m'),x.strftime('%Y-%m')) for p,x in d['op']]+[('T',p.strftime('%Y-%m'),x.strftime('%Y-%m')) for p,x in d['ot']])
                z=[d for d in rows if d['other']==0]
                if z:
                    z.sort(key=lambda d:(d['hits'],d['inM'],d['w3'],d['exact']),reverse=True); d=z[0]
                    print(f'    best with no other call: hits {d["hits"]}/{d["n"]} exact {d["exact"]} w1 {d["w1"]} w3 {d["w3"]} inMonth {d["inM"]} | {d["cfg"]}')
                    print('       peaks',fmt(d['gp'],P)); print('       troughs',fmt(d['gt'],T))
