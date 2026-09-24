#!/usr/bin/env python3
"""Pending patch for the standing collector (collection 191), prepared 17 Sep 2026 in the cloud while the Mac slept.

Every address here was tested from the cloud the same afternoon except the BLS flat files, which answer 403 to a bare
browser string (the collector's declared one passes on the BLS feeds) and are therefore registered DISABLED until
they are tested natively. Idempotent: running it twice changes nothing the second time.

Run on the Mac from 191/code:   python3 pending_patch_2026-09-17.py
Then:                           python3 -m py_compile collector.py
                                launchctl kickstart -k gui/$(id -u)/com.bristowhall.collector
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
README = os.path.join(os.path.dirname(HERE), 'README.md')
STAMP = time.strftime('%Y-%m-%d_%H%M')

CSV = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
IMF = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,%s/...%s"
DDP = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=%s&filetype=zip"
RTD = "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/real-time-data/data-files/xlsx/%s.xlsx"
BLS = "https://download.bls.gov/pub/time.series/%s"

NEW_JOBS = [
    ("oecd_revisions", {
        "name": "imf_sdmx", "dir": "imf_sdmx", "keep_vintages": True, "fresh_hours": 160,
        "_note": "Added 17 Sep 2026. The IMF's SDMX service (api.imf.org), keyless. Labor Statistics (employment, unemployed persons, unemployment rate, labour force, wage rates; 194 countries) and Production Indexes (118 countries), monthly from 1950 and quarterly, whole datasets in one request each (195 MB and 395 MB raw, 3 MB and 7 MB compressed: every row carries the dataset's description). A dated copy at each change builds the vintages the IMF does not serve: its own vintage dataflows (LS_2026_MAY_VINTAGE and the like) exist but return no observations without a login.",
        "files": [
            {"url": IMF % ("LS", "M"), "out": "imf_labor_statistics_monthly.csv.gz", "stream": True, "headers": CSV},
            {"url": IMF % ("LS", "Q"), "out": "imf_labor_statistics_quarterly.csv.gz", "stream": True, "headers": CSV},
            {"url": IMF % ("PI", "M"), "out": "imf_production_indexes_monthly.csv.gz", "stream": True, "headers": CSV},
            {"url": IMF % ("PI", "Q"), "out": "imf_production_indexes_quarterly.csv.gz", "stream": True, "headers": CSV}]}),
    ("surveys_comparators", {
        "name": "fed_ddp", "dir": "fed_data_download", "keep_vintages": True, "fresh_hours": 20, "vintage_max_mb": 60,
        "_note": "Added 17 Sep 2026. The Board's Data Download Program: each statistical release whole, as a zip, at a standing address. A dated copy at each change is a complete vintage of the release: G.17 production and capacity, H.8 bank assets and liabilities, G.19 consumer credit, H.15 rates, commercial paper, H.4.1, Z.1, G.20, charge-offs and delinquencies, household debt service, H.6, H.3, policy rates.",
        "files": [{"url": DDP % r, "out": "fed_%s.zip" % r.lower()} for r in
                  ("G17", "H8", "G19", "H15", "CP", "H41", "Z1", "G20", "CHGDEL", "FOR", "H6", "H3", "PRATES")]}),
    ("surveys_comparators", {
        "name": "bea_flat", "dir": "bea_flat", "keep_vintages": True, "fresh_hours": 40, "vintage_max_mb": 80,
        "_note": "Added 17 Sep 2026. Every NIPA table in one file (20 MB); a dated copy at each change is a complete vintage of the national accounts, personal income and outlays included.",
        "files": [{"url": "https://apps.bea.gov/national/Release/TXT/FlatFiles.zip", "out": "bea_nipa_flat_files.zip"}]}),
    ("surveys_comparators", {
        "name": "philadelphia_rtdsm", "dir": "philadelphia_rtdsm", "keep_vintages": True, "fresh_hours": 160,
        "_note": "Added 17 Sep 2026. The Philadelphia Fed's Real-Time Data Set for Macroeconomists, the five workbooks that answered: unemployment rate, payroll employment, hours, housing starts, labour force (monthly vintages from 1965). Collection 21 holds a copy taken earlier; this keeps it current.",
        "files": [{"url": RTD % n, "out": n + ".xlsx"} for n in ("rucQvMd", "employMvMd", "hMvMd", "hstartsMvMd", "lfcMvMd")]}),
    ("surveys_comparators", {
        "name": "bls_flat_files", "dir": "bls_flat_files", "enabled": False, "keep_vintages": True, "fresh_hours": 160, "vintage_max_mb": 150,
        "_note": "Prepared 17 Sep 2026, DISABLED until tested natively. The Bureau of Labor Statistics' whole databases as flat files: JOLTS, the household survey, the payroll survey, state and metropolitan payrolls, state unemployment. With a dated copy at each change this is a complete monthly vintage of everything the Bureau publishes, far beyond the 2,603 series on the ALFRED list. The host answers 403 to a bare browser string; the collector's declared one passes on the Bureau's feeds. Test one file by hand, then set enabled to true.",
        "files": [
            {"url": BLS % "jt/jt.data.1.AllItems", "out": "jolts_all.txt.gz", "stream": True},
            {"url": BLS % "ln/ln.data.1.AllData", "out": "cps_all.txt.gz", "stream": True},
            {"url": BLS % "ce/ce.data.0.AllCESSeries", "out": "ces_all.txt.gz", "stream": True},
            {"url": BLS % "sm/sm.data.1.AllData", "out": "state_metro_payrolls_all.txt.gz", "stream": True},
            {"url": BLS % "la/la.data.3.AllStatesS", "out": "laus_all_states_sa.txt.gz", "stream": True},
            {"url": BLS % "la/la.data.2.AllStatesU", "out": "laus_all_states_nsa.txt.gz", "stream": True}]}),
]

STATA_DO = r'''/*==============================================================================
    Project:    Bristow-Hall Rule - standing collector (collection 191)
    Author:     Anthony Hall (prepared by Claude, 17 Sep 2026)
    Purpose:    Read every derived series in the warehouse (two-column CSVs: date,value)
                into one labelled long panel for analysis in Stata.
    Input:      ../../warehouse/<source>/derived/*.csv
    Output:     ../../stata/warehouse_series_long.dta  (+ log)
    Note:       Reads only. Nothing in the warehouse is changed.
==============================================================================*/

clear all
set more off
cap log close

* --- paths: run from 191/code/stata, or set the global by hand ---
global root "`c(pwd)'/../.."
global wh   "${root}/warehouse"
global out  "${root}/stata"
cap mkdir "${out}"
log using "${out}/load_warehouse_`c(current_date)'.log", replace text

tempfile panel
save `panel', emptyok

local sources : dir "${wh}" dirs "*"
foreach s of local sources {
    local files : dir "${wh}/`s'/derived" files "*.csv"
    foreach f of local files {
        cap import delimited using "${wh}/`s'/derived/`f'", varnames(1) stringcols(1) clear
        if _rc continue
        cap confirm variable date value
        if _rc continue
        * value may arrive as string when a file carries a stray symbol
        cap confirm numeric variable value
        if _rc destring value, replace force
        gen str80 series = subinstr("`f'", ".csv", "", 1)
        gen str40 source = "`s'"
        * dates are ISO (YYYY-MM-DD); a month or a year alone is set to its first day
        gen str10 d = date
        replace d = d + "-01" if length(d) == 7
        replace d = d + "-01-01" if length(d) == 4
        gen long ddate = date(d, "YMD")
        format ddate %td
        drop if missing(ddate) | missing(value)
        keep source series ddate value
        append using `panel'
        save `panel', replace
    }
}

use `panel', clear
rename ddate date

* --- integrity: one value per series and day ---
duplicates report source series date
duplicates drop source series date, force
isid source series date
assert !missing(value)

label variable source "Warehouse folder the series came from"
label variable series "Series name (file name without .csv)"
label variable date   "Observation date (first day of the period for monthly and annual data)"
label variable value  "Value as published by the source"

sort source series date
compress
save "${out}/warehouse_series_long.dta", replace

* --- codebook: one line per series ---
preserve
    collapse (count) n_obs = value (min) first = date (max) last = date, by(source series)
    format first last %td
    export delimited using "${out}/warehouse_series_codebook.csv", replace
restore

codebook, compact
log close
'''

README_ADD = '''

## 17 September 2026, sixth pass - prepared in the cloud while the Mac slept, applied by `code/pending_patch_2026-09-17.py`

Anthony asked that his data skills be put to work on the collector. What each gave:

- **API data fetcher (FRED, World Bank, IMF, BLS, OECD).** FRED, ALFRED, the OECD and the World Bank monitor were already in. New from it: `imf_sdmx` (the IMF's keyless SDMX service: Labor Statistics for 194 countries and Production Indexes for 118, monthly from 1950 and quarterly, whole datasets, a dated copy at each change; the IMF's own vintage dataflows exist but return no observations without a login); `fed_ddp` (thirteen Board releases whole, as zips, a complete vintage of each release at every change); `bea_flat` (every NIPA table in one file, a complete vintage of the national accounts at every change); `philadelphia_rtdsm` (the five real-time workbooks that answered); and `bls_flat_files`, registered but disabled until one file is tested natively (the Bureau's whole databases, which with dated copies would be a complete monthly vintage of everything it publishes). The World Bank's indicator API is annual and adds nothing a monthly rule can read.
- **Stata data cleaning.** `code/stata/load_warehouse_series.do` reads every derived series in the warehouse into one labelled long panel (`stata/warehouse_series_long.dta`) with a log, integrity checks and a one-line-per-series codebook. It reads only.
- **Saving rule.** Unchanged and in force: everything lands in this folder on the Mac; nothing was gathered in the cloud, only addresses tested.
- **Not used, and why.** Ray Data is for datasets past a hundred gigabytes on a cluster; the warehouse is a few gigabytes of small files on an 8 GB laptop, where it would only add weight. The research-exploration skill governs deep-learning experiments against a frozen benchmark and has nothing to act on until such a model and benchmark exist.

Also added since the fifth pass: `sec_phrases` (weekly counts of 8-K filings containing each of fourteen phrases such as "workforce reduction", "going concern" and "covenant waiver", EDGAR full-text search, 2001 on, weeks ending Saturday; real time by construction); the log is compressed beside itself past 40 MB; a macOS notification is raised when a job fails six cycles in a row or the disk is low.
'''


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    todo = [(before, job) for before, job in NEW_JOBS if job['name'] not in names]
    if todo:
        shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_pending_patch_%s.json.bak' % STAMP))
        for before, job in todo:
            names = [x['name'] for x in j['jobs']]
            j['jobs'].insert(names.index(before) if before in names else len(names), job)
        json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', [job['name'] for _, job in todo], '| registry now', len(j['jobs']))

    sd = os.path.join(HERE, 'stata'); os.makedirs(sd, exist_ok=True)
    p = os.path.join(sd, 'load_warehouse_series.do')
    if not os.path.exists(p):
        open(p, 'w').write(STATA_DO); print('wrote', p)

    if os.path.exists(README) and 'sixth pass' not in open(README).read():
        open(README, 'a').write(README_ADD); print('README addendum appended')


if __name__ == '__main__':
    main()
