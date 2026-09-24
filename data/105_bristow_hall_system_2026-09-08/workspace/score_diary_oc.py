"""Score any walk-forward diary pickle set on the instrument's own sample: lags, date errors, false alarms."""
import sys
PAT=sys.argv[1]; STARTS=sys.argv[2] if len(sys.argv)>2 else '1961-11-03'
COOLARG=sys.argv[3] if len(sys.argv)>3 else '0'
MINDURARG=sys.argv[4] if len(sys.argv)>4 else '0'
sys.argv=['x','1962','2026']
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('score_diary_oc.out','w')"))
import pickle,glob
START=pd.Timestamp(STARTS)
LOG=[]
for f in sorted(glob.glob(f'cache/{PAT}_*.pkl')):
    if '_chosen_' in f or '_carry' in f or '_sum' in f or '_prog' in f: continue
    LOG+=pickle.load(open(f,'rb'))
LOG=[l[:4] for l in LOG]; LOG.sort(key=lambda x:x[0])
LOG=[l for l in LOG if l[0]>=START]
COOL=int(COOLARG); MINDUR=int(MINDURARG)
early=[]
if MINDUR:
    # declared: an episode is not closed inside MINDUR months of opening. A close suppressed this way leaves the
    # episode open, so the re-open that followed it is suppressed too.
    keep=[]; openat=None
    for l in LOG:
        if l[1]=='OPEN':
            if openat is not None: continue          # already open: this is a re-open, drop it
            openat=l[0]; keep.append(l)
        else:
            if openat is None: continue
            if l[0]<openat+pd.DateOffset(months=MINDUR): continue
            openat=None; keep.append(l)
    LOG=keep
if COOL:
    # declared filter: the tool does not re-open an episode it has just closed. An open published within COOL months
    # of the preceding close is suppressed.
    keep=[]; lastclose=None
    for l in LOG:
        if l[1]=='OPEN' and lastclose is not None and l[0]<lastclose+pd.DateOffset(months=COOL): continue
        if l[1]=='CLOSE': lastclose=l[0]
        keep.append(l)
    LOG=keep
P(f"DIARY {PAT} from {START:%Y-%m-%d} — {len(LOG)} entries")
used=set(); opens=[]; fa=[]
for pub,kind,dt,leg in LOG:
    if kind!='OPEN':
        P(f"   {pub:%Y-%m-%d}  CLOSE dated {dt:%Y-%m}  by {leg}"); continue
    hit=None
    for i,(pk,tr) in enumerate(zip(PK,TR)):
        if pk-pd.DateOffset(months=6)<=dt<=tr+pd.DateOffset(months=3) and i not in used: hit=i; break   # ONE CLOCK: a call fired up to three months after the trough month still belongs to that recession
    if hit is None:
        fa.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'))); P(f"   {pub:%Y-%m-%d}  OPEN  dated {dt:%Y-%m}  by {leg}   *** FALSE ALARM ***")
    else:
        used.add(hit); lag=(pub-me(PK[hit])).days; err=(dt.year-PK[hit].year)*12+dt.month-PK[hit].month
        opens.append((hit,lag,err)); P(f"   {pub:%Y-%m-%d}  OPEN  dated {dt:%Y-%m}  by {leg}   peak {PK[hit]:%Y-%m}  lag {lag:+5d}  err {err:+d}")
# TROUGH SIDE
usedt=set(); clo=[]; badclose=[]
for pub,kind,dt,leg in LOG:
    if kind!='CLOSE': continue
    hit=None
    for i,tr in enumerate(TR):
        if i in usedt: continue
        if tr-pd.DateOffset(months=6)<=dt<=tr+pd.DateOffset(months=12): hit=i; break
    if hit is None: badclose.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),'no trough')); continue
    usedt.add(hit); lagt=(pub-me(TR[hit])).days; errt=(dt.year-TR[hit].year)*12+dt.month-TR[hit].month
    if lagt<-31: badclose.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),'published more than a month before the trough month ended'))
    elif lagt<0: early.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),lagt))
    clo.append((hit,lagt,errt))
lg=[l for _,l,_ in opens]; er=[e for _,_,e in opens]
NREC=sum(1 for pk in PK if pk>START)
yrs=int((pd.Timestamp('2026-09-01')-START).days/365.25)
P(f"\n   detected {len(opens)}/{NREC} | FALSE ALARMS in {yrs} years: {len(fa)} {fa}")
if lg:
    P(f"   lags {sorted(lg)}")
    P(f"   MEDIAN {np.median(lg):.1f} days, mean {np.mean(lg):.1f}, within the month {sum(1 for x in lg if x<=31)}/{len(lg)}, over a month {sum(1 for x in lg if x>31)}")
    P(f"   dates exact {sum(1 for e in er if e==0)}, within one {sum(1 for e in er if abs(e)<=1)}, worst {max(abs(e) for e in er)}")
if clo:
    lt=[l for _,l,_ in clo]; et=[e for _,_,e in clo]
    NT=sum(1 for tr in TR if tr>START)
    P(f"\n   TROUGH SIDE: closed {len(clo)}/{NT} | lags {sorted(lt)}")
    P(f"   median {np.median(lt):.0f} days, mean {np.mean(lt):.1f}, worst {max(lt)} | dates exact {sum(1 for e in et if e==0)}, within one {sum(1 for e in et if abs(e)<=1)}")
    P(f"   PREMATURE OR UNMATCHED CLOSES: {len(badclose)} {badclose}")
    P(f"   within a month either side {sum(1 for x in lt if -31<=x<=31)}/{len(lt)}, inside the month after {sum(1 for x in lt if 0<=x<=31)}/{len(lt)} | EARLY (up to a month, accepted 8 September 2026): {len(early)} {early}")
    P(f"   MEDIAN OF ABSOLUTE LAGS {np.median([abs(x) for x in lt]):.0f} days, mean {np.mean([abs(x) for x in lt]):.1f}")
out.close()
