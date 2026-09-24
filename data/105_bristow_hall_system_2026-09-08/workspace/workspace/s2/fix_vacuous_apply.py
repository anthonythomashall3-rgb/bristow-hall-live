# fix_vacuous_apply.py - Rule Zero, 11 September 2026 (run from 105/workspace).
# The v3.29 documents said the sudden stop's no-false-alarm test was "nearly vacuous for the datum". s2/q40.py shows the
# claim is wrong as written: the property is carried by the CONJUNCTION, and each leg rejects the other's false alarms.
# This script (a) narrows the claim wherever it appears, in place, and (b) appends the correction with its numbers.
import os,glob
Q40=("**Correction, 11 September 2026 (Rule Zero) — the no-false-alarm property is not vacuous.** Anthony asked why the "
"v3.29 documents called it so. They were wrong as written, and the sentence is narrowed above. `s2/q40.py` (collection "
"105, `out/q40_conjunction.txt`) reads each leg of the sudden stop separately. The market gate alone — the S&P 500 20 per "
"cent under its 20-day high — held in nine episodes since 1948, three of them outside any recession: 19 October, 3 November "
"and 6 November 1987. The claims week alone, 35 per cent over its base with no gate, fires eleven times since 1967, five of "
"them outside a recession window (6 July 1972, 10 February 1977, 12 April 1979, 12 October 1989, 30 July 1992). Each search "
"term alone, 2004–2026: \"unemployment\" fifteen fires, twelve outside a window; \"layoffs\" sixty-one, fifty outside; "
"\"laid off\" thirty, twenty-five outside. The conjunction — the rule — fires twice since 1967, on 7 October 2008 and "
"12 March 2020, and never outside a recession window. Each leg kills the other's false alarms, which is the whole content "
"of the property. The margin is not thin: in the crash week of October 1987 the claims four-week mean stood at its own "
"52-week low (0.0 per cent over its base) and never exceeded 14.7 per cent through June 1988, so no claims line down to one "
"per cent would have opened a recession on the 1987 crash. What is true, and all that was meant, is narrower: within "
"2004–2026, where the search index exists, the gate held only inside recession windows (October 2008–March 2009, March "
"2020), so that window alone cannot discriminate between candidate search TERMS, and the one crash without a recession — "
"1987 — predates the index. The added terms therefore inherit a slot whose discipline is demonstrated on the claims week "
"over the full sample, while their own separation of a crash from a recession is untested until the next one. (The earlier "
"counts \"51\" and \"25\" for the terms alone were taken over a different arming window; `q40.py`'s are the counts to use.)")

REPL=[
 ("the no-false-alarm test is nearly vacuous for the labour datum",
  "the no-false-alarm test is narrow for the CHOICE OF SEARCH TERM (not for the rule: corrected 11 September 2026, below)"),
 ("the no-false-alarm test is nearly vacuous for the datum",
  "the no-false-alarm test is narrow for the CHOICE OF SEARCH TERM (not for the rule: corrected 11 September 2026, below)"),
 ("the no-false-alarm test is\nnearly vacuous for the datum",
  "the no-false-alarm test is\nnarrow for the CHOICE OF SEARCH TERM (not for the rule: corrected 11 September 2026, below)"),
 ("with the gate at 20 the\nno-false-alarm test is nearly vacuous for the datum",
  "with the gate at 20 the\nno-false-alarm test is narrow for the choice of search term (not for the rule: corrected 11 September 2026, below)"),
 ("With the gate at 20 the no-false-alarm test is nearly vacuous for the datum",
  "With the gate at 20 the no-false-alarm test is narrow for the choice of search term (not for the rule: corrected 11 September 2026, below)"),
 ("(with the gate at 20 any term passes, since the\ngate has held only in 2008–09 and from 12 March 2020)",
  "(within 2004–2026 any term passes, since the\ngate has held only in 2008–09 and from 12 March 2020 — the discipline itself is demonstrated on the claims week over the\nfull sample, `s2/q40.py`)"),
]
ROOTS=[os.path.expanduser('~/Projects/Recession Papers'),
       os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08'),
       os.path.expanduser('~/Projects/Onset Detector Data/108_high_frequency_speed_2026-09-10')]
done=[]
for r in ROOTS:
    for p in sorted(glob.glob(os.path.join(r,'**','*.md'),recursive=True)):
        if 'projects-old' in p or '/bristow-hall/' in p or 'Claude RA' in p: continue
        t=open(p).read(); o=t
        if 'vacuous' not in t and 'any term passes' not in t: continue
        for a,b in REPL: t=t.replace(a,b)
        if 'Correction, 11 September 2026 (Rule Zero) — the no-false-alarm property is not vacuous' not in t:
            t=t.rstrip('\n')+'\n\n'+Q40+'\n'
        if t!=o: open(p,'w').write(t); done.append(os.path.basename(p))
print('corrected:',len(done)); [print(' ',d) for d in done]
left=[]
for r in ROOTS:
    for p in glob.glob(os.path.join(r,'**','*.md'),recursive=True):
        if 'projects-old' in p or '/bristow-hall/' in p or 'Claude RA' in p: continue
        if 'nearly vacuous' in open(p).read(): left.append(p)
print('files still saying "nearly vacuous":',left)
