# apply the v3.29 paragraphs to the Recession Papers documents and the collection READMEs (run on the Mac after deployment)
# usage: python3 inserts_v329.py DEPLOY_DATE DEPLOY_TIME   e.g. python3 inserts_v329.py "11 September 2026" "01:40"
import os,sys,re
DEPLOY_DATE=sys.argv[1]; DEPLOY_TIME=sys.argv[2]
RP=os.path.expanduser('~/Projects/Recession Papers')
C105=os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08')
C108=os.path.expanduser('~/Projects/Onset Detector Data/108_high_frequency_speed_2026-09-10')
def edit(path,fn):
    s=open(path).read(); t=fn(s); assert t!=s, path; open(path,'w').write(t); print('edited',os.path.basename(path))
def fill(t): return t.replace('DEPLOY_DATE',DEPLOY_DATE).replace('DEPLOY_TIME',DEPLOY_TIME)

NV_ROW_OLD_RE=r"\| \*\*v3\.28\*\*"   # the bold current row of the version table; unbold it and add the v3.29 row after it
NV_ADD=fill("""

**v3.29 (walk55), DEPLOY_DATE — the search week on three terms.** v3.28 with the search week read on "unemployment",
"layoffs" and "laid off", each over its own base with the sudden stop's numbers (35 over the base; the S&P 500 20 under its
20-day high), the sudden stop firing on the earliest of the claims week and the three search weeks. 2020 opens 12 March 2020
(+12; was 16 March, +16), the first day the market gate held (26.7 per cent under the 20-day high at that close) with a term
at the line — "layoffs" 57 and "laid off" 55 per cent over their bases on the morning of 12 March, as a user would have seen
them (collection 108, `google_trends/asof_terms/`); no other date changes and no line moves at any of the 65 cuts
(`s2/cmpwalk.py w54 w55`); frozen 1948–2026 thirteen of thirteen, none false (`s2/q38.py`). The two added terms were chosen
after the case, at the level of the datum: the addendum (`PREREG-BRISTOW-HALL-RULE-v3.29-ADDENDUM-2026-09-10.md` §2)
states this before the record, with the reason the tests cannot catch it (with the gate at 20 any term passes, since the
gate has held only in 2008–09 and from 12 March 2020) and the evidence that no zero-false-alarm form of the sudden stop
reaches an earlier day (the lower gates 15, 12 and 10 each produce false alarms, `s2/q39.py`). Deployed DEPLOY_TIME UTC on
DEPLOY_DATE; the v3.28 files are in `105/workspace/_v328_backup_2026-09-10/`; the memo is §9 of
`BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md`.""")

HO_ADD=fill("""

**v3.29 (walk55), DEPLOY_DATE.** Anthony asked whether 2020 could be faster still and whether the tool was being fitted.
The market gate (20 under the 20-day high) first held on 12 March 2020; "unemployment" reached its line only on the 16th,
while "layoffs" and "laid off" stood at 57 and 55 over their bases on the morning of the 12th (eight terms read as of
10–16 March as a user saw them; collection 108 `asof_terms/`). The search week now reads the three terms, each over its own
base with the same numbers, and 2020 opens 12 March (+12). Frozen thirteen of thirteen (`s2/q38.py`); walked nine of nine,
no line moved, only 2020 differs (`walk55.py`, `cmpwalk.py w54 w55`); deployed DEPLOY_TIME UTC. The terms were chosen after
the case at the level of the datum, and the addendum says so before the record, with the two facts that bound the claim:
with the gate at 20 the no-false-alarm test is nearly vacuous for the datum, and the lower gates all produce false alarms
(`s2/q39.py`), so 12 March is 2020's floor for any zero-false-alarm form of the sudden stop. TSA throughput went public on
18 March 2020 and cannot beat it. **The current version is v3.29.** What remains open: the 2024 trough's evidence; the state
cross-section; the United Kingdom and Canada; the added terms' standing, which the next recession decides.""")

SR_ADD=fill("""
9. **A datum chosen after the case is disclosed at the level of the datum, before the record, and the gate is named as what
   carries the test.** v3.29 (walk55) reads the search week on "unemployment", "layoffs" and "laid off", and 2020 opens
   12 March 2020 (+12) for 16 March. The two added terms were kept because they stood at the line on 11 March 2020 as a
   user would have seen them (collection 108, `google_trends/asof_terms/`): a choice made after the case at the level of the
   datum, stated in the addendum's §2 before the record. Two rules follow. (a) With the market gate at 20 per cent under the
   20-day high the no-false-alarm test is nearly vacuous for the labour datum — since 2004 the gate has held only in
   October 2008–March 2009 and from 12 March 2020 — so a passing frozen run and a passing walk are not evidence that the
   datum discriminates; the gate carries the property, and the document says so rather than letting the record imply
   otherwise. (b) The lower gates were tested with every term (`s2/q39.py`): 15 fires 8 August 2011; 12 fires 2011, June
   2022 and April 2025; 10 fires ten episodes. So 20 is the only clean gate and 12 March 2020 is the earliest day any
   zero-false-alarm form of the sudden stop can reach; a day before the gate's first day cannot be bought with a datum, only
   with a false alarm, and the search for "faster" stops there and says so. Deployed DEPLOY_TIME UTC on DEPLOY_DATE.""")
def sr(s):
    # §81 is the last section; append clause 9 after its last clause
    assert '## §81' in s, 'no §81'
    return s.rstrip('\n')+'\n'+SR_ADD+'\n'

R105_ADD=fill("""

**Night of 10 September 2026 — v3.29 (walk55).** `walk55.py` (walk54 with the search week on three terms, `SEARCH_TERMS =
['unemp','layoffs','laidoff']`; nine of nine, none false; the diary differs from walk54 in 2020 only, 12 March 2020 for
16 March; no line moved; `RECORD-w55-2026-09-10.md`), `s2/search_week.py` (per-term histories, `GT_TERMS`, `leg_K_search`
firing on the earliest term), `s2/q38.py` (frozen 1948–2026 with one term and with three: thirteen of thirteen each; each
added term with the gate fires 7 October 2008 and 12 March 2020 only), `s2/q39.py` (the gates 20, 15, 12 and 10 with every
term: only 20 is clean), `s2/patch_v329.py` (the idempotent patches to `bhs_build.py`, `bhs_update.py`, `bhs_verify.py` and
`site/template.html`), `s2/audit_site.py` (the 2020 checks made generic over the terms; one readings row per term; the
superseded call-day check), `bhs_verify.py` (w55 expected values). `cache/bhs_version.json` names walk55 / w55 / v3.29
from DEPLOY_TIME UTC on DEPLOY_DATE; the v3.28 files are in `_v328_backup_2026-09-10/`. The term histories and the
as-of readings are collection 108; the addendum is `Recession Papers/PREREG-BRISTOW-HALL-RULE-v3.29-ADDENDUM-2026-09-10.md`;
the memo is §9 of `BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md`.""")
def r105(s): return s.rstrip('\n')+R105_ADD+'\n'

R108_ADD=fill("""

**Outcome (night of 10 September 2026).** Eight labour terms were read as of 10, 11, 12, 13 and 16 March 2020 as a user would
have seen them (`google_trends/asof_terms/`, `scripts/fetch_trends_asof_terms.py`, `asof_reading.py`; the early windows of
2–9 March in the same folder, `fetch_asof_early.py`). On the morning of 12 March "layoffs" stood 57 per cent over its base,
"laid off" 55, "unemployment insurance" 51, "furlough" 193 and "lost my job" 144 (thin bases), "unemployment" 25,
"unemployment claim" 13, "unemployment office" 8. The full histories of "layoffs" and "laid off" were reconstructed as
"unemployment"'s was (`google_trends/layoffs_*`, `laidoff_*`, 103 files; `scripts/fetch_terms_full.py`, `test_terms.py`;
`gt_terms_2026-09-10.tar.gz` is the same files archived), and the live feeds extend every term daily
(`google_trends/live/`, `scripts/trends_live.py`; the v3.27 one-term feed is `trends_live_v327.py`). v3.29 (collection 105,
`walk55.py`) reads the three terms and opens 2020 on 12 March (+12). The Wayback evidence that the TSA throughput page went
public on 18 March 2020 is `tsa/wayback_2020/`.""")
def r108(s): return s.rstrip('\n')+R108_ADD+'\n'

SR_FIX_OLD="""corrected. The 2020 floor stands at 16 March: no daily datum stood 35 per cent from its base by 11 March (search 22,
   TSA −19), and on 13 March the market stood 19.9 under its high against the gate of 20."""
SR_FIX_NEW="""corrected. The 2020 floor stands at 16 March: no daily datum stood 35 per cent from its base by 11 March (search 22,
   TSA −19), and on 13 March the market stood 19.9 under its high against the gate of 20. [Corrected 11 September 2026,
   clause 9 below: that was true of "unemployment" and of TSA, not of every labour term — "layoffs" stood 57 and "laid
   off" 55 per cent over their bases on 11 March 2020 as a user would have seen them — and the floor is 12 March, the
   first day the market gate held.]"""
NV_ROW_OLD="""| **v3.28** | 10 Sep | **walk54: the hub's hold read as the latest JOLTS print at the line OR the vacancy at the line in a majority (five or more) of the prior nine months' prints as published — the hold's own window, no new line; 2024 opens 3 May 2024 (+3) for 7 June (+38). The current version.** Collection 105; `RECORD-w54-2026-09-10.md`; `PREREG-BRISTOW-HALL-RULE-v3.28-ADDENDUM-2026-09-10.md` |"""
NV_ROW_NEW=fill("""| v3.28 | 10 Sep | walk54: the hub's hold read as the latest JOLTS print at the line OR the vacancy at the line in a majority (five or more) of the prior nine months' prints as published — the hold's own window, no new line; 2024 opens 3 May 2024 (+3) for 7 June (+38). Current from 19:42 UTC on 10 September to DEPLOY_TIME UTC on DEPLOY_DATE. Collection 105; `RECORD-w54-2026-09-10.md`; `PREREG-BRISTOW-HALL-RULE-v3.28-ADDENDUM-2026-09-10.md` |
| **v3.29** | 11 Sep | **walk55: the search week read on three terms — "unemployment", "layoffs", "laid off" — each over its own base with the sudden stop's numbers, firing on the earliest; 2020 opens 12 March 2020 (+12) for 16 March (+16), the first day the market gate held; the two added terms chosen after the case at the level of the datum (addendum §2). The current version.** Collections 105 and 108; `RECORD-w55-2026-09-10.md`; `PREREG-BRISTOW-HALL-RULE-v3.29-ADDENDUM-2026-09-10.md` |""")
HO_HEAD_OLD="**v3.28 (walk54) IS THE CURRENT VERSION, deployed 19:42 UTC, 10 September 2026**"
HO_HEAD_NEW=fill("**v3.28 (walk54) was the current version from 19:42 UTC, 10 September 2026, to DEPLOY_TIME UTC, DEPLOY_DATE**")
HO_ADD2=fill("""

**v3.29 (walk55) IS THE CURRENT VERSION, deployed DEPLOY_TIME UTC, DEPLOY_DATE** (`PREREG-BRISTOW-HALL-RULE-v3.29-ADDENDUM-2026-09-10.md`; `RECORD-w55-2026-09-10.md`; `AUDIT-SITE-v3.29-2026-09-11.md`; the memo's §9). The search week reads three terms — "unemployment", "layoffs" and "laid off" — each over its own base with the sudden stop's numbers, firing on the earliest. 2020 opens 12 March 2020 (+12) for 16 March (+16): the market gate first held at that day's close (26.7 per cent under the 20-day high), and "layoffs" stood 57 and "laid off" 55 per cent over their bases on the morning of the 12th, as a user would have seen them (eight terms read as of 10–16 March 2020; collection 108, `google_trends/asof_terms/`). Frozen thirteen of thirteen, none false (`s2/q38.py`); walked nine of nine, none false, no line moved at any cut, the diary walk54's except 2020 (`walk55.py`; `s2/cmpwalk.py w54 w55`). The record: 6 Oct 1969 (−86), 17 Sep 1973 (−74), 29 Nov 1979 (−63), 26 Feb 1981 (−155), 26 Jul 1990 (−5), 29 Mar 2001 (−2), 24 Dec 2007 (−7), 12 Mar 2020 (+12), 3 May 2024 (+3); median −7; troughs nine of nine, median +7. The two added terms were chosen after the case at the level of the datum; the addendum states it before the record, with the two facts that bound the claim — with the gate at 20 the no-false-alarm test is nearly vacuous for the datum (the gate has held only in 2008–09 and from 12 March 2020), and the lower gates all produce false alarms (`s2/q39.py`: 15 → 8 August 2011; 12 → 2011, June 2022, April 2025; 10 → ten episodes), so 12 March is 2020's floor for any zero-false-alarm form of the sudden stop. TSA throughput went public on 18 March 2020 and cannot beat it. The live system reads the terms named by `SEARCH_TERMS` (`s2/search_week.py`), the page carries the daily branch as the strongest term each day and one readings row per term, and the rule's statement on the page names the three terms and the date the two were chosen. The v3.28 files are in `105/workspace/_v328_backup_2026-09-10/`. What remains open: the 2024 trough's evidence; the state cross-section; the United Kingdom and Canada; the added terms' standing, which the next recession decides; the executive summaries are at v3.26 (Anthony: not needed on the site).""")

if __name__=='__main__':
    def sr2(s):
        assert SR_FIX_OLD in s, 'clause 8 anchor'
        s=s.replace(SR_FIX_OLD,SR_FIX_NEW)
        return s.rstrip('\n')+'\n'+SR_ADD+'\n'
    edit(os.path.join(RP,'STANDING-RULES.md'),sr2)
    for p in (os.path.join(C105,'README.md'),os.path.join(RP,'BRISTOW-HALL-SYSTEM-README-105-2026-09-08.md')):
        edit(p,r105)
    edit(os.path.join(C108,'README.md'),r108)
    def nv(s):
        assert NV_ROW_OLD in s, 'NV row anchor'
        s=s.replace(NV_ROW_OLD,NV_ROW_NEW)
        return s.rstrip('\n')+NV_ADD+'\n'
    def ho(s):
        assert HO_HEAD_OLD in s, 'HO head anchor'
        s=s.replace(HO_HEAD_OLD,HO_HEAD_NEW)
        i=s.index(HO_HEAD_NEW); j=s.index('\n\n',i)
        s=s[:j]+HO_ADD2+s[j:]
        s=s.replace('The current version is **v3.26** (10 September 2026; §0 below','The current version is **v3.29** (11 September 2026; §0 below')
        return s
    edit(os.path.join(RP,'BRISTOW-HALL-RULE-NAME-AND-VERSION.md'),nv)
    edit(os.path.join(RP,'HANDOFF-BRISTOW-HALL-RULE-2026-09-08.md'),ho)
    print('all edits done')
