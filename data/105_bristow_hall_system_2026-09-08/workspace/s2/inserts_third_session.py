# apply the third-session paragraphs (v3.27, walk51) to the Recession Papers documents and the collection READMEs (run on the Mac)
import os,re,datetime
RP=os.path.expanduser('~/Projects/Recession Papers'); C105=os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08')
def edit(path,fn):
    s=open(path).read(); t=fn(s); assert t!=s, path; open(path,'w').write(t); print('edited',os.path.basename(path))
# ---- NAME-AND-VERSION: the table row, the 'current version' sentence, and the paragraph ----
ROW="| **v3.27** | 10 Sep | **walk51: the search week in the sudden stop (Google searches for unemployment, daily from 2004, the sudden stop's own numbers, the S&P 500 at that day's close) and building permits admitted beside starts in the housing × rate pair (either at the starts line, permits as they stood on the day). The current version.** Collection 108 (the daily series), collection 107 (permits as printed), collection 105 (the live system); `RECORD-w51-2026-09-10.md` |"
NV_ADD="""

**10 September 2026, third session — v3.27 (walk51) replaces v3.26** (`BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md`). Anthony's instruction: the tool may read any series that helps the calls, whatever its start date, entering at its own first observation (Rule 23 clause 3), read causally and with no false alarm on its span. Two objects passed. (1) **The search week.** The sudden stop reads one labour datum, a week of claims 35 per cent over its base, with the market 20 per cent under its 20-day high; the datum is weekly, which is why 2020 waited for the release of 19 March. The seven-day mean of Google searches for "unemployment" over the same base (the 28-day mean's 365-day low, or 0.85 of its five-year median), known the next morning and read with the S&P 500 at that day's close, is a daily labour datum on the same numbers; the sudden stop fires on the earlier of the claims week and the search week. With the market gate it fires on 7 October 2008 and 16 March 2020 and nowhere else 2004–2026 (alone it fires every January, so the gate is what makes it usable); as a user would have seen it, the search week stood 46 per cent over its base on Friday 13 March 2020 and the S&P closed 19.9 under its high, 198 per cent on Monday 16 March with the close 29.5 under. 2020 opens **16 March 2020 (+16)** instead of 19 March. (2) **Permits beside starts.** The housing × rate pair is confirmed by starts or by building permits at the starts line (29 log points below the twelve-month high of the three-month mean) with the unemployment rate 0.4 above its eighteen-month low; permits as they stood on the day (ALFRED vintages from August 1999, the Economic Indicators tables as printed for 1969 and 1990, collection 107, the current file elsewhere as a declared bound). Starts keep 1969; permits reached the line with the April 1990 print of 16 May 1990, and 1990 opens **26 July 1990 (−5)** instead of 19 September (+50). Walked from 1962 (walk51; 65 cuts): nine of nine, none false; opens 6 October 1969 (−86), 17 September 1973 (−74), 29 November 1979 (−63), 26 February 1981 (−155), 26 July 1990 (−5), 29 March 2001 (−2), 24 December 2007 (−7), 16 March 2020 (+16), 7 June 2024 (+38); median −7 days, eight of nine inside the month; troughs nine of nine, median +7. The walk moved one line, the survey-week rate's, from 0.4 to 0.3 at the 1992 cut, and kept it through 2026 with no alarm (the audit of that line: one proposal from 2024 on, 26 June 2025, with the nearest confirmer at 0.60 of its line). Frozen 1948–2026 at the walk-end lines: thirteen of thirteen, none false (1990 at 16 May 1990). `bhs_verify.py w51`, eighteen checks, 173 input files hashed. Refused in the same session, with their false alarms: the co-signer clause on these objects (walk52: 2024 at 1 February 2024 but a false alarm 26 June 2025), the hub read across the states (LAUS first prints; a false alarm 24 June 2025 with the hold, 2003 and 2025 without), consumer sentiment as a confirmer (18/8/6 alarms), and every market-only route to February 2020 (a 20-day drawdown of 10, 12 or 15 per cent has 16, 8 or 5 non-recession episodes since 1962). The one call after the month's end, 2020 at +16, is bound by the data: no labour datum existed before 12 March 2020. Deployed to the site 10 September 2026, 18:12 UTC; the v3.26 files are in `105/workspace/_v326_backup_2026-09-10/`."""
def nv(s):
    a="| **v3.26** | 10 Sep |"
    i=s.index(a); j=s.index("\n",i)
    s=s[:i]+s[i:j].replace("**walk46: every monthly object read as it stood on its release day (Rule 23 clause 1); the housing pair's line fixed at 1.0; v3.25's four clauses. The current version.**","walk46: every monthly object read as it stood on its release day (Rule 23 clause 1); the housing pair's line fixed at 1.0; v3.25's four clauses").replace("| **v3.26** |","| v3.26 |")+"\n"+ROW+s[j:]
    s=s.replace("**v3.26 is the current version of the Bristow Hall Rule**","**v3.26 was the current version of the Bristow Hall Rule until 10 September 2026, 18:12 UTC (v3.27 below)**",1)
    return s.rstrip('\n')+NV_ADD+'\n'
edit(os.path.join(RP,'BRISTOW-HALL-RULE-NAME-AND-VERSION.md'),nv)
# ---- HANDOFF ----
HO_ADD="""

**Third session, 10 September 2026 (evening).** **The current version is v3.27 (walk51)**, deployed 18:12 UTC: the search week in the sudden stop (2020 at 16 March, +16) and building permits beside starts in the housing × rate pair (1990 at 26 July 1990, −5); eight of nine calls inside the peak month, none false, median −7; `RECORD-w51-2026-09-10.md`; the memo `BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md`; the daily series in collection 108, the permits as printed in 107. The live system carries the search week's daily feed (`108/scripts/trends_live.py`, called by `bhs_update.py`), the permits vintage refresh, the Department of Labor's own release as the first-print source when FRED lags (`bhs_dol_press.py`), and data-derived 'next release' dates. Refused with their alarms: the co-signer clause (walk52, 26 June 2025), the state hub, sentiment, every market-only route to February 2020. What remains open: 2020 (+16) is data-bound and 2024 (+38) has no clean lever; the 2024 trough's evidence; the state cross-section; the United Kingdom and Canada; the executive summaries' rebuild at v3.27 and the pre-registration addendum (`PREREG-BRISTOW-HALL-RULE-v3.27-ADDENDUM-2026-09-10.md`)."""
def ho(s):
    a="**Second session, 10 September 2026 (later).**"
    i=s.index(a); j=s.index("\n\n",i) if "\n\n" in s[i:] else len(s); return s[:j]+HO_ADD+s[j:]
edit(os.path.join(RP,'HANDOFF-BRISTOW-HALL-RULE-2026-09-08.md'),ho)
# ---- STANDING-RULES §80 ----
SR_ADD="""

## §80 — 10 SEPTEMBER 2026, THIRD SESSION: THE EVOLVING MENU; A DAILY DATUM IN THE SUDDEN STOP; EITHER HALF OF A PAIR

1. **The menu evolves** (Anthony, 10 September 2026): the rule may read any series that helps a call, whatever its start
   date, entering at its own first observation (Rule 23 clause 3), provided it is read causally — publication lags
   charged, vintages where they exist, a reconstruction declared as a bound — and produces no false alarm on its span.
   A series that begins in 2004 is tested on 2004–2026 and nowhere else; what it would have done in 1969 is not a
   question. "Our tool can be evolving as the data is made available."
2. **A new series takes the rule's own numbers.** The search week reads the sudden stop's numbers (one week 35 per cent
   over the claims base; the market 20 per cent under its 20-day high); the permits half reads the starts line. No line
   was chosen for a new series in this session, and none may be: a candidate that needs its own number is a screen, not a
   clause (consumer sentiment, 10/15/20 points: 18/8/6 alarms).
3. **A datum published overnight is read at the close of the day it is known**; a datum published at 8:30 at the prior
   close. The search week fires on Monday 16 March 2020 at that day's close; Friday 13 March fails on both the datum known
   that morning (31 per cent) and the close (19.9).
4. **Either half of a pair may confirm** when both halves are the same object on the same line and the same release
   (starts or permits at the starts line, each as it stood on its day): the pair's reading is the larger of the two, its
   day the earlier of the two confirmations. Replacing one half by the other (walk49) is a different rule and lost 1969.
5. **The walk's own re-choice is part of the record.** walk51 moved the survey-week line from 0.4 to 0.3 at the 1992 cut
   and kept it for 34 cuts with no alarm; the audit of that line (one proposal from 2024 on; the nearest confirmer at 0.60 of
   its line) is written down with the record, as §79 clause 2 requires.
6. **The 2025 wall.** Every clause that lets 2024's weak proposals use the vacancy fires in June 2025 (the co-signer clause,
   walk52; the hub read across the states, q31). The clause is refused, not the year.
7. **2020 is bound by the data.** No labour datum existed before 12 March 2020; the market alone reaches the sudden stop's
   number on 12 March and fires in 1987, 2011, 2015, 2018 and 2025 without the labour gate; a smaller market number has
   16, 8 or 5 non-recession episodes since 1962 (10, 12, 15 per cent). A call before the end of February 2020 is not
   available to a causal rule with no false alarm. The WHO's emergency declarations with the sudden stop's market number
   would fire once, on 12 March 2020 (+12), and nowhere else among eight declarations — one observation; not adopted.
8. **The live system's first print of the week comes from the Department of Labor's own release when FRED lags**
   (10 September 2026: FRED posted three hours and twenty minutes late), and a release day whose data are not yet in hand
   is shown as pending, never as passed."""
def sr(s): return s.rstrip('\n')+SR_ADD+'\n'
edit(os.path.join(RP,'STANDING-RULES.md'),sr)
# ---- READMEs ----
R105_ADD="""

**v3.27 deployed, 10 September 2026, 18:12 UTC.** `cache/bhs_version.json` names `walk51.py` / w51 / v3.27. The live builder reads the either pair (`mkpair_either_asof` from walk51's preamble; `_pair_pub` in `bhs_build.py` takes the larger of the starts and permits halves) and the search week (`s2/search_week.py`; the reading row and the notes); `bhs_update.py` refreshes the permits vintage table and current file and the search week's daily feed. Found on the first live build and corrected (Rule Zero): `s2/asof_permits.py` rebound the lab's Sahm-gap series `g` in a loop variable, which broke the co-signer row; renamed, `bhs_verify.py w51` re-run (PASS, `RECORD-w51-2026-09-10.md`). The v3.26 builder and updater are `workspace/_v326_backup_2026-09-10/bhs_build_v326_final.py`, `bhs_update_v326_final.py`."""
def r105(s): return s.rstrip('\n')+R105_ADD+'\n'
edit(os.path.join(C105,'README.md'),r105)
edit(os.path.join(RP,'BRISTOW-HALL-SYSTEM-README-105-2026-09-08.md'),r105)
R107_ADD="""

**Outcome, revised (10 September 2026, evening).** Permits were admitted BESIDE starts (walk51, v3.27): the pair is
confirmed by either series at the starts line. Starts keep 1969; permits bring 1990 to 26 July 1990 (−5). The transcription
here is the reading the rule uses for April–September 1990."""
def r107(s): return s.rstrip('\n')+R107_ADD+'\n'
edit(os.path.expanduser('~/Projects/Onset Detector Data/107_permits_first_prints_1990_2026-09-10/README.md'),r107)
print('all edits done')
