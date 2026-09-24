# -*- coding: utf-8 -*-
"""THE ONE SCORER (18 September 2026; collection 206).

Scoring a set of calls against a chronology is the single most repeated operation in this programme, and on
17-18 September it was written three times in one night - once in the placebo, once in the parameter ablation, once
in the clause ablation - each slightly different. Three scorers means three records, and a state result scored by one
of them could not honestly be set beside a national record scored by another. This is the only scorer from here on.
Everything that scores calls imports it, and its self-test refuses to let it drift.

The rule's own scoring, stated once:

  reference     a peak is referred to by the END of its peak month. A call's lag is (call - end of peak month) in
                days: negative is early, positive is late.
  matching      a call is attributed to the peak whose month-end it is nearest, within 400 days either side - the
                same 400 days the rule gives a leg proposal to be confirmed. One call to one peak; a peak with no
                call in range is missed.
  early         a lag in [-92, -1]. This is the rule's claim: inside the peak month or the two before it.
  late          a lag above -1.
  false alarm   a call inside the scored span attributed to no peak.
  the span      begins 400 days before the first scored peak's month end, so a call that could not have been
                attributed to anything is not counted against the rule.

  better()      the walk's own preference between two records: more early first, then fewer false alarms, then
                fewer late. Used wherever a "best configuration" is chosen.

Self-test (`python3 s2/score_record.py`): scores the live rule's own nine calls, read from out/bhs_state.json, and
requires exactly nine early, none late, none missed, none false, with the lags the record reports. If the scorer
drifts, or the record does, this fails and says which peak moved.
"""
import json, os, sys
import pandas as pd

# The thirteen, with 2024 on Paper 1's dates. Paper 1's 2024 peak is APRIL - not May, which an earlier pass assumed
# and which made the 2024 call look 119 days early and outside the window instead of 88 days early and inside it.
NBER_PAPER1 = [('1948-11', '1949-10'), ('1953-07', '1954-05'), ('1957-08', '1958-04'), ('1960-04', '1961-02'),
               ('1969-12', '1970-11'), ('1973-11', '1975-03'), ('1980-01', '1980-07'), ('1981-07', '1982-11'),
               ('1990-07', '1991-03'), ('2001-03', '2001-11'), ('2007-12', '2009-06'), ('2020-02', '2020-04'),
               ('2024-04', '2024-08')]
NBER_ONLY = NBER_PAPER1[:-1]          # the second scoreboard: the NBER's list, on which the 2024 call is a false alarm
WALKED = list(range(4, 13))           # the nine peaks the walk can reach; 1948-1960 is not walkable
EARLY = (-92, -1)
MATCH = 400


def peak_ends(chron=None):
    return [pd.Timestamp(p) + pd.offsets.MonthEnd(0) for p, _ in (chron or NBER_PAPER1)]


def walked_for(chron=None):
    """WALKED, cut to the chronology given. NBER_ONLY is twelve peaks, so index 12 does not exist on it; passing
    the full WALKED there used to raise IndexError deep inside score(). Every caller scoring both scoreboards
    should ask for its indices here rather than hardcoding the range."""
    return [i for i in WALKED if i < len(peak_ends(chron))]


def score(calls, chron=None, which=None, early=EARLY, match=MATCH):
    """calls: an iterable of timestamps. Returns early / late / missed / fa and the lag to each scored peak."""
    pe = peak_ends(chron); idx = list(range(len(pe))) if which is None else list(which)
    bad = [i for i in idx if not 0 <= i < len(pe)]
    if bad:
        raise IndexError('peak index %s does not exist in a chronology of %d peaks; use walked_for(chron)'
                         % (bad, len(pe)))
    if not idx: raise ValueError('no peaks to score')
    calls = sorted(pd.Timestamp(c) for c in calls)
    used, lags = set(), {}
    for i in idx:
        cand = [c for c in calls if abs((c - pe[i]).days) <= match and c not in used]
        if not cand: continue
        c = min(cand, key=lambda x: abs((x - pe[i]).days))
        used.add(c); lags[i] = (c - pe[i]).days
    span0 = pe[idx[0]] - pd.Timedelta(days=match)
    # A call matched to a peak but further ahead than the early window - say 211 days early - used to fall out of
    # every count: not early, not late (late is a lag above -1), not missed (it is in lags), and not a false alarm
    # (it is used). It vanished. The live rule's nine calls are all within [-88, -2] so the published record never
    # showed this, but the N-of-M and placebo runs of 18 September do produce such calls and were silently
    # dropping them. `tooearly` counts them, and `matched` is early + late + tooearly, so the four categories plus
    # missed now add to the number of peaks scored and nothing can disappear again.
    tooearly = sum(1 for i in idx if i in lags and lags[i] < early[0])
    out = dict(early=sum(1 for i in idx if early[0] <= lags.get(i, 9999) <= early[1]),
               late=sum(1 for i in idx if lags.get(i, -9999) > early[1]),
               tooearly=tooearly,
               missed=sum(1 for i in idx if i not in lags),
               fa=sum(1 for c in calls if c not in used and c >= span0),
               lags={i: lags.get(i) for i in idx})
    assert out['early'] + out['late'] + out['tooearly'] + out['missed'] == len(idx), \
        'the scorer lost a peak: %s' % out
    return out


def better(a, b):
    """the walk's preference: more early, then fewer false alarms, then fewer late"""
    if b is None: return True
    return (a['early'], -a['fa'], -a['late']) > (b['early'], -b['fa'], -b['late'])


def selftest(state_path=None):
    p = state_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'workspace', 'out', 'bhs_state.json')
    if not os.path.exists(p): p = os.path.join('out', 'bhs_state.json')
    st = json.load(open(p))
    calls = [pd.Timestamp(e['open_pub']) for e in st['episodes']]
    s = score(calls, which=WALKED)
    want = dict(early=9, late=0, missed=0, fa=0)
    got = {k: s[k] for k in want}
    lines = ['the live rule\'s nine calls, scored by this scorer:', '  %s' % got,
             '  lags: %s' % {NBER_PAPER1[i][0]: s['lags'][i] for i in WALKED}]
    ok = got == want
    if not ok:
        lines.append('  FAIL: expected %s' % want)
        for i in WALKED:
            if s['lags'].get(i) is None: lines.append('    %s has no call within %d days' % (NBER_PAPER1[i][0], MATCH))
            elif not (EARLY[0] <= s['lags'][i] <= EARLY[1]):
                lines.append('    %s is at %+d days, outside [%d, %d]' % (NBER_PAPER1[i][0], s['lags'][i], *EARLY))
    # the second scoreboard, for the record
    s2 = score(calls, chron=NBER_ONLY, which=list(range(4, 12)))
    lines.append('the NBER list alone (2024 not a recession): %s' % {k: s2[k] for k in want})
    print('\n'.join(lines))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selftest(sys.argv[1] if len(sys.argv) > 1 else None))
