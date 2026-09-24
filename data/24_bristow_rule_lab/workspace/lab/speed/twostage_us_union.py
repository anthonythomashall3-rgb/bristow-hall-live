"""The American trough, two stages, with the union's peak call as the opening signal.

twostage_us.py opened a contraction when the panel's D (in hand a month after its month)
reached two per cent, and closed it with the Philadelphia Fed survey (general activity, real-
time factors, a rise of five points from its minimum for one month, published the third
Thursday of the month it describes).  Two of the eight troughs since 1970 were never opened
there - 1970 and 2001 - because D did not reach two per cent in time or at all.  Here the
opening signal is the union of the peak objects (lab/weekly/union_peaks.py: the state
diffusion index, the national weekly conjunct at 0.20, the weekly state breadth - whichever
publishes first), and the closing clause is the survey's, unchanged (a=5, r=1, tracked from
three months before the opening).  Nothing is re-chosen: the survey setting is the recorded
one and the opening is the recorded union.  Scored as twostage_us scores (hits within six
months, exact, within one and three, published within the month, other calls), and in days
from the trough month's last day as union_troughs does.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/speed'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh')
import numpy as np, pandas as pd
import ecbcs_speed as E, twostage_ec as T2, twostage_us as U, union_peaks as UP
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def union_opens():
    legs=[UP.leg_A(),UP.leg_B(0.20),UP.leg_C()]
    pubs=sorted(p for calls in legs for p,d in calls)
    # one opening per episode: the first publication, then nothing for twelve months
    out=[]; last=None
    for p in pubs:
        if last is None or (p-last).days>365: out.append(p); last=p
    return out
def twostage_open(opens, s, a=5., r=1, pre=3):
    """opens: publication dates; s: survey (monthly, real-time adjusted).  From the first survey
    month at or after the opening, call the trough in the first month the survey has stood `a`
    above its minimum (tracked from `pre` months before the opening) for `r` months; date at the
    minimum; one call per opening."""
    out=[]
    for o in opens:
        m0=pd.Timestamp(o.year,o.month,1)
        for t in s.index[s.index>=m0]:
            seg=s[m0-pd.DateOffset(months=pre):t].dropna()
            if len(seg)<2: continue
            mn=seg.idxmin(); lo=float(seg.min()); tail=seg[seg.index>mn]
            if len(tail)>=r and bool((tail.iloc[-r:]>=lo+a).all()):
                out.append((t,mn)); break
    return out
if __name__=='__main__':
    opens=union_opens(); print('openings (union peak calls):',[o.strftime('%Y-%m-%d') for o in opens])
    P=U.philly(); s=E.sa_rt(P['general activity']).dropna()
    calls=twostage_open(opens,s,5.,1)
    T=U.NBER_T
    print('\nrecorded: D opens, Philadelphia Fed closes (twostage_us.py):')
    T2.line('  Philly general activity a=5 r=1, D opens',T2.twostage(U.d_available(),s,5.,1),T)
    print('\nthe union opens, Philadelphia Fed closes:')
    T2.line('  Philly general activity a=5 r=1, union opens',calls,T)
    print('\n  days from the trough month\'s last day to the survey\'s publication (third Thursday, taken as the 18th):')
    for p,d in calls:
        near=min(T,key=lambda k:abs(md(d,k)))
        pub=pd.Timestamp(p.year,p.month,18); end=(near+pd.DateOffset(months=1))-pd.Timedelta(days=1)
        print(f'    trough {near:%Y-%m}: call published {pub:%Y-%m-%d} ({(pub-end).days:+d} d), dated {d:%Y-%m} ({md(d,near):+d})')
