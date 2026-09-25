# ops/ — the update machinery, for whatever version of the tool is live

22 September 2026, collection 306. Anthony: *"I NEED TO KNOW IF EVERY UPDATE WORKS SUCCESSFULLY OR NOT ... MAKE SURE THAT
THE AUTOUPDATING FUNCTION OF THE WEBSITE IS ALWAYS FOR OUR MOST RECENT/BEST VERSION OF THE TOOL AND THAT WE ARE ALWAYS
CORRECT ON THE DAY AND TIME THAT THE NEW DATA COMES ... we need the automatic updating process to always be flawless no
matter what version of the tool is live."*

The tool (today the Bristow-Hall Rule, v3.x, in `data/105_…`) decides what the site says. `ops/` decides nothing about
the rule. It makes sure the update runs when data are released, tells Anthony how every run went, keeps the release
calendar current and the site's "next" days right, and keeps the site updating even if a new version breaks.

| file | what it does |
|---|---|
| `tool.json` | where the live tool keeps its entry, state, pages and slot list; the per-row calendar rules; the files that make a version what it is; the FOMC decision days |
| `run.sh` | the workflow's main step: the tool's entry with a 15-minute limit per attempt, a second try (never after a time-out), then the last good version; the verdict guard |
| `lastgood.py` | remembers the commit of the last run that published; puts that version back for one run (its code, and every file a person changed since that no run wrote); puts the new code back before anything is committed |
| `calendar_build.py` | every row's coming release times (FRED's calendars, the agencies' own pages, the rules for the rest) → `site/public/ops/release_calendar.json`; what is due and has not come → `state/pending.json`; **the run schedule** → `run_slots.json` |
| `inject.py`, `site/next_published.js` | the data page and front page roll a passed "next" day forward in the reader's browser, with its clock time and, where it applies, "due; not published yet"; the data page says when the site next updates |
| `notify.py` | one ntfy message per run: updated / retrying / held / failed, the version, the indicator's level and change, the standing, every series that moved (old → new), what is late, the next update and the next release; a GitHub issue for a failure nothing will retry (closed by the next good run) |
| `state/last_good.json` | committed by the runner after every full run that published with its own code |
| `state/pending.json` | releases whose time passed without their row moving; the look-again slots come from it |
| `cache/` | FRED's release calendars, the series→release map, the agencies' own calendars (refreshed daily; an outage costs nothing) |

## When the site updates

`calendar_build.py` writes `run_slots.json` after every build, and the two starters follow it (the Cloudflare Worker
`bhr-dispatch` every minute since 25 September 2026, collection 411; GitHub's own crons as the second line):

- 5 minutes after each timed release the site shows (20 minutes until 25 September 2026), or 5 minutes after FRED's usual post of it where the tool reads the
  release from FRED and FRED posts later than the agency (`state/fred_posted.json`, FRED's posting clock per release: the 75th
  percentile of its last nine posting days; seeded 23 September 2026 from FRED's archived series pages, collection 358, and
  extended at every run from each release's representative series); releases within 15 minutes of each other are one run;
- 4:20 PM on NYSE trading days (the S&P 500 close from the chart feed, settled by 4:15, and the day's H.15 post, FRED 4:16), and
  FRED's SP500 post plus eight minutes (about 8:10 PM) for the official close, so a provisional close never stands overnight
  (collection 411; one run at 5:05 PM until 25 September 2026);
- 9:05 AM on a day a rule-dated month becomes public, whatever else runs that day;
- GDPNow on the days of the releases it reads, at FRED's clock (its own slot since 23 September 2026);
- 10, 30 and 90 minutes after a release that was due and did not come, then at every run until it does;
- and any slot a `conditional_slots` rule asks for while the tool is in that state.

Nothing else. A run that finds nothing new says so in its message; it never publishes anything wrong.

## The contract — what any version of the tool must provide

A new version, or an entirely new tool, keeps the update flawless if it provides these. Change `tool.json` if a path
moves; nothing else in `ops/` needs to change.

1. **An entry script** (`tool.json` `entry`, today `run_cloud.sh`) that updates the data, builds, and writes the site
   into `site_public`. Exit 0 on success, non-zero on failure. It must be safe to run twice in a row.
2. **A published state** (`tool.json` `state`, JSON) with at least: `version` (e.g. "v3.71"); `built_at` ("YYYY-MM-DD
   HH:MM", New York time — the starters compare it with the release slots); `standing` (`state` "open" or "closed",
   `since`); the headline reading as `series.dates` + `series.values` (or `headline.value` + `headline.date`);
   `feeds`: one entry per input with `name`, `ids` (FRED series ids where they exist), `through`, `next`, `value`,
   `every` ("Monthly …" / "Weekly …" / "Daily …").
3. **A data page** (`tool.json` `data_page`) whose rows carry `data-ids`, `data-next`, `data-through` and `data-value`;
   the front page's tiles in the inline `H.tiles` (`sid`, `next`). Rows whose ids are FRED series get their calendar
   automatically; any other input needs a line in `tool.json` `calendar_rules` (`nyse_close`, `h15_daily` — the Board's
   business-day post at 4:15 PM, `fred_every_day` — FRED's daily post at its measured clock, weekends included, `utc_day_end`
   — the day's end in UTC for Google's series, `fomc`, `month_end_plus_21`, or `fred:<release id>`; `h15_week` and
   `daily_next_morning` remain for older pages). Where FRED is the publisher the tool reads (the fed funds target, the Sahm
   series, GDPNow) the page shows FRED's own posting clock, the median of its last nine posts.
4. **The files that carry its identity** in `tool.json` `version_files` (today `cache/bhs_version.json` and the page
   templates): the files a port rewrites in place. They are put back with the code when the last good version has to run,
   so that version runs as itself. The history is used first; this list is the fallback.
5. **Optionally, its own run slots** (`tool.json` `run_slots`). `calendar_build.py` writes that file from the release
   calendar in any case; a tool that writes its own is overwritten at the end of each run.

## Porting a new version

Commit it to `main` and push. The push starts the update at once (`update.yml` `on: push`); the phone says whether the
new version is live ("NEW VERSION LIVE: v3.70 → v3.71") or failed. If it fails, the last good version publishes in its
place (its own code, version file and template) until the new one is fixed, unless it would reach a different standing —
then nothing is published and the message says so. The repository always keeps the new code. There is no need to start a
run by hand. Pull before you push, and never copy `ops/`, `.github/workflows/update.yml` or `worker/` from an older
clone; if you redeploy the Worker, do it from an up-to-date clone (every run compares its version with `worker/src/index.js`).

## What the phone messages mean

| message | what happened | what to do |
|---|---|---|
| **Updated · indicator 0.433 → 0.441** | a run published; the lines under it are what moved | nothing |
| **Updated with the previous version** | the new code failed; the last good version published and the data are current | fix the new version (its error is in the message) |
| **Update did not go through · retrying by itself** | a run failed; the starter tries again in about ten minutes (up to three for one release) | nothing, unless it turns into FAILED |
| **Update HELD by the checks** | the build was made but the checks refused to publish it; the site still shows the last good build | look at the checks' line in the message |
| **Update FAILED** | a failure nothing will retry before the next release | the run log is linked in the message; a GitHub issue carries it too |
| **RECESSION CALLED / closed** (top priority) | the standing changed | read the site |
| **FRED KEY REFUSED / MISSING** (top priority; 23 Sep 2026, collection 356) | the run asked FRED whether it accepts the key (`ops/out/key_check.json`) and it does not: every FRED series stops updating while the run still publishes | put a working key in the repository secret `FRED_API_KEY` (Anthony rotates keys himself) |
| **CHECK (drift)** / **Yearly drift report** (23 Sep 2026, collection 356) | `ops/drift_report.py` measures what the objects measure (claims coverage of the unemployed, claims per job loser, the insured rate against the unemployment rate, the states' first-print noise); January's first message carries the summary, a crossed registered line a CHECK once a day | read `/ops/drift_report.json` on the site; a flag is a decision for Anthony, never an automatic change |
| **the site has stopped updating** (from the Worker; 23 Sep 2026, collection 356) | the dead-man: the site has carried one build for more than 72 hours and the newest release slot passed over two hours ago without a build | look at the Actions runs; the Worker's status page shows its decision (`?simulate_now=<ISO time>` shows what it would decide at another moment, sending nothing) |

## Testing a change to the machinery

Push it to a branch (never `main`) and start the workflow on that branch:
`gh workflow run update.yml -R anthonythomashall3-rgb/bristow-hall-live --ref <branch> -f origin=hand -f simulate=<fail_first|fail_primary|bad_fred_key|>` (`bad_fred_key`, the planted-key drill: a well-formed key FRED never issued, never the real one).
A branch run publishes a Cloudflare **preview** (never the site), pushes to its own branch, writes no ledger line, opens
no issue, and sends its message to the test topic `(the OPS_TEST_TOPIC secret)` (read it with
`curl -s https://ntfy.sh/(the OPS_TEST_TOPIC secret)/json?poll=1`).
