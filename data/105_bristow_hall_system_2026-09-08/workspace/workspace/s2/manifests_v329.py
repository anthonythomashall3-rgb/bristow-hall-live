# append the v3.29 sections, with file hashes, to the MANIFEST-NOTES of collections 105 and 108 (run on the Mac from 105/)
import hashlib,os,glob,shutil
def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
RP=os.path.expanduser('~/Projects/Recession Papers')
shutil.copy(os.path.join(RP,'BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md'),'SEARCH-WEEK-v327-2026-09-10.md')
shutil.copy(os.path.join(RP,'BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md'),'../108_high_frequency_speed_2026-09-10/SEARCH-WEEK-v327-2026-09-10.md')
files=['workspace/walk55.py','workspace/s2/search_week.py','workspace/s2/q38.py','workspace/s2/q39.py','workspace/s2/patch_v329.py','workspace/s2/patch_panel_2024.py','workspace/s2/audit_site.py','workspace/s2/inserts_v329.py','workspace/s2/apply_memo_v329.py','workspace/s2/memo_s9_v329.md','workspace/bhs_build.py','workspace/bhs_update.py','workspace/bhs_verify.py','workspace/cache/bhs_version.json','workspace/cache/w55_prog.pkl','workspace/cache/w55_carry.pkl','workspace/out/walk55_run.log','site/template.html','site/public/index.html','RECORD-w55-2026-09-10.md','AUDIT-SITE-v3.29-2026-09-10.md','AUDIT-TOOL-v3.29-2026-09-11.md','PREREG-v329-ADDENDUM-2026-09-10.md','NAME-AND-VERSION.md','SEARCH-WEEK-v327-2026-09-10.md','workspace/_v328_backup_2026-09-10/template_v329_pre_panel_2026-09-11.html']
rows='\n'.join(f'{h(f)}  {os.path.getsize(f)}  ./{f}' for f in files if os.path.exists(f))
missing=[f for f in files if not os.path.exists(f)]
txt=f"""

## Night of 10–11 September 2026 — v3.29 (walk55) live from 01:27 UTC (rebuilt 01:33 UTC)

`walk55.py` (walk54 with the sudden stop's search week on three terms — "unemployment", "layoffs", "laid off" — each over its own base, firing on the earliest; run 23:42–01:21 UTC, an hour lost to the Mac's sleep): nine of nine, none false, no line moved at any cut, the diary walk54's except 2020 (12 March 2020 for 16 March; `s2/cmpwalk.py w54 w55`). `bhs_verify.py w55` eighteen of eighteen, 177 files (`RECORD-w55-2026-09-10.md`; the reference column now labelled as the NBER's month and, for 2024, Paper 1's April–August 2024). `s2/q38.py` (frozen 1948–2026 with one term and with three: thirteen of thirteen each), `s2/q39.py` (the gates 20/15/12/10 with every term: only 20 clean), `s2/patch_v329.py` (the v3.29 patches), `s2/search_week.py` (`SEARCH_TERMS`, `GT_TERMS`, per-term feeds). The term histories, the as-of readings of March 2020 and the live feeds are collection 108. The addendum states the after-the-case choice of the two added terms at the level of the datum before the record (`PREREG-v329-ADDENDUM-2026-09-10.md`; Recession Papers copy). The v3.28 files are in `workspace/_v328_backup_2026-09-10/` (with `template_v329_pre_panel_2026-09-11.html`, the template as deployed at 01:27 before the panel patch).

Rule Zero on the way: (1) the first build failed — a loop variable `_rel` in the new per-term branch of `bhs_build.py` shadowed the page's release-calendar function; renamed `_trel`. (2) The 01:27 UTC build read the walk's clauses from walk55's own text and missed the hub's majority hold that walk55 carries by exec from walk54; 3 May 2024 stood on a held 1.00 over 0.933 — caught by `s2/audit_site.py` (44/47) five minutes after deployment; `bhs_build.py` now reads the whole chain of walk files (`_walk_chain`) and refuses to build when the diary's 2024 open lacks the hold; rebuilt 01:33 UTC, 47/47 (`AUDIT-SITE-v3.29-2026-09-10.md`; two checks made exact: the held-day check stops at the open day — 13 March 2020 reads 0.997, the market 19.94 under its high, the day after the call — and the per-term row count no longer counts the S&P row). (3) The speed panel's reference for 2024 was the rule's own month; now Paper 1's chronology (April–August 2024): seven of nine before the end of the peak month, 2024 +3 days and 91 days ahead of the Sahm rule (`s2/patch_panel_2024.py`; STANDING-RULES §81 clause 10). The whole night's checks: `AUDIT-TOOL-v3.29-2026-09-11.md`. The memo's §9 (`SEARCH-WEEK-v327-2026-09-10.md`, copy) records the search for "faster" and where it stops. Hashes:

{rows}
"""
open('MANIFEST-NOTES.md','a').write(txt); print('105 MANIFEST-NOTES appended', len(rows.splitlines()), 'missing', missing)
os.chdir('../108_high_frequency_speed_2026-09-10')
f8=sorted(glob.glob('google_trends/layoffs_*'))+sorted(glob.glob('google_trends/laidoff_*'))
live=sorted(glob.glob('google_trends/live/*.csv')); asof=sorted(glob.glob('google_trends/asof_terms/*'))
sc=sorted(glob.glob('scripts/*.py'))
rows8='\n'.join(f'| {p} | {os.path.getsize(p)} | {h(p)} |' for p in live+sc+['SEARCH-WEEK-v327-2026-09-10.md'])
txt8=f"""

## Outcome, night of 10–11 September 2026 — v3.29 reads three terms

The term histories `google_trends/layoffs_*` and `laidoff_*` ({len(f8)} files; `gt_terms_2026-09-10.tar.gz` archives the same files), the as-of readings `google_trends/asof_terms/` ({len(asof)} files: eight terms as of 10/11/12/13/16 March 2020, and "layoffs", "laid off", "unemployment" as of 2–9 March), the live feeds `google_trends/live/` (three terms, extended daily by `scripts/trends_live.py`) and the scripts are what v3.29 (collection 105, `walk55.py`) stands on: 2020 opens 12 March 2020 (+12) for 16 March. The memo (`SEARCH-WEEK-v327-2026-09-10.md`, §9) and the addendum (`105/PREREG-v329-ADDENDUM-2026-09-10.md`) state that the two added terms were chosen after the case at the level of the datum. Hashes of the live feeds, the scripts and the memo copy:

| file | bytes | sha256 (16) |
|---|---:|---|
{rows8}
"""
open('MANIFEST-NOTES.md','a').write(txt8); print('108 MANIFEST-NOTES appended: term files',len(f8),'asof',len(asof),'live',len(live),'scripts',len(sc))
