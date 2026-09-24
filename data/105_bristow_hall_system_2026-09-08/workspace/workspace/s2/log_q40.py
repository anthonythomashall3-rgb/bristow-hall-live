# log the q40 correction: the audit document's §7, the 105 MANIFEST, the Recession Papers copies (run from 105/workspace)
import hashlib,os,shutil
def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
C=os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08')
RP=os.path.expanduser('~/Projects/Recession Papers')
shutil.copy(os.path.join(C,'AUDIT-SITE-v3.29-2026-09-11.md'),os.path.join(RP,'BRISTOW-HALL-RULE-AUDIT-SITE-v329-2026-09-11.md'))
ITEM="""
8. **The no-false-alarm property was described wrongly and is corrected (Anthony, 11 September 2026: "why is our no false
   alarm vacuous?! we don't want that").** The v3.29 documents said the test was "nearly vacuous for the datum".
   `s2/q40.py` (`out/q40_conjunction.txt`) reads each leg alone: the market gate held in nine episodes since 1948, three
   outside any recession (19 October, 3 and 6 November 1987); the claims week alone fires eleven times since 1967, five
   outside a recession window (1972, 1977, 1979, 1989, 1992); each search term alone, 2004–2026, fires fifteen, sixty-one
   and thirty times with twelve, fifty and twenty-five outside a window ("unemployment", "layoffs", "laid off"). The
   conjunction fires twice — 7 October 2008 and 12 March 2020 — and never outside. Each leg rejects the other's false
   alarms, and the margin at the 1987 crash is the whole of it: the claims four-week mean stood at its own 52-week low in
   the crash week and never above 14.7 per cent through June 1988, so no claims line down to one per cent would have
   opened a recession there. What is narrow is only the evidence for the choice of search TERM: within 2004–2026 the gate
   held only inside recession windows, and the one crash without a recession predates the index. Corrected in place in the
   addendum §2, this document, the memo §9, STANDING-RULES §81 clause 9, NAME-AND-VERSION, the HANDOFF and their copies,
   each carrying the correction at its end. The page now states the same numbers in its notes (deployed 07:07 UTC on
   11 September 2026; `s2/audit_site.py` 47/47 at 07:09 UTC, `AUDIT-SITE-v3.29-2026-09-11.md`).
"""
p=os.path.join(C,'AUDIT-TOOL-v3.29-2026-09-11.md'); t=open(p).read()
a="\n## 8. What the audit does not establish"
assert t.count(a)==1
t=t.replace(a,ITEM+a); open(p,'w').write(t)
shutil.copy(p,os.path.join(RP,'BRISTOW-HALL-RULE-AUDIT-TOOL-v329-2026-09-11.md'))
print('audit doc item 8 added')
files=['workspace/s2/q40.py','workspace/out/q40_conjunction.txt','workspace/s2/fix_vacuous_apply.py','workspace/s2/log_q40.py','site/template.html','site/public/index.html','AUDIT-SITE-v3.29-2026-09-11.md','AUDIT-TOOL-v3.29-2026-09-11.md','PREREG-v329-ADDENDUM-2026-09-10.md','SEARCH-WEEK-v327-2026-09-10.md','NAME-AND-VERSION.md']
os.chdir(C)
rows='\n'.join(f'{h(f)}  {os.path.getsize(f)}  ./{f}' for f in files if os.path.exists(f))
open('MANIFEST-NOTES.md','a').write(f"""

### The conjunction test and the correction of "vacuous" (11 September 2026, 07:07 UTC)

`s2/q40.py` reads each leg of the sudden stop alone and together (`out/q40_conjunction.txt`): the market gate alone, nine episodes since 1948 with three outside any recession (19 October, 3 and 6 November 1987); the claims week alone, eleven fires since 1967 with five outside a window; each search term alone 2004–2026, fifteen/sixty-one/thirty fires with twelve/fifty/twenty-five outside; the conjunction, two fires (7 October 2008, 12 March 2020) and none outside. The 1987 margin: the claims four-week mean at its own 52-week low in the crash week, never above 14.7 per cent through June 1988, so no claims line down to one per cent fires there. The v3.29 documents had called the no-false-alarm test "nearly vacuous for the datum"; that is wrong as written and is corrected in place in twelve documents by `s2/fix_vacuous_apply.py`, each carrying the correction at its end, and the page's notes now carry the numbers. Rebuilt and deployed 07:07 UTC; `s2/audit_site.py` 47/47. Hashes:

{rows}
""")
print('manifest appended')
