# apply the second-session paragraphs to the Recession Papers documents and the collection-105 README (run on the Mac)
import os,re,datetime
RP=os.path.expanduser('~/Projects/Recession Papers'); C105=os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08')
def edit(path,fn):
    s=open(path).read(); t=fn(s); assert t!=s, path; open(path,'w').write(t); print('edited',os.path.basename(path))
NV_ADD="""

**10 September 2026, second session — the owed items, and two clauses tested and not adopted** (`BRISTOW-HALL-RULE-SPEED-v327-2026-09-10.md`). The trough closers' monthly objects (R, T, S and the confirmations of Q) now read the release-day vintage (`s2/asof_trough.py`, walk47); the walked diary, the six moves, the walk-end lines and the frozen run are walk46's to the day, and the live system runs on walk47 under the same version number. Nine candidate clauses with no new number were tested frozen 1948–2026 on the vintage: seven refused with their false alarms (the hub without its hold — 16 December 2025; the hours pair or the vacancy for the weak proposers — 1979, or 1959/1989/2022; the S&P 500 15 per cent under its 26-week high — six alarms; 20 per cent under its 20-day high — October 1987; permits in both pairs — January 2023). Two survived the frozen test and were walked: the household co-signer admitting a weak proposal to the strong proposers' confirmers (walk48: nine of nine, none false, 2024 at 1 February 2024 (−89), 2001 at 22 March 2001 (−9), median −63; but the walk moved the vacancy line to 0.25 and the hub's look-back to 12 at the January 2026 cut, and the clause with the survey-week line one notch looser opens a recession on 26 June 2025 — the survey-week rate 0.3 above its low against 0.4, the co-signer 0.267, the vacancy gap 0.204 and 0.201 against 0.20), and building permits in place of starts in the housing × rate pair (walk49: 1990 at 26 July 1990 (−5), but 1969 at 30 March 1970 (+89) and a false alarm on 26 June 2025 at the survey-week line of 0.3 the walk chose in 1992). Neither is in the rule; the first is held for Anthony's ruling with its numbers. The permits data as printed in 1969 and 1990 (Economic Indicators, FRASER) are collection 107. The pre-registration amendment for v3.26 is filed (`PREREG-BRISTOW-HALL-RULE-v3.26-AMENDMENT-2026-09-10.md`); `s2/verify_paper.py` recomputes every number the four executive summaries print (`RECORD-PAPER-v326-2026-09-10.md`); the menu is dated (`s2/q18.py`; the table in the amendment)."""
def nv(s):
    a="the v3.24 files are in `Recession Papers/Older Versions/`."
    i=s.rfind(a); assert i>0; j=i+len(a); return s[:j]+NV_ADD+s[j:]
edit(os.path.join(RP,'BRISTOW-HALL-RULE-NAME-AND-VERSION.md'),nv)
HO_ADD="""

**Second session, 10 September 2026 (later).** The owed items are closed: the trough closers' monthly objects are on the release-day vintage (walk47; the live system runs on it, same record, same version); the pre-registration amendment for v3.26 is filed; `s2/verify_paper.py` gives a verifier row for every number the executive summaries print; the menu is dated (Rule 23 clause 3; the table is in the amendment). The two calls outside the month were attacked with nine no-new-number clauses; the two that passed the frozen test failed the walk (`BRISTOW-HALL-RULE-SPEED-v327-2026-09-10.md` §4): permits in the housing pair lose 1969 and produce a false alarm in June 2025 through the walk's own re-choice of the survey-week line; the co-signer clause for the weak proposals is clean but one tenth from a false alarm in June 2025 and the walk retreated from it at the 2026 cut. **The current version is still v3.26**; the co-signer clause is held as a candidate for Anthony's ruling. What remains open: 1990 (+50) and 2024 (+38) at the floors the data allow; the 2024 trough's evidence; the state cross-section; the United Kingdom and Canada."""
def ho(s):
    a="Collection 106 holds the audit scripts"
    i=s.index(a); j=s.index("\n\n",i); return s[:j]+HO_ADD+s[j:]
edit(os.path.join(RP,'HANDOFF-BRISTOW-HALL-RULE-2026-09-08.md'),ho)
SR_ADD="""

## §79 — 10 SEPTEMBER 2026, SECOND SESSION: ONE CONVENTION FOR ALL MONTHLY DATA; THE FROZEN TEST IS NOT THE WALK; TWO CLAUSES REFUSED

1. **One convention.** The trough closers' monthly objects (the settling closers R, T, S and the confirmations of Q) now
   read the release-day vintage like every other monthly object (`s2/asof_trough.py`, walk47). The record is unchanged to
   the day; the live system runs on walk47 under v3.26. A rule reads all its monthly data one way.
2. **The frozen test at the walk-end lines is necessary and not sufficient.** Two clauses with no new number passed it
   (13/13, nothing else, 1948–2026 on the vintage) and failed the walk: building permits in the housing pair (1969 lost;
   the walk's re-choice of the survey-week line at the 1992 cut produced a false alarm on 26 June 2025) and the household
   co-signer admitting weak proposals to the strong confirmers (clean on the walk, but the walk moved two lines at the
   January 2026 cut, and the clause one grid notch looser opens 26 June 2025: the survey-week rate 0.3 against 0.4, the
   co-signer 0.267, the vacancy gap 0.204 and 0.201 against 0.20). From here a clause enters the rule only after the walk,
   and a walk that moves a line at its last cut is read as a warning about the clause, not as a result.
3. **The margin in the one forward year is the test.** 2025 is the only year the record does not train on and does not
   score; a clause that is one tenth from a false alarm there is not adopted, whatever it does for 2024.
4. **Data gathered stays.** Permits as printed in 1969 and 1990 (Economic Indicators, FRASER; collection 107) are kept
   as data whether or not the clause that prompted them is adopted. ALFRED's permits vintages begin in August 1999 and
   collection 27 already held the table (checked before fetching, per the data rule).
5. **The pre-registration amendment for v3.26 is filed**, with the clauses of 10 September named as adopted after their
   cases and the two candidates of the second session named as not adopted; nothing in it can be revised to accommodate
   a result. `s2/verify_paper.py` is the verifier row for every number the executive summaries print; `s2/q18.py` dates
   the menu (Rule 23 clause 3): every series the rule reads existed before the 1962 cut except JOLTS and the financial
   paper rate, which enter on their own dates; the hindsight in the list itself is declared, not removed."""
def sr(s): return s.rstrip('\n')+SR_ADD+'\n'
edit(os.path.join(RP,'STANDING-RULES.md'),sr)
R105_ADD="""

**Second session, 10 September 2026.** `walk47.py` (walk46 with the trough closers' monthly objects on the release-day vintage, `s2/asof_trough.py`; the same record to the day; the live system runs on it, `cache/bhs_version.json` walk47 / w47 / v3.26; `RECORD-w47-2026-09-10.md`), `walk48.py` (the household co-signer admitting weak proposals to the strong proposers' confirmers — tested, not adopted) and `walk49.py` (walk48 with building permits in the housing × rate pair, `s2/asof_permits.py` — tested, refused: a false alarm 26 June 2025 in the walked diary and 1969 at +89); the diagnostics `s2/q15.py` (the proposer and confirmer of every walked call), `q16.py` (nine candidate clauses frozen on the vintage), `q17.py` (the trough closers, first print against vintage), `q18.py` (the menu dated), `q20.py` (permits frozen), `q21.py` (the candidates under the walk and the June 2025 near-miss), `q22.py`; `s2/verify_paper.py` (a verifier row for every number the executive summaries print; `RECORD-PAPER-v326-2026-09-10.md`); the unused builder patches `s2/patch_build2.py`, `s2/patch_update2.py` (written for a v3.27 that was not adopted). The memo: `Recession Papers/BRISTOW-HALL-RULE-SPEED-v327-2026-09-10.md`; the amendment: `PREREG-BRISTOW-HALL-RULE-v3.26-AMENDMENT-2026-09-10.md`; the permits data: collection 107."""
def r105(s): return s.rstrip('\n')+R105_ADD+'\n'
edit(os.path.join(C105,'README.md'),r105)
edit(os.path.join(RP,'BRISTOW-HALL-SYSTEM-README-105-2026-09-08.md'),r105)
R107_ADD="""

**Outcome (10 September 2026, later).** The permits clause was walked (collection 105, `walk49.py`) and refused: the 1969
call moves from 6 October 1969 to 30 March 1970 (permits had fallen 21 log points by September 1969 where starts had fallen
29), and the walk's re-choice of the survey-week line at the 1992 cut produces a false alarm on 26 June 2025. The data
stay: the transcription is a fact about 1990, whichever object the rule reads."""
def r107(s): return s.rstrip('\n')+R107_ADD+'\n'
edit(os.path.expanduser('~/Projects/Onset Detector Data/107_permits_first_prints_1990_2026-09-10/README.md'),r107)
print('all edits done')
