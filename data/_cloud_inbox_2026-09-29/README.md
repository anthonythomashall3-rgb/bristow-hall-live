# Cloud inbox, 29 September 2026 (the other account's cloud session)

Real-time data gathered in the cloud for the Mac to take in. No collection number: claim one on the Mac
(`python3 _CLAIMS/claim.py next …`) and move this folder there. Nothing here is wired into any tool; collections 105 and 45
are untouched (an earlier commit on this branch had staged a switch inside 105; it is withdrawn, and the patch is kept as
`code/staged_wiring_for_v376_NOT_APPLIED.diff` for reference only).

## 1. JOLTS job openings as printed, 2004-2010

`jolts_asprinted_2004_2010/` — Table 1 (total nonfarm, SA, thousands) of every BLS JOLTS release from 15 April 2004 (the
first seasonally adjusted table) to 11 August 2010 (ALFRED's first vintage): 539 printed values, 77 releases, the raw
release texts in `raw/`. `code/jolts_asprinted.py` rebuilds the CSV from `raw/` (and `--fetch` re-downloads; bls.gov needs
`BLS_UA` with a contact). The 11 August 2010 release matches ALFRED month for month.

- The releases of 30 July 2002 - March 2004 were not seasonally adjusted (BLS: "comparisons between consecutive months
  should not be used"); no SA JOLTS existed before 15 April 2004. A vacancy object read before then is not a print.
- Check against the Mac's vacancy as printed (collections 522/523) before use; this may duplicate it.

## 2. State insured unemployment rates as printed, 2020-2026, dated (a collection 45 defect)

`state_page8_2020_2026/state_iur_asprinted_2020_2026_dated.csv` — 17,013 state-weeks, insured weeks 25 Apr 2020 -
15 Aug 2026. **Defect in 45 (reported, not fixed there):** `45/state_first_prints_clean.csv` has 17,066 rows from May 2020
on with `ic_week_ended` and `iu_week_ended` blank, because page 8 stopped printing the year in its headers and 45's parser
required it. A loader that drops undated rows (v3.76's `s2/state_rates_as_printed.py`) reads FRED's current file for
those weeks instead of the prints — the whole 2024 episode.

- Dated from the release file's week (insured week = claims week - 7 days), checked against the header of all 321 pages
  re-read from oui.doleta.gov (`raw/`); all 17,013 rates equal 45's values. `0223.html` in the 2023 archive is a
  misnamed identical copy of `120223.html` (53 rows dropped).
- Absent from the Department's archive (404): week ended 2022-12-24 and the shutdown weeks 2025-08-30 and
  2025-09-20 .. 2025-11-01 — dark in real time.

## 3. Tests run here (on v3.76, the LIVE rule — not the best version)

Scratch-HOME rebuilds of the v3.76 bundle only. They say nothing about C6 on T17p9; re-run there.

- Both sets switched in: frozen record, 13 episodes and branches, standing and near misses unchanged; 221 sub-line
  series days move.
- Knockouts on v3.76's vacancy gap: held "falling" over 2000-12 .. 2010-06 it would add opens on 2003-07-03 (X) and
  2006-12-14 (B). On the printed JOLTS the gap peaks at 0.064 (2004-07) against the 0.25 line (0.131 on the revised file);
  on the help-wanted index for 2002-03 it peaks at 0.166.
- In v3.76's build several objects are dark early: the Sahm-gap objects carry no reading before 15 March 1960 (ALFRED
  UNRATE's first vintage), the hours pair before 3 November 1961, state breadth before June 1984. Whether C6/T17p9 is the
  same is for the Mac to check.

## 4. Still being collected in the cloud (results will be added here)

Permits as printed 1960-99 (Economic Indicators, FRASER); UNRATE, MANEMP, AWHMAN, NDMANEMP, PAYEMS as printed 1948-61;
the Help-Wanted Index as printed (BCD series 46, SCB, press 1996-2004); state insured rates as printed 1984-2002; Google
Trends pulls saved in 2020; the handoff's remaining weekly gaps (rate 22, level ~76, claims 3); new real-time candidates.
