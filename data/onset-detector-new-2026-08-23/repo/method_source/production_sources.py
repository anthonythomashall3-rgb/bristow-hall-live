#!/usr/bin/env python3
"""Authoritative FRED series manifest for scheduled production refreshes.

Both refresh paths read this file.  Keeping the manifest in Python also lets the
operational tests compare it with the literal series consumed by every builder,
so a new model input cannot silently become a never-refreshed cache file.
"""

NATIONAL_SERIES = (
    "AAA", "ANFCI", "AWHMAN", "BAA", "BAA10Y",
    "BAMLH0A0HYM2", "CC4WSA", "CCSA", "CFNAI", "CFNAIMA3", "CMDEBT",
    "CMRMTSPL", "CPIAUCSL", "DAAA", "DBAA", "DFF", "DGS1",
    "DGS10", "DGS2", "DGS3MO", "DRTSCILM", "GACDFSA066MSFRBPHI", "GS1",
    "GS10", "HOUST", "HTRUCKSSAAR", "IC4WSA", "ICSA", "INDPRO",
    "IURSA", "JTSJOR", "JTSQUR", "M2SL", "MORTGAGE30US", "MSACSR", "NASDAQCOM", "NFCI",
    "PAYEMS", "PERMIT", "RECPROUSM156N", "RRSFS", "SAHMREALTIME",
    "STLFSI4", "T10Y2Y", "T10Y3M", "T10YFF", "TB3MS", "TCU",
    "TBSDODNS", "TEMPHELPS", "TOTALSA", "UMCSENT", "UNRATE", "USRECD",
    "VIXCLS", "W875RX1", "WTISPLC",
)

INDUSTRY_SERIES = (
    "USMINE", "USCONS", "MANEMP", "USWTRADE", "USTRADE", "USTPU",
    "USINFO", "USFIRE", "USPBS", "USEHS", "USLAH", "USSERV",
)

# Retained for the paper/replication cache even though current production uses
# the daily DFF and the precomputed T10YFF spread instead.
AUXILIARY_SERIES = ("FEDFUNDS",)

PRODUCTION_SERIES = tuple(dict.fromkeys(
    NATIONAL_SERIES + INDUSTRY_SERIES + AUXILIARY_SERIES
))

# RETIRED 2026-07-25: USSLIND stopped publishing at 2020-02-01. It was still a
# required source and was forward-filled onto the daily grid, so for 2366 days a
# frozen 2020 constant was carried as current information. No adopted model
# selected it. The file is under raw/quarantine/ with the ten HTML error pages
# that a failed FRED download leaves behind; leading_daily.py now refuses both
# rather than turning them into silent all-NaN features.
#
# RETIRED 2026-07-26: BAA_AAA was never a FRED series id. Asking fredgraph for
# "BAA_AAA" does not 404 -- FRED resolves it to BAA and serves that, with the
# column header "BAA" -- so every refresh wrote the Baa YIELD LEVEL into a file
# whose name promises the Baa-Aaa SPREAD, and every validation in
# fetch_fred_batch.py (header prefix, byte count, row count) passed on it. The
# file was byte-identical to raw/BAA.csv: values 2.94-17.18 where a corporate
# spread runs 0.32-5.64, correlation 0.3546 with the true spread, 8.4% of rows
# inside the 0.5-3.5pp band against 94.5% for the real thing. No production
# builder ever read it -- index_v1, recpage_build, nowcast_harness,
# alfred_replay and leading_daily each compute BAA minus AAA in code from the
# two authoritative series -- so the only effect of keeping it was to burn a
# fetch and leave a plausibly named trap in raw/ for anything that trusted the
# filename. Quarantined rather than repaired: a derived spread sitting in raw/
# has no refresh path and would go stale, and the correct spread is one
# subtraction away from two series that are already fetched.
# THE COMPLETENESS GUARD LIVES HERE, NEXT TO THE LIST IT DESCRIBES.
#
# refresh.sh and refresh_fast.sh each carried their own literal (">= 72"). Quarantining
# BAA_AAA took the manifest to 70 and both refreshes began failing closed on a manifest
# that was correct: the guard was defending a number, not an invariant. A count written
# in one file and enforced in two others is guaranteed to drift, and it drifted silently.
#
# So the expected count sits beside the tuple and is asserted at import. Removing a series
# is now a deliberate two-line edit in ONE file, which is what the guard was always
# supposed to require, and any accidental truncation of the tuple still fails loudly
# everywhere the module is imported.
EXPECTED_SERIES_COUNT = 70
assert len(PRODUCTION_SERIES) == EXPECTED_SERIES_COUNT, (
    f"production manifest has {len(PRODUCTION_SERIES)} series, expected "
    f"{EXPECTED_SERIES_COUNT}. If this change is intended, update "
    f"EXPECTED_SERIES_COUNT in this file; do not edit the refresh scripts.")

DISCONTINUED_SERIES = ()
QUARANTINED_SOURCES = (
    "USSLIND",                       # stopped publishing 2020-02-01
    "BAA_AAA",                       # not a FRED id; served the BAA level
    "PHIL", "PHIL2", "CMRMTSPLM", "GACDISA066MSFRBPHI", "NAPM", "SP500PR",
    "WILL5000IND", "WILL5000INDFC", "WILL5000PR", "WILL5000PRFC",
    "probe_USALOLITONOSTSAMEI",      # all HTML error pages, all orphans
)
DAILY_SERIES = (
    "BAMLH0A0HYM2", "DAAA", "DBAA", "DFF", "DGS1", "DGS10", "DGS2",
    "DGS3MO", "NASDAQCOM", "T10Y2Y", "T10Y3M", "T10YFF", "VIXCLS",
)
WEEKLY_SERIES = (
    "ANFCI", "CC4WSA", "CCSA", "IC4WSA", "ICSA", "IURSA",
    "MORTGAGE30US", "NFCI", "STLFSI4",
)
QUARTERLY_SERIES = ("CMDEBT", "DRTSCILM", "TBSDODNS")
HIGH_LAG_MONTHLY_SERIES = ("CMRMTSPL",)
SERIES_MAX_AGE_DAYS = {
    series: (10 if series in DAILY_SERIES else 21 if series in WEEKLY_SERIES
             # Observation dates are period starts, not publication dates.
             # Balance-sheet/SLOOS quarters and CMRMTSPL therefore need room
             # for their normal release lag while the downloader itself still
             # fails closed whenever a scheduled network refresh cannot run.
             else 300 if series in QUARTERLY_SERIES
             else 150 if series in HIGH_LAG_MONTHLY_SERIES else 120)
    for series in PRODUCTION_SERIES
    if series not in DISCONTINUED_SERIES
}


if __name__ == "__main__":
    print("\n".join(PRODUCTION_SERIES))
