# log the feed work of 11 September 2026 (run from 105/workspace): MANIFEST sections in 105, 37 and 45, and the audit
# document's §7. Every file hashed.
import hashlib,os,glob
def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
def sz(p): return os.path.getsize(p)
C=os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08')
C37=os.path.expanduser('~/Projects/Onset Detector Data/37_dol_eta5159_2026-09')
C45=os.path.expanduser('~/Projects/Onset Detector Data/45_dol_first_prints_2026-09')
RP=os.path.expanduser('~/Projects/Recession Papers')

os.chdir(C)
files=['workspace/s2/patch_feeds.py','workspace/s2/state539_live.py','workspace/s2/state_press_live.py','workspace/s2/state_page8_backfill.py','workspace/s2/log_feeds.py','workspace/bhs_update.py','workspace/bhs_build.py','site/template.html','site/public/index.html','AUDIT-SITE-v3.29-2026-09-11.md']
rows='\n'.join(f'{h(f)}  {sz(f)}  ./{f}' for f in files if os.path.exists(f))
open('MANIFEST-NOTES.md','a').write(f"""

### Every feed on the page, and two feeds that had stopped (11 September 2026, 09:35 UTC)

Anthony: "make sure ALL of our data updates on the site, and EVERYTHING IS AUTOMATICALLY UPDATING, including the most recent data that we added, and make sure that it is shown". The page now carries a table of every series the rule reads - source, how often it updates, what it is in hand through, and when it next updates - built from the state JSON's new `feeds` block (`s2/patch_feeds.py` patched `bhs_build.py` and `site/template.html`); the "Next data" list now names the daily 4:20 PM Eastern run (the S&P 500 close and the three search terms), which it had never shown, and lists eight dated releases instead of six, so JOLTS and the employment report appear.

Building that table found two feeds that were not updating at all. (1) The Department's ETA 539 state panel (collection 37) was built once on 4 September and never refreshed; `s2/state539_live.py` now extends it at every run, weeks after its last only, and saves the Department's file beside it. (2) The state FIRST PRINTS the breadth proposer reads (collection 45, `state_iu_first_print_wide.csv`) were built from the Department's page-8 archive, which runs about two weeks behind and has 41 weeks missing; `s2/state_press_live.py` now parses the advance state table out of the weekly press release PDF this system already downloads, so the first prints keep up with the release itself (the week ending 29 August 2026 was added). The breadth object itself still reads through 22 August 2026 because it is a year-over-year share and its base week, 30 August 2025, is one of the archive's holes (the Department's 2025 archive is missing 8 weeks; `s2/state_page8_backfill.py` fetches what the archive has and reports what it does not). The page states this in the feeds table rather than showing a date that would imply the object is current. The object is a weak proposer standing at 0.23 against a line of 0.60, so nothing in the standing turns on it.

Hashes:

{rows}
""")
print('105 MANIFEST appended')

for col,txt in [(C37,f"""

**Refreshed automatically from 11 September 2026.** The panel was built once (4 September 2026) and had stopped at the week ending 22 August 2026. `105/workspace/s2/state539_live.py` now extends `panel/panel_539_weekly.csv` at every run of the live system - only weeks after its last, so the weeks in hand keep their first-published values - and replaces `raw/ar539.csv` with the Department's current file (the copy it replaces is kept as `.bak`). The panel is through {__import__('pandas').read_csv(os.path.join(C37,'panel','panel_539_weekly.csv'),parse_dates=['week'])['week'].max().date()} as of that date.
"""),(C45,f"""

**Refreshed automatically from 11 September 2026.** The state first prints had stopped at the insured-unemployment week ending 22 August 2026: they were built from the Department's page-8 archive, which runs about two weeks behind the release and is missing 41 weeks (2 in 2002, 1 in 2007, 29 in 2019, 1 in 2022, 8 in 2025). `105/workspace/s2/state_press_live.py` now parses the advance state table on page 4 of the weekly claims press release - the PDF `bhs_dol_press.py` already saves in `raw/press_live/` - and appends each week to `state_iu_first_print_wide.csv` and `state_ic_first_print_wide.csv` (backups `.bak`); the week ending 29 August 2026 was added this way and matches the release (Alabama 6,630; California 326,122). `s2/state_page8_backfill.py` fills holes from the archive where the archive has them; for the eight missing weeks of 2025 it does not, and the Wayback Machine holds only one of them (13 September 2025). Because the breadth object is a year-over-year share, each missing week costs two readings - its own and the week 52 weeks later - which is why the object reads through 22 August 2026 while the data are in hand through 29 August 2026. Stated on the site in the feeds table.
""")]:
    p=os.path.join(col,'MANIFEST-NOTES.md')
    if not os.path.exists(p): p=os.path.join(col,'README.md')
    open(p,'a').write(txt); print('appended',os.path.basename(col),os.path.basename(p))

ITEM="""
9. **Two feeds were not updating at all, and the page did not say what updates when** (Anthony, 11 September 2026).
   The page's "Next data" list named only the dated releases; the daily run that reads the S&P 500 close and the three
   search terms - the newest data in the rule - appeared nowhere. The page now carries a table of every series the rule
   reads with its source, its cadence, what it is in hand through and when it updates next (`s2/patch_feeds.py`;
   `feeds` in the state JSON). Building it found that the Department's ETA 539 state panel (collection 37) and the state
   first prints the breadth proposer reads (collection 45) had both been built once and never refreshed; both are now
   extended at every run (`s2/state539_live.py`, `s2/state_press_live.py`, wired into `bhs_update.py`). The breadth
   object still reads through 22 August 2026 because its year-over-year base week, 30 August 2025, is one of 41 weeks
   missing from the Department's page-8 archive; the feeds table says so on the page, and `s2/state_page8_backfill.py`
   records what the archive can and cannot fill. Deployed 09:35 UTC; `s2/audit_site.py` 47/47.
"""
p=os.path.join(C,'AUDIT-TOOL-v3.29-2026-09-11.md'); t=open(p).read()
a="\n## 8. What the audit does not establish"
assert t.count(a)==1
open(p,'w').write(t.replace(a,ITEM+a))
import shutil; shutil.copy(p,os.path.join(RP,'BRISTOW-HALL-RULE-AUDIT-TOOL-v329-2026-09-11.md'))
print('audit doc item 9 added')
