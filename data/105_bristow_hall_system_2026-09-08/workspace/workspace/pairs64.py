"""Conjunctive PAIRS as confirming objects, swept at the corrected window.

A pair fires only where both parts stand at their lines in the same month, so
its quiet exposure is at most the smaller of the two -- which is the only known
mechanism for buying confirmation speed without buying hazard. The programme
has swept pairs once, at the old window, and found the effect lived entirely in
housing starts x the unemployment rate. The window has since changed, and the
exposure ranking changed with it, so the sweep is run again.

The target is exact. The claims side already reaches January 1980 at -14 days,
March 2001 at -9 and December 2007 at -3; to release those calls a confirming
object must stand at its line on a reading that is PUBLIC by then -- the month
before the call month, at the latest, and within six months of it.
"""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
import glob, os, itertools
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
IDX=pd.date_range('1960-01-01','2026-07-01',freq='MS')   # the route's own exposure index
BASE=[S,V,P3h,H]
TGT=[('1979-07','1979-12'),('2000-09','2001-02'),('2007-06','2007-11')]
TM=[((IDX>=pd.Timestamp(a+'-01'))&(IDX<=pd.Timestamp(b+'-01'))) for a,b in TGT]
qmask=np.array([True]*len(IDX))
for p_,t_ in zip(PEAKS,TROUGHS):
    qmask &= ~((IDX>=pd.Timestamp(p_+'-01')-pd.DateOffset(months=9))&(IDX<=pd.Timestamp(t_+'-01')+pd.DateOffset(months=18)))
BASEarr=np.zeros(len(IDX),bool)
for x in BASE: BASEarr |= x.reindex(IDX).fillna(False).values.astype(bool)
def expo(arr,bk=7,fw=5):
    ss=pd.Series(arr,index=IDX)
    f=ss[::-1].rolling(fw,min_periods=1).max()[::-1].astype(bool).values
    b=ss.rolling(bk,min_periods=1).max().astype(bool).values
    return float((f|b)[qmask].mean()*100)
SKIP={'USREC','RECPROUSM156N','SAHMCURRENT','SAHMREALTIME','GDPNOW'}
cands=[]
for f in sorted(glob.glob(AL+'*.csv')):
    nm=os.path.basename(f).replace('_all_vintages.csv','')
    if nm in SKIP: continue
    try: v=first_prints(nm).dropna()
    except Exception: continue
    if len(v)<300 or v.index[0]>pd.Timestamp('1970-01-01'): continue
    for fn,o in [('12max',(v.rolling(12).max()/v-1)*100),('6max',(v.rolling(6).max()/v-1)*100),
                 ('3fall',-(v/v.shift(3)-1)*100),('gap12',v-v.rolling(12).min()),
                 ('sahmform',v.rolling(3).mean()-v.rolling(12).min().shift(1))]:
        o=o.dropna()
        if len(o)<300: continue
        oq=o[pd.Series(qmask,index=IDX).reindex(o.index).fillna(False)]
        if len(oq)<200: continue
        for pct in (97,98,99,99.5):
            line=float(np.percentile(oq.values,pct))
            if not np.isfinite(line): continue
            arr=(o>=line).reindex(IDX).fillna(False).values.astype(bool)
            hits=[bool((arr&t).any()) for t in TM]
            if not any(hits): continue
            cands.append((nm,fn,round(line,4),pct,arr,hits,expo(arr)))
base_e=expo(BASEarr)
print(f"control: the shipped confirming set at (6 back, 4 forward) = {base_e:.2f}%")
print(f"{len(cands)} single objects fire in at least one target window "
      f"(shipped confirming set sits at {base_e:.2f}%)")
solo=[c for c in cands if expo(BASEarr|c[4])<=base_e+1e-9]
print(f"{len(solo)} of them add ZERO exposure on their own")
best={}
for a,b in itertools.combinations(range(len(cands)),2):
    ca,cb=cands[a],cands[b]
    if ca[0]==cb[0]: continue
    pa=ca[4]&cb[4]
    hits=[bool((pa&t).any()) for t in TM]
    if not any(hits): continue
    e=expo(BASEarr|pa)
    if e>base_e+1e-9: continue
    k=(sum(hits),)
    rec=(sum(hits),e,ca[0],ca[1],ca[2],cb[0],cb[1],cb[2],hits)
    key=(ca[0],cb[0])
    if key not in best or rec<best[key]: best[key]=rec
R=sorted(best.values(),key=lambda r:(-r[0],r[1]))
print(f"\n{len(R)} distinct PAIRS add zero exposure and release at least one wall\n")
print(f"{'walls':>6}{'expo':>7}   {'object A':34}{'object B':34}  1980/2001/2007")
for r in R[:20]:
    print(f"{r[0]:6d}{r[1]:6.2f}%   {r[2]+' '+r[3]+' '+str(r[4]):34.34}{r[5]+' '+r[6]+' '+str(r[7]):34.34}  "
          + ' '.join('YES' if x else ' - ' for x in r[8]))
import pickle; pickle.dump([(r[2],r[3],r[4],r[5],r[6],r[7],r[0],r[1]) for r in R[:40]],open('pairs64.pkl','wb'))
