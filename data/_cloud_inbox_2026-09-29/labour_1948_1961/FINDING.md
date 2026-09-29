# Labour series as printed, 1948-1961: FINDING

Work dir: `collect/labour_1948_1961/` (scratchpad). All numbers come from code: the PDF text layer plus two
tesseract readings of each table, followed by accounting identities and cross-issue checks. No value was
typed or read by eye.

## Deliverables
- `out/vintages/<SERIES>_asprinted_vintages.csv`: wide, ALFRED layout (`date`, then one column per
  publication named `SERIES_YYYYMMDD`). Cells flagged as doubtful are left blank. When two sources fall in the
  same month, the EI print is used.
  `out/vintages/by_source/`: the same tables split by source (EI / EE / MLR), plus `<SERIES>_columns_source.csv`,
  which maps each column to its source and issue.
- `out/asprinted_long.csv`: tidy table of every parsed print: series, basis, ref_month, value, source,
  issue, pub_date, CPS basis, unit/precision, derived flag, the three OCR readings, checks and doubt reason.
  `is_current=False` marks superseded-basis duplicates, such as the 68-area rows printed beside the 230-area rows.
- `out/first_prints.csv`: the first non-doubtful print for each series and month.
- `out/doubtful_cells.csv`: the withheld cells, with their reasons. `out/alfred_validation*.csv`: comparison with ALFRED.
- `MANIFEST.csv`; `scripts/` (fetch, extract, map, assemble, finalize); `raw/` (see "Raw" below).

Series. Labour-force series are for ages 14 and over, as printed; levels are in thousands.
UNRATE (SA %), UNRATENSA, CLF14NSA/SA, UNEMPLOY14NSA/SA, CE14NSA/SA, MANEMP (SA), MANEMPNSA, NDMANEMP (SA),
NDMANEMPNSA, DMANEMP/NSA, PAYEMS (SA), PAYEMS_XAKHI, PAYNSA, AWHMAN (SA), AWHMANNSA, AWHDURNSA, AWHNONDURNSA.

## Publication date convention
Economic Indicators (EI), Employment and Earnings (E&E) and the Monthly Labor Review (MLR) print no release
day. `pub_date` is therefore the last day of the issue month. For EI, the Census/BLS press release came earlier
in that month; in 1960-61 ALFRED dates these releases to the 5th-15th. Using month-end is conservative:
nothing is dated before it was printed. When validating, I compared each issue with the last ALFRED vintage
dated in or before the issue month. If that vintage was dated inside the same month, the one before it was
also allowed, because the day the issue went to press is unknown.

## When each series was first printed, and on what basis (from the prints)
- Unemployment rate, NSA: EI printed "% of civilian labor force" from the Feb 1950 issue. From May 1948 to
  Jan 1950 only the levels were printed, so UR = 100*UNEMP/CLF is derived (flagged `derived`). Where civilian
  labor force itself was not printed (1948-49), CLF = TLF - armed forces.
- **Unemployment rate, SA: first printed in EI July 1957** (column "Seas. adj.", with values back to May 1956).
- CPS basis: EI 1954 issues print the Jan-Feb 1954 months on both the 68-area and the 230-area sample (both kept,
  the 230-area one is current). The "New definitions" rows begin with Jan 1957. Data include Alaska and Hawaii
  from Jan 1960. EI 1961 issues print labour-force levels in millions (flagged; converted to thousands).
- Payroll employment (EI table eras, from the printed headers): 1948-05..11 total and manufacturing; 1948-12..1949-09
  durable and nondurable only (manufacturing = sum, derived); 1949-10..1954-11 manufacturing, durable and nondurable,
  but no nonfarm total except in 1954-08..11 (otherwise the total is derived as the sum of the printed divisions);
  **SA nonfarm total from EI Dec 1954** ("Total adjusted for seasonal variation"; EI credits the Department of
  Labor and the Federal Reserve Board, and its values differ from E&E's BLS seasonally adjusted total);
  **SA manufacturing, durable and nondurable in EI from July 1957** (NSA manufacturing is not printed in EI after
  June 1957); 1960-02..1961-10 totals are printed both including and excluding Alaska and Hawaii.
- E&E printed SA employment by industry division (TOTAL, manufacturing) from Sep 1954.
- The Oct 1949 EI carries a benchmark revision of manufacturing (Jun-1949 NSA 15,061 -> 13,885). The revised level
  matches ALFRED's 1961 vintage basis.
- Hours, SA: **E&E introduced SA average weekly hours in July 1960** (table C-5: "being introduced with this
  issue"); **EI from Nov 1960**. Before that, only NSA hours were printed.

## Validation against ALFRED (overlap 1960-03 .. 1962-03)
Non-doubtful prints matched exactly:
UNRATE 334/334, MANEMP 70/70, NDMANEMP 70/70, DMANEMP 70/70, AWHMAN 70/70, PAYEMS 43/43, CLF16OV 167/167
(to 0.1 million), CE16OV 166/166. Including the withheld cells, the rates are UNRATE 334/339, PAYEMS 69/70 and
CLF 167/168; every mismatch had been flagged doubtful before the comparison was run.
Before 1960 there is no ALFRED vintage to compare with, so those prints are checked only by the identities and
by cross-issue agreement (most cells equal the print of the same month in an adjacent issue).

## OCR method, and what "doubtful" means
Each table cell gets three readings: the FRASER text layer, tesseract at 300 dpi with ruling lines removed, and
tesseract at 400 dpi. These are majority-voted and then checked against the printed identities: CLF = E + U,
E = agriculture + nonagriculture, manufacturing = durable + nondurable, nonfarm total = sum of divisions, and the
NSA rate = U/CLF. Then come the cross-issue votes and consistency checks: the same month's print in adjacent
issues, the median of all prints, spikes within one issue, and NSA versus SA totals. For the SA unemployment
rate there is an extra check: NSA/SA must be close to that calendar month's seasonal factor. This matters because
the SA column is set in italics, and OCR reads an italic 3 as 8 and an italic 5 as 6. Every correction is
flagged in the long file. Cells that cannot be confirmed are withheld from the wide tables. Withheld shares:
UNRATE 2.3%, MANEMP 0.5%, MANEMPNSA 1.1%, NDMANEMP 0.5%, NDMANEMPNSA 5.9%, AWHMANNSA 1.8%, AWHMAN 1.2%,
UNRATENSA 0.7%, CLF14NSA 0.4%, PAYEMS 14.8%, PAYNSA 15.9% (the leading 5 in the 1956-60 nonfarm-total columns is
often read as 6).

## Routes tried
- FRASER EI: `files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf` works. The exceptions use `EI_<MM><YYYY>.pdf`
  (1948-05, 1948-06, 1952-02, 1952-07, 1962-02). FRASER returns 403 for a file that does not exist. EI begins
  May 1948. The Feb 1962 issue has no text layer, so it was OCR'd with tesseract.
- FRASER E&E (title 60): `employment/emp_<YYYYMM>.pdf` to 1960-06, then `employment/1960s/empl_<MMYYYY>.pdf`.
  Downloaded for 1954-05..1962-02.
- FRASER MLR: `bls_mlr/bls_mlr_<YYYYMM>.pdf` (about 50 MB each). Downloaded for 1947-12..1949-03. Only the sections
  holding Current Labor Statistics A and C were kept, for Feb-May 1948; the full issues were deleted.
- Census P-57 and P-50: not on census.gov (`/library/publications/time-series/p57.html` returns 404;
  www2.census.gov/library/publications/19xx/demographics/ lists only P-25, P-60 and P-23). The UNT Monthly
  Catalog (mocat.library.unt.edu) returned 403. HathiTrust and web.archive.org were not attempted (blocked by policy).

## What remains (gaps)
1. **Jan-Apr 1948 first prints.** EI starts May 1948. The earlier prints are in the MLR. Only the April 1948
   issue's A-1 (labour force, rows kept where CLF = E + U holds) and the Apr-Jun 1948 issues' A-2 (nonfarm total
   and manufacturing) were parsed, from a single text-layer reading. MLR Feb/Mar 1948 A-1 and the MLR C-1 hours
   table were not parsed; their pages are in raw/mlr_pages.
2. **E&E SA employment, Sep 1954 .. Jun 1957.** Only cells whose table passed TOTAL = sum of divisions were kept:
   47 MANEMP and 45 PAYEMS cells from about 12 issues. The mid-1956..1959 month-row layout was mostly not captured.
3. **E&E SA hours, Jul-Oct 1960.** Not captured, because the identity failed; EI SA hours start Nov 1960.
4. NSA manufacturing after Jun 1957, NSA hours after Oct 1960, and thousands-level labour force for 1959-62 are
   all printed in E&E but were not parsed. E&E PDFs are in raw/ee.
5. Release days are unknown (month-end convention above). Candidate sources for them: the Census P-57 cover
   dates, which could not be found online, and newspaper archives, which were not tried.
6. PAYEMS/PAYNSA have a high withheld share for 1956-60 (see above). NDMANEMP SA from ALFRED's own 1961 vintage
   differs by ~450k from the 1959-60 prints, because of the 1961 benchmark/SIC revision; this is real revision,
   not error.

## Raw
- raw/ei: symlinks to the identical EI PDFs in collect/claims_pre1975/pdf/ei, plus fetch_log.csv with the URLs.
- raw/ei_fulltext: pdftotext layout text of every issue. raw/ei_pages: the text layer of each table page used.
- raw/ee: E&E PDFs (284 MB), with ee_fulltext, and ee_pages holding the pages used.
- raw/mlr_pages: MLR sections for Feb-May 1948, plus text for 1947-12..1949-03.
- out/ei_cells: every table cell with its three raw OCR strings, one file per issue.

MANIFEST note: pct_repeated_values = % of reference months whose first print equals the previous month's first print; n_obs = non-empty cells in the wide table.
