# Handoff gaps: real-time UI first prints (rate / level / claims), cloud hunt 2026-09-29

Status: FINISHED (cloud session). Every value below was produced by code (regex on a saved raw page / PDF text layer).
Nothing was typed from a search summary. Raw pages are in `raw/` (large HTML stored gzipped), every fetch is in `MANIFEST.csv`.

## 1. Gap list (what was hunted)
`scripts/01_gaps.py` ran on the two read-only cloud tables (s2/first_prints_early_1975_2002.csv and
cache/national_first_prints_1985_live.csv; weeks 1975-07 to 2003-12) -> `gaps_all.csv`, then `scripts/12_...py` -> `gaps_targeted.csv`
(priority, expected first-print release, status, value found).

| priority | rate | level | claims |
|---|---|---|---|
| P1 claims 1976-05-22, 1977-07-02, 1977-07-30 | | | 3 |
| P1 Dec-1995 shutdown (iu weeks 12-09..12-30) | 4 | 4 | |
| P2 1984-88 | 95 | 103 | |
| P3 1975-76, 1993, 1994, 2003 rates | 30 | | |
| P4 other cloud-only gaps (probably already filled on the Mac) | 211 | 169 | 8 |
| P5 level held only as a later restatement | | 92 | |

The cloud copy is older than the Mac table, so the Mac's list (22 rate weeks, ~76 levels, 3 claims) is a subset.
"Level gap" = no level, a level marked "iusa from the current series", or a round 100,000 (rounded millions).

## 2. Found (found_prints.csv)
| series | week ended | value | kind | source (pub date) | check |
|---|---|---|---|---|---|
| rate | 2003-05-17 | **3.0** | advance | DOL ETA news release oui.doleta.gov/press/2003/052903.html (2003-05-29) | text prints "3,0 percent" (typo), table prints 3.0%. That typo is why the cloud row 052903 has no rate. Neighbours 2.9 / 2.9; FRED now 2.9 |
| rate | 2003-05-17 | 2.9 | revised (next release) | oui.doleta.gov/press/2003/060503.html (2003-06-05) | "prior week's revised rate of 2.9 percent" |
| rate | 1992-12-05 | **2.7** | advance | UPI Archives 1992-12-24 "Jobless insurance claims rise" | level in the same story, 2,862,000, equals the cloud's first-print level exactly; FRED now 2.8 |
| rate | 1992-12-12 | **2.7** | advance | UPI Archives 1992-12-31 "Jobless insurance claims drop by 28,000" | level 2,776,000 in the same story equals the cloud level; FRED now 2.7 |
| rate | 1992-11-28 | 2.8 | prior-week figure quoted in the next release (revised or unrevised not stated) | UPI 1992-12-24 ("decreased to 2.7 percent from 2.8 percent") | FRED now 2.8. This is a holding, not the first print |

Year proof: DOL archive listing year=2003 plus the file name 052903 and the release text "May 29, 2003". UPI: the
article-date line ("Dec. 24, 1992") and the URL path /Archives/1992/12/24/. Weeks are named in the same sentence
("for the week ending Dec. 5"). All are the Department's figures ("the Labor Department said Thursday").

**No P1 week, and no P2 (1984-88) level or rate, was found.** The only Mac-list week filled is the 2003 rate.
The 1992 rates are cloud-only gaps.

## 3. Validation
- The news parser (`scripts/parse_news.py`, `09_run_parse.py`) was also run on non-gap weeks. For the latest week of
  each story it equals the cloud first print exactly in 25 of 31 cases (`validation.csv`). Five of the six misses are
  claims whose week the parser assigns wrongly when the only week named in the sentence belongs to the prior-week figure
  ("...377,000, up from 363,000 during the week ended Nov. 25"). No claims value was recorded from news, so none
  of these misses reached found_prints.
- **Conflict (not a gap week): insured unemployment, week ended 1983-12-10.** Two separate UPI stories of 1983-12-29
  print **2,785,000**, "a decrease of 17,000 from the previous week's revised level". The cloud row (AP 1983-12-29, Nexis)
  has **2,758,000**. One source transposed digits. The AP figure implies the week of Dec 3 was revised from 2,773,000
  (first print) to 2,775,000. The UPI figure implies a revision to 2,802,000 (+29,000). The AP value is the more plausible;
  the Mac should re-read its AP source before deciding. FRED now shows 2,666,000.
- Found values against the current series: 2003-05-17 is 3.0 against 2.9 now; 1992-12-05 is 2.7 against 2.8 now; 1992-12-12
  is 2.7 against 2.7 now. All are within 0.1 point, and none is an outlier.

## 4. Routes tried, with results
Before every fetch I checked robots.txt for the `Claude-User` agent (the user-directed fetcher), and every fetch waited at least 1.5 s per host
(10.5 s on FRASER, whose robots.txt sets a crawl-delay of 10).

**Not used, because the publisher opts out of `Claude-User` in robots.txt:** NYT, AP (apnews.com), Chicago Tribune,
Orlando Sentinel, Sun Sentinel, Baltimore Sun (Tribune Publishing robots.txt lists Claude-User under Disallow: /).
The robots files are kept in raw/probe_robots_*.txt. The Mac's AP and NYT routes via Nexis are unaffected.

| route | result |
|---|---|
| **DOL ETA press archive** (oui.doleta.gov/unemploy/archive.asp, report=press) | Works for Nov 2002 on and gave the 2003-05-17 rate. Years 1988-2001 return "There is no data available". Correct path is /press/YYYY/MMDDYY.html, not /unemploy/press/. |
| **UPI Archives, article pages** | Article pages can be fetched and their text extracted cleanly. But /search and /archive/search are robots-disallowed, there is no date index, and archive sitemaps cover only recent news. |
| **UPI year text index** (/Archives/1980-1989/text/YYYY/pN/) | Reverse-chronological. Page 101 and beyond silently return page 1, so only the last ~1,500 items of each year are reachable. Scanned 1981, 1982, 1983, 1984, 1987, 1990, 1992 and 2001: this found the two 1992 rates, the 1983-12-10 conflict, and 1982/2001 stories on non-gap weeks. The 1990-12-28 claims story has an empty body on UPI. The 1984-12-27 and 1987-12-24 stories lie beyond the cap. |
| **WebSearch for UPI URLs** (about 20 phrasings) | The index holds very few 1980s UPI archive pages: 1982-04-16, 1982-12-09, 1993-07-08 and 1994-01-20 were found, none on a target week. |
| **LA Times** (monthly sitemaps list all la-xpm URLs, with no slugs) | Scanned the business section (fi) for 1985-03-29 and 1996-01-19 (78 pages): no national claims story. Scanning further would be bulk crawling (robots.txt blocks ClaudeBot), so I stopped. WebSearch refuses latimes.com. |
| **Deseret News** (Claude-User explicitly allowed; article sitemaps 1988 on) | Fetched 54 slug-selected weekly-claims stories (1991-2003). None falls on a gap week. 1988 coverage starts in April and has no weekly claims stories; 1996-01-18/19 has none. Useful only for validation. |
| **Google Books API** | HTTP 429, quota limit 0 for the anonymous project (checked twice). books.google.com/books/feeds answers, but /books/ is robots-disallowed for all agents, so I did not use it. |
| **FRASER** | Commercial & Financial Chronicle 1976 (69 MB PDF): no UI data. Economic Indicators 1985: the UI table is monthly only. The Schultze papers hold only Meltzer-cited items. No ETA weekly claims release series. |
| **FOMC Greenbooks** (federalreserve.gov) | 1977-07-13, 1977-07-15 supplement, 1977-08-10 and 1996-01-26: insured-unemployment rate monthly only, weekly claims in charts, and levels rounded in text ("2.77 million"). No first prints. |
| **Ford Library** (EPB and Cannon files digitized) | Sampled folders have no weekly claims. The Seidman "EPB Weekly Economic Report" and "CEA Economic Indicators" folders are not digitized. |
| **ALFRED** | ICSA vintages start 2009-05-28, so nothing for the gaps. |
| **archive.org** | Full-text search returned HTTP 502 twice. Metadata search finds no DLR, Barron's issues (indexes only), WSJ index (lending-restricted), or NYT index for the years needed. Open Library /search/inside is robots-disallowed and returned an error. |
| **Common Crawl index** | Connection closed by the egress proxy, so blocked. I did not route around it. |
| **Washington Post archive** | Akamai returned no response over both HTTP/2 and HTTP/1.1. |
| **dol.gov newsroom** | Akamai returned "Access Denied" for query URLs. |
| **Bond Buyer** | The online archive starts in the 2000s. |
| **State newspaper sites** | nyshistoricnewspapers, Texas Portal, Indiana, Virginia and IDNC are behind Cloudflare or JS challenges (not solved). CDNC and Colorado disallow all agents. |

## 5. Still missing, and the best holding for each
- **Claims 1976-05-22, 1977-07-02, 1977-07-30:** still missing. Best holding is the cloud's prev-rev1 (the next release's
  restatement): 1977-07-02 = 385,000 and 1977-07-30 = 396,000 (the 1977-07-18 and 1977-08-15 releases). For 1976-05-22 only the
  current series (394,000) is held. The advance figure needs the DOL release or the DLR for those weeks, or a 1976-77 newspaper.
  Every 1976-77 newspaper route open to this session is closed (see above).
- **Dec-1995 shutdown rates and levels (iu weeks 12-09, 12-16, 12-23, 12-30):** still missing. The first print is the 1996-01-18
  catch-up release. The AP story of that day (Mac: Nexis 3SJ4-P9W0-0006-H2RC) gives claims only. The Greenbook of 1996-01-26
  confirms only "2.77 million for the week ending January 13". Best holding is the current series.
- **1984-88 levels and rates (P2, 198 weeks in the cloud list):** none found. Exact levels need the weekly releases or UPI
  stories, and UPI cannot be enumerated beyond late December. Best holding is the current series (levels) or nothing (rates).
- **1993 and 1994 single rate weeks:** not found. For 1994-07-23 the release is 1994-08-04. The Deseret AP story of
  1994-07-29 covers week 07-16 only.
- **1975-76 rates:** not found (no newspaper route for 1975-76 is open here).

## 6. Suggestions for the Mac (routes this session could not use)
1. For 1984-88 levels and rates, and the Dec 1995 rates, use UPI via Nexis. The UPI stories quote exact levels and the rate
   ("The seasonally adjusted insured unemployment rate ... for the week ending Dec. 5. There were 2,862,000 people ...").
   The Mac already cites UPI Nexis ids (for example 3S8G-HFT0-0008-Y2HY).
2. Retry the Google Books API from the Mac's own quota for the DLR SEASONALLY ADJUSTED DATA tables, on the release
   dates listed in gaps_targeted.csv (column expected_first_print_release).
3. Recheck the 1983-12-10 level: AP 2,758,000 against UPI 2,785,000.

## Files
- gaps_all.csv: raw gap list from the cloud tables.
- gaps_targeted.csv: weeks hunted, with priority, expected release, status, value found and other holdings.
- found_prints.csv: 5 rows (4 weeks: 3 advance first prints, 1 revised, 1 prior-week holding).
- candidates_all.csv: every figure the parser extracted from every downloaded story.
- validation.csv: those figures compared with the cloud table and current FRED.
- deseret_* and upi_index_hits.tsv: candidate URL lists. latimes_candidates.txt: empty (LA Times URLs carry no slugs).
- scripts/: 01_gaps, fetch (polite fetcher and manifest), 02-06 and 08 (sitemap and index scans), 07_dol_2003, 09_run_parse
  with parse_news, upitext and latext, 10_record_vetted, 11_fetch_upi_list, 12_targets_and_validation, record.
- MANIFEST.csv: every request (raw file, URL, UTC time, HTTP status, bytes, sha256).
