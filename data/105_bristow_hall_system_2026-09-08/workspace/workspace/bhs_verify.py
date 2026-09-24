"""THE BRISTOW HALL RULE — the record, reproduced and verified (plan step 8). v3.55 copy: walk94 admitted, the tail split by _TAILMARK (16 September 2026).

    python3 bhs_verify.py [w37|w38]

Loads the walk's own preamble (the objects as the walk read them) while recording every file it opens, hashes those
files, loads the walk's diary (`cache/<VAR>_prog.pkl`) and walk-end configuration (`cache/<VAR>_carry.pkl`), scores
the diary on one clock exactly as `score_diary_oc.py` does (a peak call fired up to three months after the trough
month belongs to that recession; a close up to twelve months after the trough; a close published more than a month
before the trough month ended is premature), re-runs the frozen rule at the walk-end lines, and compares every
number with the published record. Writes `RECORD-<VAR>-<date>.md` beside the collection root and prints PASS or
FAIL for each check. Exit code 0 only if every check passes."""
import sys, os, io, contextlib, pickle, hashlib, datetime, json, builtins
VAR=sys.argv[1] if len(sys.argv)>1 else 'w38'
WALK={'w37':'walk37.py','w38':'walk38.py','w39a':'walk39a.py','w39':'walk39.py','w40':'walk40.py','w42':'walk42.py','w43':'walk43.py','w44':'walk44.py','w45':'walk45.py','w46':'walk46.py','w47':'walk47.py','w48':'walk48.py','w49':'walk49.py','w50':'walk50.py','w51':'walk51.py','w52':'walk52.py','w53':'walk53.py','w54':'walk54.py','w55':'walk55.py','w81':'walk81.py','w94':'walk94.py','w94m':'walk94.py'}[VAR]
COL=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ=set(); _open=builtins.open
def _topen(f,*a,**k):
    m=(a[0] if a else k.get('mode','r'))
    if isinstance(f,(str,bytes,os.PathLike)) and 'r' in str(m) and '+' not in str(m):
        try: READ.add(os.path.abspath(os.fspath(f)))
        except Exception: pass
    return _open(f,*a,**k)
builtins.open=_topen
sys.argv=['x','2011','2012','wverify']
_wsrc=_open(WALK).read()
_TAILMARK = "exec(open('walk39.py').read().split(_MARK)[1]"   # v3.55: walks 56-95 carry no literal marker; their loop is this exec line
if "# ---- the walk itself" in _wsrc: src=_wsrc.split("# ---- the walk itself")[0]
elif _TAILMARK in _wsrc: src=_wsrc.split(_TAILMARK)[0]
else: src=_wsrc.split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close(); builtins.open=_open
import numpy as np, pandas as pd
READ={f for f in READ if os.path.isfile(f) and not f.endswith('.pyc') and 'site-packages' not in f and '/lib/python' not in f}
def sha(path):
    h=hashlib.sha256()
    with _open(path,'rb') as fh:
        for chunk in iter(lambda: fh.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()
CF=f'cache/{VAR}_carry.pkl'; PROG=f'cache/{VAR}_prog.pkl'
p=pickle.load(_open(CF,'rb')); pg=pickle.load(_open(PROG,'rb')); LOG=sorted([l[:4] for l in pg['log']],key=lambda z:z[0])
START=pd.Timestamp('1961-11-03'); LOG=[l for l in LOG if l[0]>=START]
# ---- the one-clock score, as score_diary_oc.py ----
used=set(); opens=[]; fa=[]; rows=[]
for pub,kind,dt,leg in LOG:
    if kind!='OPEN': continue
    hit=None
    for i,(pk,tr) in enumerate(zip(PK,TR)):
        if pk-pd.DateOffset(months=6)<=dt<=tr+pd.DateOffset(months=3) and i not in used: hit=i; break
    if hit is None: fa.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'))); rows.append(('OPEN',pub,dt,leg,None,None,None)); continue
    used.add(hit); lag=(pub-me(PK[hit])).days; err=(dt.year-PK[hit].year)*12+dt.month-PK[hit].month
    opens.append((hit,lag,err)); rows.append(('OPEN',pub,dt,leg,PK[hit],lag,err))
usedt=set(); clo=[]; badclose=[]; early=[]
for pub,kind,dt,leg in LOG:
    if kind!='CLOSE': continue
    hit=None
    for i,tr in enumerate(TR):
        if i in usedt: continue
        if tr-pd.DateOffset(months=6)<=dt<=tr+pd.DateOffset(months=12): hit=i; break
    if hit is None: badclose.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),'no trough')); rows.append(('CLOSE',pub,dt,leg,None,None,None)); continue
    usedt.add(hit); lagt=(pub-me(TR[hit])).days; errt=(dt.year-TR[hit].year)*12+dt.month-TR[hit].month
    if lagt<-31: badclose.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),'published more than a month before the trough month ended'))
    elif lagt<0: early.append((pub.strftime('%Y-%m-%d'),dt.strftime('%Y-%m'),lagt))
    clo.append((hit,lagt,errt)); rows.append(('CLOSE',pub,dt,leg,TR[hit],lagt,errt))
NREC=sum(1 for pk in PK if pk>START); NT=sum(1 for tr in TR if tr>START)
lg=[l for _,l,_ in opens]; er=[e for _,_,e in opens]; lt=[l for _,l,_ in clo]; et=[e for _,_,e in clo]
got=dict(peaks_detected=len(opens),peaks_of=NREC,false_alarms=len(fa),peaks_exact=sum(1 for e in er if e==0),peaks_within_one=sum(1 for e in er if abs(e)<=1),
         peaks_worst=max(abs(e) for e in er) if er else None,peaks_median_days=float(np.median(lg)) if lg else None,
         troughs_closed=len(clo),troughs_of=NT,troughs_exact=sum(1 for e in et if e==0),troughs_within_one=sum(1 for e in et if abs(e)<=1),
         troughs_worst=max(abs(e) for e in et) if et else None,troughs_median_days=float(np.median(lt)) if lt else None,premature_or_unmatched=len(badclose),
         open_days=[r[1].strftime('%Y-%m-%d') for r in rows if r[0]=='OPEN'],close_days=[r[1].strftime('%Y-%m-%d') for r in rows if r[0]=='CLOSE'])
# ---- the published record, per version ----
EXPECTED={
 'w37':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=4,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-15','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-05-05','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-22','2009-06-18','2020-05-07','2024-09-26'],
            note='the walk as written; the 2020 days carry the hours pair at the fifth of the month (V321 note §13)'),
 'w38':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=4,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=7,troughs_worst=2,troughs_median_days=24.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-15','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-05-08','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-22','2009-06-18','2020-06-06','2024-09-26'],
            note='v3.21 as it stands: walk37 with the hours pair dated by the employment-report calendar; the same lines at every cut (V321 note §13)'),
 'w39a':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=4,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=7,troughs_worst=2,troughs_median_days=24.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-17','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-05-08','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-06-04','2024-09-26'],
            note='walk38 on the actual release days (the audit of 8 September 2026): the same lines at every cut; three days move - 17 September 1973 (the H.15 Monday), 21 November 2001 (the Wednesday before Thanksgiving), 4 June 2020 (the release of the last May claims week)'),
 'w39':dict(peaks_detected=9,peaks_of=9,false_alarms=1,peaks_exact=1,peaks_within_one=5,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=1,
            open_days=['1969-08-21','1973-09-17','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-03-26','2024-05-03','2025-12-16'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26','2026-03-12'],
            note='walk39a with the vacancy rate on first prints from July 2010 and closer C\'s stock confirmers on first prints (Rule 23): 2020 opens 26 March 2020 and closes 7 May 2020 by C; the hub fires 16 December 2025 - a false alarm, closed 12 March 2026 by R under the lines that opened it - and the 2026 cut moves the lines (sahm 0.5, u45 0.7, look 52, hline 0.85)'),
 'w40':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=5,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-17','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-03-26','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='v3.22: walk39 (first prints throughout, actual release days) with the hub\'s "still falling" clause - the vacancy\'s latest print must stand at its line on the day the unemployment reading arrives - and the labor force carried over October 2025; the same lines as walk38 at every cut; no call in 2025'),
 'w42':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=5,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-17','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-03-26','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-08-03','2001-03-15','2008-01-04','2020-03-26','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='v3.23: walk40 with the household co-signer on the insured rate\'s 0.45 branch and the initial-claims branch - a proposal within 0.2 point (15 points for claims) above its line fires only if the three-month average unemployment rate, as last published on the proposal day, stands at least 0.2 point above its twelve-month low; a stronger proposal fires on its own; an unsigned proposal stays armed - and the claims grid extended to 40 and 35. The same eighteen calls as walk40 at every cut; the lines moved at seven of sixty-five cuts (1972, 1977, 1981, 1982, 1984, 1985, 2002), the look-back never; frozen at the walk-end lines over 1948-2026 the rule calls all thirteen recessions and nothing else. From this version the lines are fixed: no further January re-choice (9 September 2026)'),
 'w43':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=5,peaks_worst=5,peaks_median_days=-2.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-08-21','1973-09-17','1979-11-29','1981-02-26','1990-08-03','2001-03-29','2008-01-04','2020-03-26','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-08-03','2001-03-15','2008-01-04','2020-03-26','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='v3.24: walk42 (v3.23) with the claims object\'s moving base - the four-week mean\'s rise is measured from the higher of its 52-week low and 85 per cent of its trailing five-year median, as published, so a return from a freak low is not read as a turn (August 2022: 43.9 per cent above the 52-week low, 31.4 above the base, line 40). The same eighteen calls as walk42 to the day, zero false alarms, the same seven moves and the same walk-end lines; frozen 1948-2026 thirteen of thirteen and nothing else, every day as v3.23\'s. The lines stay fixed; the base moves with the object\'s own five-year norm (MOVING-LINES-2026-09-09.md; 9 September 2026, evening)'),
 'w46':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=2,peaks_within_one=3,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-09-19','2001-03-29','2007-12-24','2020-03-19','2024-06-07'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-09-19','2001-03-15','2007-12-24','2020-03-19','2024-06-07'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='v3.26: every monthly object - the unemployment rate (the Sahm gap, the co-signer, the pair\'s rate half), housing starts, factory hours, nondurable employment and, from July 2010, job openings - is read for each month from the series as it stood on the day that month first appeared (Rule 23 clause 1; walk39-walk44 read each month at its own first print, and on the release-day vintage that convention hid a false alarm in October 1984); every one-decimal object in exact tenths (a reading equal to its line fires); the housing pair\'s line fixed at 1.0 and out of the grid (both halves at their lines: the walked line of 0.85 in 1984 is what confirmed the October 1984 proposal); the starts x vacancy pair added to the weak proposers\' confirmers; the paper spread read on the wider of the AA financial and AA nonfinancial markets from September 1997; the sudden stop (a single week of claims 35 per cent over its base with the S&P 500 20 per cent under its 20-day high at the last close before the release), kept where it costs nothing and fired once, 19 March 2020. Walked from 1962: nine of nine, none false; 1990 opens 19 September 1990 (+50) and 2024 on 7 June 2024 (+38) - the two calls the first-print convention had shown inside the month; 2008 opens 24 December 2007 (-7) on financial paper. Frozen 1948-2026 at the walk-end lines: thirteen of thirteen and nothing else (10 September 2026)'),
 'w47':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=2,peaks_within_one=3,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-09-19','2001-03-29','2007-12-24','2020-03-19','2024-06-07'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-09-19','2001-03-15','2007-12-24','2020-03-19','2024-06-07'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='v3.26 on walk47: walk46 with the trough closers\' monthly objects (the settling closers R, T and S, and the confirmations of Q: the rise of housing starts and of factory hours from their twelve-month lows, the settling test on starts, the unemployment rate rolling over) read, for each month, from the series as it stood on the day that month\'s print first appeared (s2/asof_trough.py), as the peak side\'s monthly objects have been since walk45 - one rule reads all its monthly data one way. The closers\' own calls move in a few places; the walked diary, the six moves, the walk-end lines and the frozen run are walk46\'s to the day (10 September 2026)'),
 'w50':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=2,peaks_within_one=3,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-09-19','2001-03-29','2007-12-24','2020-03-16','2024-06-07'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-09-19','2001-03-15','2007-12-24','2020-03-16','2024-06-07'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk50: walk47 with the search week in the sudden stop - the seven-day mean of Google searches for unemployment (daily from 2004, collection 108) over the claims base, 35 per cent, known the next morning, with the S&P 500 at that day\'s close 20 per cent under its 20-day high; the sudden stop fires on the earlier of the claims week and the search week. The walked diary is walk47\'s to the day except 2020, which opens 16 March 2020 (+16); the same six moves and walk-end lines (10 September 2026)'),
 'w51':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=4,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-07-26','2001-03-29','2007-12-24','2020-03-16','2024-06-07'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-05-16','2001-03-15','2007-12-24','2020-03-16','2024-06-07'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk51: walk50 with building permits admitted beside starts in the housing x rate pair (s2/asof_permits.py; the pair at 1.0 when starts or permits stand at the starts line with the unemployment rate at its line; permits on the ALFRED vintage from 1999, the printed Economic Indicators tables for 1969 and 1990 (collection 107), the current file elsewhere as a declared bound). Walked: 1990 opens 26 July 1990 (-5) on the survey-week rate with the permits pair (April print, 16 May 1990); the walk moved the survey-week line from 0.4 to 0.3 at the 1992 cut and kept it; frozen at those lines 1990 opens 16 May 1990; everything else walk50\'s (10 September 2026)'),
 'w53':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-07-26','2001-03-29','2007-12-24','2020-03-16','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-05-16','2001-03-15','2007-12-24','2020-03-16','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk53: walk51 with the hub\'s hold read as the latest JOLTS print at the line OR the vacancy at the line in a majority (five or more) of the prior nine months - counted over the whole window, including months not yet published on the release day (superseded by walk54, which counts the published prints; the diaries agree). 2024 opens 3 May 2024 (+3, dated May) for 7 June; no line moved at any cut; everything else walk51\'s (10 September 2026)'),
 'w55':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-07-26','2001-03-29','2007-12-24','2020-03-12','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-05-16','2001-03-15','2007-12-24','2020-03-12','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk55: walk54 with the search week on three labour terms - unemployment, layoffs, laid off - each over its own base with the sudden stop\'s numbers (35 over the base; the S&P 500 20 under its 20-day high at the close of the day the datum is known), firing on the earliest; the terms chosen after the case (on 11 March 2020 layoffs stood 57 and laid off 55 per cent over their bases against unemployment\'s 25); with the gate each added term fires 7 October 2008 and 12 March 2020 only. 2020 opens 12 March 2020 (+12) for 16 March (+16); everything else walk54\'s (10 September 2026, evening)'),
 'w54':dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=3,peaks_within_one=5,peaks_worst=5,peaks_median_days=-7.0,
            troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
            open_days=['1969-10-06','1973-09-17','1979-11-29','1981-02-26','1990-07-26','2001-03-29','2007-12-24','2020-03-16','2024-05-03'],
            close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-07-28','1973-09-17','1979-11-05','1981-02-26','1990-05-16','2001-03-15','2007-12-24','2020-03-16','2024-05-03'],
            frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
            note='walk54: walk51 with the hub\'s hold read as the latest JOLTS print at the line OR the vacancy at the line in a majority (five or more) of the prior nine months\' prints as published by the release day (s2/q35.py; the hold\'s own window, no new line; adopted after its case, 2024). 2024 opens 3 May 2024 (+3, dated May) on the five published hits of July-November 2023, for 7 June (+38); December 2025 stays blocked (two of nine); no line moved at any cut; everything else walk51\'s (10 September 2026, evening)'),
}
EXPECTED['w94']=dict(peaks_detected=9,peaks_of=9,false_alarms=0,peaks_exact=1,peaks_within_one=6,peaks_worst=2,peaks_median_days=-59.0,
    troughs_closed=9,troughs_of=9,troughs_exact=4,troughs_within_one=8,troughs_worst=2,troughs_median_days=7.0,premature_or_unmatched=0,
    open_days=['1969-11-26','1973-10-01','1979-12-27','1981-05-28','1990-05-16','2001-03-29','2007-11-02','2020-01-30','2024-02-02'],
    close_days=['1970-12-24','1975-05-08','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
    frozen_peaks=['1948-10-10','1953-10-01','1957-09-05','1960-07-30','1969-11-18','1973-09-17','1979-11-05','1981-05-28','1990-05-16','2001-02-02','2007-10-11','2019-12-05','2024-02-02'],
    frozen_troughs=['1950-03-09','1954-06-03','1958-07-03','1961-05-04','1970-12-24','1975-05-01','1980-07-24','1982-11-04','1991-04-25','2001-11-21','2009-06-18','2020-05-07','2024-09-26'],
    note='v3.55 / walk94 (walk81 with leg m on its own ladder axis from the 1972 cut; legs c and m on an axis separate from A, Y, G, J, F): nine of nine peaks 1969-2024 walked from 1962, zero false alarms, every call in the peak month or the two before it (months early 1,1,1,2,2,0,1,1,2), days to the peak-month end -35,-60,-35,-64,-76,-2,-59,-30,-88; troughs nine of nine, median +7 days. Reproduced natively on the Mac on 16 September 2026 (cache w94m, identical chosen configurations at all 65 cuts to the cloud walk of the same day). The frozen check is the walk-end rule without the carried legs; the thirteen-of-thirteen frozen list with every carried leg armed is bhs_build_v355 output (DEPLOY-READINESS-v355).')
EXPECTED['w94m']=EXPECTED['w94']
exp=EXPECTED.get(VAR)
# ---- the frozen rule at the walk-end lines ----
with contextlib.redirect_stdout(io.StringIO()): _r,_t=build_v(p)
FR=[(x['kind'],x['published'].date().isoformat(),x.get('leg')) for x in _t if x['kind'] in ('peak','trough')]
# ---- report ----
today=datetime.date.today().isoformat()
L=[]; ok=True
L.append(f"# The Bristow Hall Rule — the record of {VAR}, reproduced {today}\n")
L.append(f"Walk `{WALK}`; diary `{PROG}` (sha256 {sha(PROG)[:16]}); walk-end configuration `{CF}` (sha256 {sha(CF)[:16]}); this script sha256 {sha(os.path.abspath(__file__))[:16]}.\n")
L.append("Walk-end lines: "+", ".join(f"{k}={v}" for k,v in sorted(p.items()))+"\n")
L.append("## The diary on one clock\n")
L.append("| call | fired | dated | branch | reference month (the NBER's; for 2024, which the NBER has not dated, Paper 1's: April–August 2024) | days from the reference month's end | error, months |\n|---|---|---|---|---|---:|---:|")
for k,pub,dt,leg,ref,lag,err in rows:
    L.append(f"| {k} | {pub:%Y-%m-%d} | {dt:%Y-%m} | {leg} | {ref.strftime('%Y-%m') if ref is not None else 'none — FALSE ALARM' if k=='OPEN' else 'none'} | {'' if lag is None else f'{lag:+d}'} | {'' if err is None else f'{err:+d}'} |")
L.append("")
L.append(f"Peaks: detected {got['peaks_detected']}/{got['peaks_of']}, false alarms {got['false_alarms']} {fa}, dates exact {got['peaks_exact']}, within one month {got['peaks_within_one']}, worst {got['peaks_worst']}, median {got['peaks_median_days']:+.1f} days from the peak month's end.")
L.append(f"Troughs: closed {got['troughs_closed']}/{got['troughs_of']}, dates exact {got['troughs_exact']}, within one month {got['troughs_within_one']}, worst {got['troughs_worst']}, median {got['troughs_median_days']:+.0f} days from the trough month's end, premature or unmatched {got['premature_or_unmatched']} {badclose}, early by up to a month {early}.\n")
L.append("## The frozen rule at the walk-end lines (every year at today's lines; not the record, a check)\n")
L.append(", ".join(f"{k} {d} ({leg})" for k,d,leg in FR)+"\n")
L.append("## Checks against the published record\n")
if exp is None:
    L.append(f"No published record for {VAR} yet; the numbers above are the record to publish.\n"); ok=None
else:
    for k in ['peaks_detected','peaks_of','false_alarms','peaks_exact','peaks_within_one','peaks_worst','peaks_median_days','troughs_closed','troughs_of','troughs_exact','troughs_within_one','troughs_worst','troughs_median_days','premature_or_unmatched','open_days','close_days']:
        good=(got[k]==exp[k]); ok=ok and good
        L.append(f"- {'PASS' if good else 'FAIL'} {k}: got {got[k]}{'' if good else ' — expected '+str(exp[k])}")
    if 'frozen_peaks' in exp:
        fp=[d for k,d,_ in FR if k=='peak']; ft=[d for k,d,_ in FR if k=='trough']
        for nm,gotv,expv in (('frozen_peaks',fp,exp['frozen_peaks']),('frozen_troughs',ft,exp['frozen_troughs'])):
            good=(gotv==expv); ok=ok and good
            L.append(f"- {'PASS' if good else 'FAIL'} {nm}: got {gotv}{'' if good else ' - expected '+str(expv)}")
    L.append(f"\n{exp.get('note','')}\n")
L.append("## Every file the walk read, sha256 and bytes\n")
for f in sorted(READ):
    try: L.append(f"- `{os.path.relpath(f,COL) if f.startswith(COL) else f}` — {sha(f)[:16]} — {os.path.getsize(f)} bytes")
    except Exception as e: L.append(f"- `{f}` — unreadable: {e}")
rep="\n".join(L)+"\n"
outp=os.path.join(COL,f'RECORD-{VAR}-{today}.md'); _open(outp,'w').write(rep)
print(rep.split('## Every file')[0])
print(f"files read: {len(READ)}; record written to {outp}")
print('VERDICT:','PASS' if ok else ('NO PUBLISHED RECORD' if ok is None else 'FAIL'))
sys.exit(0 if ok else 2)
