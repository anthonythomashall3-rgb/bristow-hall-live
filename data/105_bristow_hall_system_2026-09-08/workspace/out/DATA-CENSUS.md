# The data census - 2026-09-25 (the tool v3.74, built 2026-09-25 12:02)

Every input the live tool reads: the publisher and route, the backup or substitute, the schedule, what is in hand, and the guard on its format. Gaps are listed at the end.

| feed | series | source | every | in hand through | next | backup or substitute | format guard |
|---|---|---|---|---|---|---|---|
| Initial claims, continued claims, insured unemployment rate | ICSA, CCSA, IURSA | Department of Labor (the UI claims news release; ALFRED vintages after it; the f | Weekly - Thursday 8:30 AM ET (Wednesday before a Thursday ho | 2026-09-19 | 2026-10-01 | the states' ETA 539 weekly file with the Bureau's seasonal factors (s2/claims_substitute.py, exact where teste | q41 feed checks; the claims loader asserts the release week columns (45) |
| State insured unemployment rates (the breadth object) | ETA 539 state insured rates | Department of Labor (page 8 of the weekly release; the advance state table of th | Weekly - Thursday 8:30 AM ET, one week behind initial claims | 2026-09-12 | 2026-10-01 | the advance state table of the weekly release PDF while the archive catches up | the page-8 parse validated against the advance table |
| Unemployment rate, factory hours, nondurable employment | UNRATE, AWHMAN, NDMANEMP, PAYEMS | Bureau of Labor Statistics, Employment Situation | Monthly - usually the first Friday, 8:30 AM ET | 2026-08-01 | 2026-10-02 | the Chicago Fed real-time unemployment forecast; ADP private payrolls (LSEG first prints) - declared, not auto | q41: the tile and the readings recomputed from the fetched files |
| Job openings (the vacancy rate) | JTSJOL, CLF16OV | Bureau of Labor Statistics, JOLTS | Monthly - about five weeks after the month, 10:00 AM ET | 2026-07-01 | 2026-09-29 | the Indeed Hiring Lab postings index, at most two months (s2/vacancy_bridge.py; collection 330) | walk39 asserts the vacancy first prints are not stale (>150 rows, within 8 months) |
| Housing starts and building permits | HOUST, PERMIT | Census Bureau, New Residential Construction | Monthly - about the 17th, 8:30 AM ET | 2026-08-01 | 2026-10-20 | building permits beside starts (the pair reads either); the Census calendar | q41 feed checks |
| Commercial paper and three-month bill rates (the spread) | DCPF1M, DCPN30, WTB3MS | Federal Reserve, H.15 selected interest rates | Daily - the Board posts the H.15 every business day at 4:15  | 2026-09-23 | 2026-09-25 | FRED DCPN30, DCPF1M and DTB3 (the Federal Reserve is not shut in a shutdown) | q41: the paper rates and their last printed day |
| S&P 500 daily close (the market gate of the sudden stop, the activity  | ^GSPC | Yahoo Finance close at the 5:05 PM ET run, corrected to the official close on FR | Every trading day - read at the 5:05 PM ET run | 2026-09-24 | 2026-09-25 | the official FRED SP500 close when the chart feed fails (two independent quotes) | q41: reading matches the readings table; two sources compared |
| Industrial production, as published (the activity opener) | INDPRO | Federal Reserve, G.17 Industrial Production and Capacity Utilization (each month | Monthly - about the 16th, 9:15 AM ET | 2026-08 | 2026-10-16 | the FRED current file of INDPRO (flagged: revised values), then the G.17 release text | activity_opener.py: the vintage history appended and checked |
| Federal funds target range, upper limit (the activity opener's tighten | DFEDTARU | Federal Reserve, FOMC statement (FRED DFEDTARU, the daily series) | Daily - FRED posts the series every day, weekends included,  | 2026-09-25 | 2026-09-26 | the FOMC statement on federalreserve.gov (the rate carried from the last reading until then) | activity_opener.py: the FOMC calendar end alert (watchdog) |
| State continued weeks claimed, ETA 539 (the activity opener's breadth  | ETA 539 | Department of Labor, ETA 539 weekly state claims (continued weeks claimed, by st | Monthly - each month is read 21 days after it ends, from the | 2026-08 | 2026-10-21 | the ETA 5159 monthly report (slower), then the last month read | state539_live.py: the 539 file columns asserted |
| State unemployment rates, all 51 (the second opener) | LAUS state rates (51) | Bureau of Labor Statistics, Local Area Unemployment Statistics, as first printed | Monthly - with the State Employment and Unemployment release | 2026-08-01 | 2026-10-20 | the states' ETA 539 insured-rate acceleration, at most two months (collection 336) | state_breadth.py: 45-state coverage guard; q41 v3.72 checks |
| Real GDP (the damage grade's output dimension) | GDPC1 | Bureau of Economic Analysis, Gross Domestic Product news release (FRED GDPC1, th | Quarterly - the advance estimate about four weeks after the  | 2026-04 | 2026-09-30 | GDPNow for the unprinted quarter; the BEA release text | damage_dimensions.py: the vintage table read by column name; q41 v3.73 checks |
| GDPNow (the output dimension's bridge for the quarter not yet printed) | GDPNOW | Federal Reserve Bank of Atlanta, GDPNow (FRED GDPNOW, every update as a vintage) | Several times a month, on the days of the releases it reads  | 2026-07 | 2026-09-30 | the Atlanta Fed page; the last printed quarter carried | the vintage appender names each vintage by its FRED date |
| Sahm rule, real time (the comparator on the speed panel) | SAHMREALTIME | FRED SAHMREALTIME | Monthly - FRED posts it on the morning of the employment rep | 2026-08 | 2026-10-02 | computed from the unemployment rate first prints if FRED SAHMREALTIME lapses | q41: the speed panel |
| Search week: Google searches for "unemployment" (the sudden stop's sec | Google Trends "unemployment" | Google Trends, United States, daily index stitched onto one scale and extended e | Daily - a day's index is complete when the day ends in UTC ( | 2026-09-24 | 2026-09-25 | the claims week alone at any cell looser than (35, 20) (E34c); a second search source is not yet declared (R2) | the collector's anchored window and the R2 shape guard (108/scripts/trends_live.py: a re-f |
| Search week: Google searches for "layoffs" (the sudden stop's second l | Google Trends "layoffs" | Google Trends, United States, daily index stitched onto one scale and extended e | Daily - a day's index is complete when the day ends in UTC ( | 2026-09-24 | 2026-09-25 | the claims week alone at any cell looser than (35, 20) (E34c); a second search source is not yet declared (R2) | the collector's anchored window and the R2 shape guard (108/scripts/trends_live.py: a re-f |
| Search week: Google searches for "laid off" (the sudden stop's second  | Google Trends "laid off" | Google Trends, United States, daily index stitched onto one scale and extended e | Daily - a day's index is complete when the day ends in UTC ( | 2026-09-24 | 2026-09-25 | the claims week alone at any cell looser than (35, 20) (E34c); a second search source is not yet declared (R2) | the collector's anchored window and the R2 shape guard (108/scripts/trends_live.py: a re-f |

## The channels (E5: current, stale, substitute, dark)

| channel | status | last | limit (days) | substitute |
|---|---|---|---|---|
| initial and continued claims, insured unemployment rate (DOL weekly) | current | 2026-09-19 | 13 |  |
| insured unemployment rate as the proposers read it | current | 2026-09-12 | 20 |  |
| unemployment rate, factory hours, nondurable jobs (BLS Employment Situ | current | 2026-08-01 | 45 |  |
| job openings (BLS JOLTS) | current | 2026-07-01 | 80 |  |
| paper and bill rates (Federal Reserve H.15) | current | 2026-09-18 | 12 |  |
| S&P 500 close | current | 2026-09-24 | 5 |  |
| industrial production as published (Federal Reserve G.17) | current | 2026-09-18 | 45 |  |
| the policy rate (FOMC target range, FRED DFEDTARU) | current | 2026-09-25 | 10 |  |
| state breadth (ETA 539 continued weeks by state, over payrolls) | current | 2026-08 | 56 |  |
| state unemployment rates, all 51 (BLS LAUS first prints; the second op | current | 2026-08 | 56 |  |

## Gaps

- none
