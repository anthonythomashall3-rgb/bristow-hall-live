# Building permits (and starts) as printed, 1960 to July 1999: FINDING

Status: DONE (2026-09-29, about 19:40Z).

Every number was produced by code from a saved raw file: the PDF text layer or tesseract OCR. No value was typed by hand or read off an image by a person.

## Deliverables (this directory)

**`permits_asprinted_1960_1999.csv`** holds 6,028 rows: 446 *Economic Indicators* issues from 1962-11 to 1999-12, printing the months 1961-09 to 1999-11.
- The first eight columns match `107_permits_first_prints_1990_2026-09-10/ei_permits_as_printed.csv`:
  - `issue, issue_ym, as_of, month, permits_authorized_saar_thous, starts_total_saar_thous, flag, source`
  - `as_of` is the last day of the issue month.
  - `flag` is the printed `p` or `r` mark where OCR caught it.
  - `source` is the exact PDF URL plus the PDF page number.
- Extra columns:
  - `newest_month_in_issue`, which dates the issue by the Census release; `is_newest_month`.
  - `permits_universe_places` and `universe_basis`: the permit-issuing-place universe as the page footnote states it. It is 10,000 / 12,000 / 13,000 / 14,000 / 16,000 / 17,000 / 19,000.
  - `universe_basis` says whether the value is on the page, OCR-corrected from adjacent issues, or not stated. 1976 to mid-1979 issues print no universe footnote.
  - `universe_footnote`: the raw footnote text.
  - `permits_read_status`, `permits_ocr_reads`, `starts_read_status`, `starts_ocr_reads`, `row_label_ocr`.
  - `census_current_permits` and `census_current_starts`: today's FRED PERMIT and HOUST values, for reference only.
- `starts_total_saar_thous` is total private starts, including farm, SAAR.

**`bcd/bcd_series29_asprinted.csv`** covers *Business Cycle Developments* series 29 in the 15 issues from 1961-10 to 1962-12.
- **Level**, October 1961 issue only (SAAR, thousands), 1959-01 to 1961-09:
  - 28 months are accepted.
  - 1960-05, 1960-07, 1960-11, 1961-07 and 1961-09 are blank (doubt or no read).
- **Index**, 1957-59=100, from November 1961 on: 439 of 528 cells accepted.
- The level/index ratio between the October 1961 and November 1961 issues is 10.892 on 15 months. It is used only to confirm single October 1961 reads, never to create values.

**Other files:**
- `MANIFEST.csv`
- `validation_summary.txt`
- `validation_alfred.csv`
- `validation_isolated_*.csv`
- `validation_far_from_census_*.csv`
- `parsed/`: the per-issue, per-engine reads (`reads_MM-YYYY.csv`), parse logs, `engine_drops.csv` and `dropped_rows.csv`.

**Scripts:**
- `fetch_ei.py`, `find_pages.py`, `save_front.py`
- `parse_ei.py`, `run_parse_all.sh`, `rerun_stale.sh`
- `build_final.py`, `validate.py`, `make_manifest.py`
- `bcd/fetch_bcd.py`, `bcd/extract_bcd_pages.py`, `bcd/parse_bcd.py`, `bcd/build_bcd.py`

**Raw files kept.** Full PDFs were deleted after extraction because the disk is shared; sha256 hashes are in `raw/full_pdf_checksums.csv` and `bcd/pages/page_index.csv`.
- `raw/pages/MM-YYYY_pNN.pdf`: the original scanned housing-table page.
- `raw/pages/MM-YYYY_pNN.txt`: pdftotext of that page.
- `raw/pages/MM-YYYY_front.txt`: text of pages 1 to 3.
- `raw/cells/<issue>/`: the cell crops used by OCR engine C.
- `bcd/pages/`: the same, for BCD.

## Sources and HTTP results

**1. FRASER *Economic Indicators*** (`https://fraser.stlouisfed.org/files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf`, default urllib user agent).
- All 480 issues from 1960-01 to 1999-12 returned HTTP 200 (`fetch_log.csv`).
- Seven issues return S3 403 (application/xml) under the plain name and are stored as `EI_<MM><YYYY>.pdf`: 1962-02, 1968-06, 1972-01, 1975-06, 1975-07, 1976-04 and 1978-07. These were found from the FRASER item pages, e.g. `/title/economic-indicators-1/june-1968-584`.
- The decade listing omits August 1968, but `08-1968.pdf` exists (HTTP 200).

**Permits first appear in EI in the November 1962 issue** (table "New housing starts and applications for financing", column "New private housing units authorized", SAAR), printing 1961-09 to 1962-10.
- The 34 issues from 1960-01 to 1962-10 have no permits column. Their text layers were checked; see `raw/pages/page_check.csv`.
- So SAAR permit levels for 1960-01 to 1961-08 were never printed in EI.

**2. govinfo.gov *Economic Indicators***: not needed, because FRASER is complete for 1995 to 1999.

**3. FRASER *Survey of Current Business*** (title 46, `SCB/1960-69/SCB_MMYYYY.pdf`):
- July 1960 prints only NSA "residential construction authorized", the old BLS all-places series.
- October 1962 prints no permits.
- No SAAR level is printed. HTTP 200.

**4. FRASER *Business Cycle Developments*** (title 43, `BusCycD/60-69/BCD_MMYYYY.pdf`): all 15 issues from 1961-10 to 1962-12 returned HTTP 200.
- Series 29 in Table 1 (Basic data, January 1959 to present) is the only seasonally adjusted permits measure printed before November 1962.
- It is a level in October 1961 and an index from November 1961.

**5. *Construction Review* (BDSA) and Census *C40***: not on FRASER.
- FRASER OAI-PMH was checked: `oai?verb=ListSets`, then `ListRecords&set=author:30` (Census) and `author:8` (Commerce), with titles grepped.
- FRASER site search URLs return 404.
- web.archive.org, HathiTrust and files.nber.org are blocked by egress policy and were not tried.

## Method (deterministic)

Each housing page was read three ways:
- **A:** the ABBYY text layer FRASER embedded (pymupdf word boxes).
- **T:** tesseract 5 (psm 6) on a 350-dpi render of the table rows.
- **C:** tesseract (psm 7, digits only) on each permits and starts cell, located from the A geometry (or T when A fails), under three preprocessing variants with a majority vote.

Rows are months:
- The block is found from the "Seasonally adjusted annual rates" banner, or a fallback year-row anchor.
- Months come from year and month labels, or the issue date when the year label is unreadable.
- Columns come from right-edge clustering.
- Starts is the leftmost SAAR column. Permits is the column under the "author-/ized" header that tracks today's Census PERMIT and not completions or one-unit starts.

Rules for accepting a value:
- A value read by at least 2 engines is accepted (`3of3` or `2of3`).
- Reads more than 35% (log) from today's Census value are excluded from the vote as OCR failures (for example, a lost leading "1,"). They stay listed in `*_ocr_reads`.
- A split cell is accepted only if an engine's read equals the same month in the adjacent issue (`split->prev_issue`, or `split->next_issue` for newest months).
- A value that differs from both adjacent issues, while those two agree, is replaced by the adjacent value if some engine read it (`isolated->adjacent`). Otherwise it is kept and flagged `isolated_deviation`.
- Anything else is left blank (`ocr_doubt` or `missing`).

## Validation

**External, starts.** ALFRED HOUST vintages start 1960-07-21 (local copy in collection 27). For each issue, the vintage with the same newest month was compared cell by cell: 6,002 cells in 445 issues, **99.8% exact**. This confirms the row and month registration, and the OCR of the row that also carries permits.

**External, permits.** ALFRED PERMIT (from 1999-08-17) against the August to December 1999 issues: 66 cells, **100% exact**.

**Collection 107.** Its hand-built EI rows (October 1969 and May to October 1990) against this file: 93 overlapping cells, **0 differences** in permits or starts.

**Cross-issue.** A median month is printed 13 times with 3 distinct permit values, consistent with first print, revision and annual seasonal revisions. There are 2 permit isolated deviations left: 1964-08/1964-06 (1316) and 1979-02/1978-11 (1727), both read identically by all three engines and kept with a flag.

**Against today's Census PERMIT.** The median absolute log ratio is 0.027 in the 1960s, 0.028 in the 1970s, 0.013 in the 1980s and 0.010 in the 1990s. No cell is more than 0.2 away.

**Read status, permits (6,028 rows):**

| Status | Cells |
|---|---|
| 3of3 | 4,709 |
| 2of3 | 1,249 |
| split->prev_issue | 22 |
| split->next_issue | 38 |
| isolated->adjacent | 4 |
| isolated_deviation (kept) | 2 |
| ocr_doubt (blank) | 3 |
| missing (blank; the figure is printed but unreadable) | 1 |

The blank cells are:
- 1963-05/1962-06
- 1980-05/1980-03
- 1994-05/1993-03
- 1970-06/1970-05, the first print of May 1970, which is unreadable in the scan.

## Gaps and caveats

**Months 1960-01 to 1961-08.** No as-printed SAAR permit level exists in EI or SCB. The only one is the single October 1961 BCD vintage, 28 months; it is not a monthly real-time series. BCD from November 1961 prints an index, not a level.

**Newest month never printed as a first print in EI**, because the newest row printed only FHA/VA figures or data were delayed:
- 1962-12, 1963-08, 1963-12, 1964-03 and 1968-05. These months first appear one issue later.
- 1995-11 and 1995-12: the government shutdown. The January 1996 issue is dated January but prints data through January 1996.

**Up to 19 issues lost their oldest row in OCR.** That month is present in the earlier issues. They are listed in `validation_summary.txt`.

**`flag` (p/r)** is only as good as OCR of the small superscripts; it is blank where unreadable.

**Universe** is taken from each page's footnote. 1976 to 1979 issues state none, so `universe_basis` says "not stated".

**Mac commit** (`save-all-recession-data` rule): no device-bridge tool was available in this session. The collection sits only in this work directory until the coordinator packages it.
