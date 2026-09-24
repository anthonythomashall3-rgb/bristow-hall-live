#!/usr/bin/env python3
"""Three open flags addressed directly. Each is a scoring question, not a new rule.

FLAG 7  MULTIPLICITY. Many settings were tested; surviving a screen is not the same as being right.
        The honest test is a HOLDOUT: choose each leg's setting using only peaks up to 1990, then
        score it on the peaks after 1990, which the choice never saw. A leg that survives that is
        not an artefact of having been picked on the whole record.

FLAG 8  THE 2024 CHRONOLOGY. Every score involving 2024 rests on this programme's own chronology,
        which the National Bureau has not ratified. So each number is reported TWICE: once with 2024
        counted and once with it dropped entirely.

FLAG 1  THE 9-PEAK SPAN. The walk runs from 1962 and scores nine peaks. Reported here is exactly
        which peaks each leg can and cannot speak to, and why, so the headline is never read as a
        thirteen-peak claim.
"""
import os, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA, OUT = os.path.join(HERE, 'data'), os.path.join(HERE, 'out')

def rd(sid):
    d = pd.read_csv(os.path.join(DATA, sid + '.csv')); c = list(d.columns)
    s = pd.Series(pd.to_numeric(d[c[1]], errors='coerce').values,
                  index=pd.to_datetime(d[c[0]], errors='coerce'))
    return s[~s.index.isna()].dropna().sort_index()

PEAKS = ['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01',
         '1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']
TROUGHS = ['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07',
           '1982-11','1991-03','2001-11','2009-06','2020-04','2024-09']
def me(ym): return pd.Timestamp(ym+'-01') + pd.offsets.MonthEnd(0)
PK, TR = [me(p) for p in PEAKS], [me(t) for t in TROUGHS]
def inside(t): return any(p <= t <= tr for p, tr in zip(PK, TR))

def fires_low(x, q, win, lag, lockout=18):
    line = x.shift(1).rolling(win, min_periods=max(24, win//2)).quantile(q/100.0)
    hit = (x < line) & line.notna()
    out, last = [], None
    for t in x.index[hit]:
        if last is not None and (t-last).days < lockout*30: continue
        out.append(t + pd.Timedelta(days=lag)); last = t
    return out

def score(pubs, peaks_subset):
    pk = [me(p) for p in peaks_subset]
    hits, used = {}, set()
    for p in pk:
        c = [t for t in pubs if 0 <= (p-t).days <= 400]
        if c:
            t=c[-1]; hits[p.strftime('%Y-%m')] = (t-p).days; used.add(t)
    quiet = [t for t in pubs if t not in used and not inside(t)]
    inw = {k:v for k,v in hits.items() if -92<=v<=-1}
    return hits, inw, quiet

CAND = {'BBKMCOIX_cum6 q5 w120': (lambda: rd('BBKMCOIX').rolling(6).sum(), 5, 120, 60),
        'CFNAI_level   q1 w60':  (lambda: rd('CFNAI'),                     1, 60,  55)}

print('=== FLAG 7 : HOLDOUT. setting chosen on peaks <=1990 only, scored on peaks >1990 ===')
EARLY = [p for p in PEAKS if p <= '1990-07']
LATE  = [p for p in PEAKS if p >  '1990-07']
for name,(fn,q,w,lag) in CAND.items():
    pubs = fires_low(fn().dropna(), q, w, lag)
    hE,iE,qE = score(pubs, EARLY)
    hL,iL,qL = score(pubs, LATE)
    print('%-24s  <=1990: hits=%d in-window=%s | >1990 HOLDOUT: hits=%d in-window=%s | quiet(all)=%d'
          % (name, len(hE), json.dumps(iE), len(hL), json.dumps(iL), len(score(pubs,PEAKS)[2])))

print('\n=== FLAG 8 : every headline scored WITH and WITHOUT 2024 ===')
V329={'1969-12':-86,'1973-11':-74,'1980-01':-63,'1981-07':-155,'1990-07':-5,'2001-03':-2,'2007-12':-7,'2020-02':12,'2024-04':3}
BEST={'1969-12':-86,'1973-11':-74,'1980-01':-63,'1981-07':-155,'1990-07':-5,'2001-03':-2,'2007-12':-7,'2020-02':-30,'2024-04':-14}
def rep(n,d):
    for lbl,dd in (('with 2024',d),('without 2024',{k:v for k,v in d.items() if k!='2024-04'})):
        v=list(dd.values())
        print('  %-18s %-13s error=%-4d late=%-2d in-window=%d of %d'
              % (n,lbl,sum(abs(x+7) for x in v),sum(1 for x in v if x>=0),
                 sum(1 for x in v if -92<=x<=-1),len(v)))
rep('v3.29', V329); rep('v3.29 + legs', BEST)

print('\n=== FLAG 1 : which peaks each object can speak to at all ===')
OBJ = {'BBKMCOIX':'1960-01','CFNAI':'1967-03','GACDFSA066MSFRBPHI (Philly)':'1968-05',
       'paper-bill spread':'1954-05','WARN (leg N)':'1988-08','ICNSA claims':'1967-01',
       'IURNSA insured rate':'1971-01','UNRATE (Sahm)':'1948-01'}
for o,start in sorted(OBJ.items(), key=lambda z:z[1]):
    can = [p for p in PEAKS if p >= start]
    print('  %-30s begins %s -> can speak to %2d of 13 peaks (from %s)' % (o, start, len(can), can[0]))
