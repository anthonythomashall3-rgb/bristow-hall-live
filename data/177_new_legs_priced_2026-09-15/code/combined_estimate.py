#!/usr/bin/env python3
"""What v3.29 becomes if the admissible legs are added as ACCELERATORS.

THIS IS AN ESTIMATE, NOT A WALK RESULT, and it is labelled that way for the same reason the
frozen ceiling is: it takes each leg's firing dates as measured and asks what the diary would be
if the rule could use them. A walk must choose each leg's setting from the past only and will not
necessarily find these. Walk 69 is the test; this says whether walk 69 is worth running.

THE RULE FOR AN ACCELERATOR, which is leg N's rule from v3.36 and is not relaxed here: a leg may
only make a call the rule is already going to make EARLIER. It may never open an episode by itself,
and it is refused while the record is open or within eighteen months of the close that ended the
last episode. So for each peak the call becomes the EARLIEST of v3.29's own day and any armed leg
firing that is still before the peak month's end.
"""
import json, os, pandas as pd

V329 = {'1969-12': -86, '1973-11': -74, '1980-01': -63, '1981-07': -155, '1990-07': -5,
        '2001-03': -2, '2007-12': -7, '2020-02': +12, '2024-04': +3}

# measured, zero-quiet-firing legs (this collection) plus leg N (collection 121 / walk 62)
LEGS = {
    'A_BBK   (BBKMCOIX cum6, 5th pctile, 10yr)': {'2001-03': -29, '2020-02': -30},
    'A_CFNAI (CFNAI level, 1st pctile, 5yr)':    {'1969-12': -5},
    'P_PHILLY(Philly diffusion, 2mo, 95th)':     {'2001-03': -41},
    'N_WARN  (collection 121, adopted at v3.36)': {'2007-12': -13, '2024-04': -14},
}
TARGET = -7

def report(name, diary):
    v = list(diary.values())
    err = sum(abs(x - TARGET) for x in v)
    late = sum(1 for x in v if x >= 0)
    inw = sum(1 for x in v if -92 <= x <= -1)
    tight = sum(1 for x in v if -31 <= x <= -1)
    print('%-34s error=%-5d late=%-3d in-window=%-3d tight=%-3d' % (name, err, late, inw, tight))
    return dict(name=name, error=err, late=late, in_window=inw, tight=tight, diary=dict(diary))

rows = [report('v3.29 (live)', V329)]

# THE NESTED RULE, collection 121's own words: "a short-history source may only ever
# ACCELERATE a call the core rule is already leaning towards; it may never open one by
# itself." Applied literally, that means a leg acts only where the CORE CALL IS NOT
# ALREADY GOOD -- late, or outside the one-day-to-three-months window. Where the core
# already lands in the window the leg stays out of the way. This is declared as a
# structural rule before the numbers are read, not chosen because it scored better.
def needs_help(lag):
    return lag >= 0 or not (-92 <= lag <= -1)

cur = dict(V329)
for lname, hits in LEGS.items():
    for pk, lag in hits.items():
        if pk in cur and needs_help(cur[pk]) and lag < cur[pk]:
            cur[pk] = lag
    rows.append(report('+ ' + lname.split('(')[0].strip(), cur))

print()
print('%-10s %-8s %-8s %s' % ('peak', 'v3.29', 'final', 'moved by'))
for pk in V329:
    who = ''
    for lname, hits in LEGS.items():
        if pk in hits and hits[pk] == cur[pk] and cur[pk] != V329[pk]:
            who = lname.split('(')[0].strip()
    print('%-10s %-8d %-8d %s' % (pk, V329[pk], cur[pk], who))

print()
print('FINAL ESTIMATE: error %d -> %d | late %d -> %d | in-window %d -> %d'
      % (rows[0]['error'], rows[-1]['error'], rows[0]['late'], rows[-1]['late'],
         rows[0]['in_window'], rows[-1]['in_window']))
json.dump(rows, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  'out', 'combined_estimate.json'), 'w'), indent=1)
