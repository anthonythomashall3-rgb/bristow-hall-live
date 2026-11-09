# The data census - 2026-11-09 (the tool C1021+E22, built 2026-11-09 11:53)

Every input the live tool reads: the publisher and route, the backup or substitute, the schedule, what is in hand, and the guard on its format. Gaps are listed at the end.

| feed | series | source | every | in hand through | next | backup or substitute | format guard |
|---|---|---|---|---|---|---|---|
| Initial claims and continued claims, seasonally adjusted and not (the  | ICSA, CCSA, ICNSA, CCNSA | Department of Labor (the UI claims news release; ALFRED vintages after it; the f | Weekly - Thursday 8:30 AM ET (Wednesday before a Thursday ho | 2026-10-31 | 2026-11-12 | the states' ETA 539 weekly file with the Bureau's seasonal factors (s2/claims_substitute.py, exact where teste | q41 feed checks; the claims loader asserts the release week columns (45) |
| Unemployment rate, payrolls, the unemployed count, job losers (the hou | UNRATE, PAYEMS, UNEMPLOY, LNS13023621 | Bureau of Labor Statistics, Employment Situation (each month as first printed: A | Monthly - usually the first Friday, 8:30 AM ET | 2026-10 | 2026-12-04 | ALFRED's vintage tables appended each release (bhs_update); the last vintage in hand stands until the next; a  | c1021.py: each vintage read by its dated column; q41 C1021 checks (the thirteen opens, the |
| Job openings (the help-wanted pillar: openings growing slower than cla | JTSJOL | Bureau of Labor Statistics, JOLTS (ALFRED JTSJOL, each month as first printed) | Monthly - about five weeks after the month, 10:00 AM ET | 2026-09 | 2026-12-01 | the Indeed Hiring Lab postings index, at most two months (s2/vacancy_bridge.py; collection 330) | walk39 asserts the vacancy first prints are not stale (>150 rows, within 8 months) |
| Industrial production (the production pillar) | INDPRO | Federal Reserve, G.17 Industrial Production and Capacity Utilization (ALFRED IND | Monthly - about the 16th, 9:15 AM ET | 2026-09 | 2026-11-17 | the FRED current file of INDPRO (flagged: revised values), then the G.17 release text | c1021.py: the newest G.17 print within its ALFRED vintage; the vintage history appended an |
| Moody's Baa corporate bond yield, monthly average (the credit pillar) | BAA | Federal Reserve H.15 via FRED (BAA); read the 7th of the month after | Monthly - the month's average, posted by FRED on the first b | 2026-10 | 2026-12-07 | the FRED monthly series cached (cache/c1021/BAA.csv, private); the cache stands when FRED is unreachable | c1021.py: fredgraph csv parsed by header, a bad parse stops the run; q41 feed checks |
| Effective federal funds rate, monthly average (the fed-shock door) | FEDFUNDS | Federal Reserve H.15 via FRED (FEDFUNDS) | Monthly - the month's average, known the day after month end | 2026-10 | 2026-12-01 | the FRED monthly series cached (cache/c1021/FEDFUNDS.csv); the cache stands when FRED is unreachable | c1021.py: fredgraph csv parsed by header; q41 feed checks |
| 10-year and 1-year Treasury yields, monthly averages (the job-losers d | GS10, GS1 | Federal Reserve H.15 via FRED (GS10, GS1) | Monthly - the month's averages, known the day after month en | 2026-10 | 2026-12-01 | the FRED monthly series cached (cache/c1021/GS10.csv, GS1.csv); the cache stands when FRED is unreachable | c1021.py: fredgraph csv parsed by header; q41 feed checks |
| S&P 500 daily close (the market pillar: below its close a year earlier | ^GSPC | Yahoo Finance close at the 5:05 PM ET run, corrected to the official close on FR | Every trading day - read at the 5:05 PM ET run | 2026-11-06 | 2026-11-09 | the official FRED SP500 close when the chart feed fails (two independent quotes) | q41: reading matches the readings table; two sources compared |
| Real GDP (the damage grade's output dimension) | GDPC1 | Bureau of Economic Analysis, Gross Domestic Product news release (FRED GDPC1, th | Quarterly - the advance estimate about four weeks after the  | 2026-07 | 2026-11-25 | GDPNow for the unprinted quarter; the BEA release text | damage_dimensions.py: the vintage table read by column name; q41 v3.73 checks |
| GDPNow (the output dimension's bridge for the quarter not yet printed) | GDPNOW | Federal Reserve Bank of Atlanta, GDPNow (FRED GDPNOW, every update as a vintage) | Several times a month, on the days of the releases it reads  | 2026-11-04 | 2026-11-17 | the Atlanta Fed page; the last printed quarter carried | the vintage appender names each vintage by its FRED date |
| Sahm rule, real time (the comparator on the speed panel) | SAHMREALTIME | FRED SAHMREALTIME | Monthly - FRED posts it on the morning of the employment rep | 2026-10 | 2026-12-04 | computed from the unemployment rate first prints if FRED SAHMREALTIME lapses | q41: the speed panel |

## The channels (E5: current, stale, substitute, dark)

| channel | status | last | limit (days) | substitute |
|---|---|---|---|---|
| initial and continued claims, insured unemployment rate (DOL weekly) | current | 2026-10-31 | 13 |  |
| industrial production, the newest G.17 print (the production pillar) | current | 2026-10-16 | 45 |  |
| Moody's Baa yield, monthly average (the credit pillar) | current | 2026-10 | 45 |  |
| the effective federal funds rate, monthly average (the fed-shock door) | current | 2026-10 | 40 |  |
| the 10-year and 1-year Treasury yields, monthly averages (the job-lose | current | 2026-10 | 40 |  |
| the unemployed count and job losers, first prints (the count door, the | current | 2026-10 | 45 |  |
| unemployment rate and payrolls, the newest Employment Situation vintag | current | 2026-10-01 | 45 |  |
| job openings (BLS JOLTS; the help-wanted pillar) | current | 2026-09-01 | 80 |  |
| S&P 500 close | current | 2026-11-06 | 5 |  |

## Gaps

- none
