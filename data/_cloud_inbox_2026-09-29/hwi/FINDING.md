# HWI as printed: what was collected, how, and what is still missing

Target: The Conference Board help-wanted advertising index (newspaper HWI, BCD series 46; series 60 = ratio to
unemployed), as printed at the time, with publication dates, 1961 to 2004.

Rule followed: every value comes from code that parses a saved raw file. The raw files are PDF text layers
(OCR done by FRASER or BEA ABBYY, read with pdfplumber and pdftotext) and news HTML. No number was typed by
hand or taken from a search-engine summary. No page was re-OCR'd with tesseract, so cells the OCR got wrong
are flagged, not corrected.

## Deliverables

- `hwi_asprinted_long.csv`: 16,706 rows (12,336 for series 46) from 454 publications. Columns:
  - publication, issue, publication_date, date_basis, month, value, base, sa_flag, series
  - table: basic_data / C-page / S-page / historical / US column / news_*
  - mark: r/p/e as printed
  - ocr_doubtful, raw_token, source_url, page, note
- `hwi_asprinted_wide_vintages.csv`: series 46, one column per publication date (`HWI_YYYYMMDD`, with a
  suffix when two sources share a date), 660 months × 453 vintages. `hwi_asprinted_wide_columns.csv` gives
  each column's source, base, date basis, first and last month, and URL. **Bases differ by column** (see
  below). Do not splice columns without rescaling.
- `hwi_release_calendar_1996_2005.csv`: Conference Board release dates for reference months 1995-11 to
  2005-06. The rule is the last Thursday of the following month, or the Wednesday before when that Thursday is
  Thanksgiving; the HWOL technical note gives the same rule for the successor series. The rule matched all 7
  release dates stated in news text: 1998-06-25, 1999-08-26, 2000-03-30, 2001-12-27, 2003-01-30,
  2004-05-27 and 2004-10-28.
- `MANIFEST.csv`: one row per source × table × series. Gives the first and last observation, n_obs,
  pct_repeated_values, pct_ocr_doubtful, bases and date bases.
- `work/`: intermediate cell files, `first_prints.csv`, `validation_summary.txt`, `bcd_release_dates.csv`
  and `bcd_dropped_wrong_column.csv`.
- `raw/`: saved sources.
  - fraser: metadata, FRASER OCR text (gz), per-issue layout text (gz), and word boxes plus PNGs for
    candidate pages. The full PDFs were deleted for disk. Copies for 1961-1976 are in
    ../claims_pre1975/pdf/bcd.
  - bea: SCB help-wanted pages as single-page PDFs plus text.
  - neei: FRB Boston reports.
  - news: HTML and sitemaps.
- `scripts/`:
  - fetch: `fetch_fraser_bcd.py`, `fetch_bea_scb.py`, `fetch_parse_neei.py`, `fetch_parse_news.py`, `fetch_spokesman.py`
  - extract and parse: `extract_bcd_pages.py`, `parse_bcd.py`, `parse_coltable.py`, `parse_scb.py`, `parse_rowtable.py`
  - QA, dates and build: `qa_bcd.py`, `bcd_release_dates.py`, `release_calendar.py`, `build_outputs.py`, `validate.py`, `manifest.py`

## Sources used

| Source | Prints | Months printed | Publication date basis |
|---|---|---|---|
| Business Cycle Developments / Business Conditions Digest (FRASER title 43) | 325 of 342 issues, 1961-10 to 1990-03 | 1955 to 1990-02, about 2-3 years per issue | Each issue states the next one's date ("scheduled for release on ..."): stated for 249 of the 325 issues used. Estimated for the other 76 from the nearest year's median lag, which covers all of 1961-10 to 1963-07. |
| Survey of Current Business, BCI C-pages (BEA archive) | 64 issues, 1990-04 to 1995-11/12 | 14 months each | SCB states no date. Cover-month end is used as an estimate. |
| SCB S-pages | 43 issues, 1989-1993 | Secondary: OCR is poor | Same |
| SCB historical tables | Nov 1994 and Jan/Feb 1996 | 1948-01 to 1994-12 | Same |
| FRB Boston *New England Economic Indicators*, US column (Conference Board data) | 42 reports, 2002-01 to 2006-08 | 14 months each (1999-11 to 2006-06) | PDF CreationDate |
| News: UPI (5), Editor & Publisher (14), Spokesman-Review (1) | 20 articles with values, 1992-2005 | Current, prior and year-ago values | Release date from the wording "said Thursday" or "reported yesterday" (8 articles). Otherwise the article date. |

Bases: 1957=100 through the Jan 1964 BCD, 1957-59=100 from Feb 1964, and 1967=100 from the Mar 1971 BCD
through SCB 1995. The switch points come from step changes in the ratio of printed values to the Barnichon
series. The Conference Board's 1987=100 index is used from 1996; NEEI states this base, and the news
articles do not state one.

## Validation (work/validation_summary.txt)

- **First prints vs Barnichon (1987=100 reconstruction), within each base.**

  | Base | Ratio median (IQR) | Level corr | Monthly-change corr |
  |---|---|---|---|
  | 1957=100 | 2.61 (2.55-2.65) | 0.95 | 0.60 |
  | 1957-59=100 | 2.84 (2.76-2.90) | 0.99 | 0.70 |
  | 1967=100 | 1.52 (1.48-1.55) | 0.99 | 0.77 |

  Only 5 first-print months are more than 8% off the base median ratio:

  | Month | Printed | Explanation |
  |---|---|---|
  | 1968-07 | 185 | Printed in 6 issues, then revised to 204 in the Oct 1969 issue |
  | 1976-01 | 77 | Duplicate-column cell, flagged doubtful. Later prints say 87. |
  | 1994-01 | 106 | Preliminary |
  | 1955-02 | 55 | Long-table cell |
  | 1958-11 | 94 | Long-table cell |

  After 1995 Barnichon is a print-plus-online composite, so the 1987=100 ratio is not comparable.
- **Cross-source checks.**
  - SCB C-pages vs BCD over the 1989-1990 overlap: 11 of 13 months identical, max difference 1.
  - NEEI vs news, same months: 23 of 29 identical. The 6 differences are 1-2 points, where NEEI is a later
    vintage.
- **Revisions (first vs last print).** Across BCD 1967=100, 50% of months were revised, by 1.7 points on
  average. SCB: 56%, by 1.9 points. NEEI: 15%, by 0.3 points. SCB June 1995 prints Jun-Aug 1994 about 8
  points below the Jan/Feb 1996 historical table; the page image was checked, and this is a genuine revision,
  not OCR.
- **OCR flags.**
  - BCD: 16% of series-46 cells are ocr_doubtful. The flag covers digit substitutions, rows placed by
    geometry, duplicate-column cells resolved by level, and isolated disagreement with the neighboring
    issues (67 cells).
  - 2,307 cells from a neighboring column were dropped (work/bcd_dropped_wrong_column.csv). Barnichon was
    used only to decide which column a cell belongs to, never as a value.
  - BCD series 60 is only range-filtered (0.1-2.0) and is unvalidated.

## Remaining gaps

1. **1995-11 to 2001-10 has no systematic print.** The only first prints are from news:
   1997-04 (year-ago), 1998-03, 1998-04, 1998-05, 1998-07, 1999-07, 2000-01, 2000-02, 2000-11 (year-ago),
   2001-04, 2001-05 and 2001-07.
   - 1999-11 to 2001-10 values come from NEEI reports of 2002, which are later vintages, not first prints.
   - The Conference Board's own monthly releases and its *Business Cycle Indicators* report were not found
     online.
   - Tried with no result: UPI (discovery impossible), Spokesman (1 story), E&P (sporadic), and NEEI before
     2002 (not online).
   - Not fetched: apnews.com and latimes.com (they refuse Anthropic agents) and plansponsor.com (JavaScript
     challenge).
   - Next routes: E&P print archive (1905-2015), NEEI 1996-2001 in a library, and Business Week or WSJ
     "help-wanted index" briefs.
2. **SCB publication dates are estimates** (cover-month end).
3. **76 BCD release dates are estimates**, including all of 1961-10 to 1963-07.
4. **BCD 1961-1990 was not re-OCR'd.** Doubtful cells are flagged. The PNGs for 1977+ are in
   raw/fraser/cand, and the 1961-76 pages can be re-rendered from the shared PDFs.
5. **Pre-1961 prints** (NICB *Business Record*) were not found. FRASER has no NICB titles for this.
6. **Help Wanted OnLine (2005+)** was not collected. The E&P HWOL articles were skipped by the extractor,
   which excludes online-only sentences.

## Routes log

| Route | Result |
|---|---|
| FRASER title 43 (BCD), metadata.php JSON, pdfUrl/textUrl | 342 issues fetched, plain urllib UA |
| BEA SCB archive apps.bea.gov/scb/issues/YYYY/scb-YYYY-month.pdf | 1990-1996 fetched. BCI section ends with Nov/Dec 1995. No HWI in 1960, S-pages carry it by 1975. The Sep 1994 PDF holds the May 1994 C-2 page; it is flagged and dropped. |
| FRB Boston NEEI /-/media/Documents/neei/reports/<mon><yy>.pdf | 2002-01 to 2006-12 online, minus 2003-03 to 06 and 2003-09. Pre-2002 requests return an HTML not-found page. |
| Editor & Publisher sitemaps (robots-listed, 167k URLs) | 22 HWI stories 1999-2005 |
| UPI archive | 5 stories found through web search. Listing pagination is capped, the search is client-side, and ids are random. |
| Spokesman-Review monthly sitemaps 1995 to mid-2002 | 1 story |
| conference-board.org legacy press URLs | Empty 200 responses |
| Haver Economy-in-Brief archive | 404 |
| ALFRED/FRED HELPWANT (Economagic mirror "fedstl/helpwant") | Removed from FRED and ALFRED (404), so no vintages |
| CEA Economic Indicators (govinfo) | No HWI |
| FOMC Greenbook | Chart only |
| IndustryWeek archive | Import date only. Kept in work/news_cells.csv, excluded from the long file. |
| inman.com, apparelnews.net | 403 |
| Deseret Arc sitemaps | Only the last weeks of each year |
| web.archive.org, HathiTrust, files.nber.org | Not attempted (egress policy) |
