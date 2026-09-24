import json,datetime
m=json.load(open("research/_ch_r39_model.json"))
dv={o["var"]:o for o in json.load(open("research/_ch_r39_vars.json"))}
dec=[r for r in m if "skip" not in r]
for r in dec: r["vpc"]=round(1000*r["pre2000_recessions"]/max(r["cost_store_mb"],1),1)
CONCEPT={"employ":"PAYEMS (nonfarm payrolls)","ipt":"INDPRO (IP, total)",
 "ipm":"IPMAN (IP, manufacturing)","cut":"TCU (capacity util, total)",
 "cum":"MCUMFN (capacity util, mfg)","hstarts":"HOUST (housing starts)",
 "cpi":"CPIAUCSL (CPI)","m1":"M1SL (M1)","m2":"M2SL (M2)","ruc":"UNRATE (landed B-LAND-4-R2)"}
mm=[r for r in dec if r["member_mapped"] and r["var"]!="ruc"]
mm.sort(key=lambda r:-r["vpc"])
oth=[r for r in dec if not r["member_mapped"]]
oth.sort(key=lambda r:(-r["pre2000_recessions"],r["cost_store_mb"]))
tot=sum(r["cost_store_mb"] for r in dec)
def row(r,concept=None):
    return f'| {r["var"]} | {r["freq"]} | {r["first_vintage"]} | {r["landable_vints"]} | {r["cost_store_mb"]:.0f} | {r["pre2000_recessions"]} | {r["tail_2020plus"]} | {r["vpc"]} | {concept or r["label"][:32]} |'
L=[]
L.append("# CH-R39 — RTDSM Rollout Dossier (v1)")
L.append("")
L.append(f"_Read-only probe, window 4. Zero store writes. Generated from the CH-R24 prefetch cache "
 f"(`research/prefetch/rtdsm/`, 236 xlsx / 69 MB / 118 variables) and the B-LAND-4-R2 RUC landing proof. "
 f"UTC {datetime.datetime.utcnow():%Y-%m-%dT%H:%MZ} (wall-clock from host)._")
L.append("")
L.append("## 0. TL;DR")
L.append(f"- RUC is landed (proof). **9 remaining member-mapped bases** cost **~{sum(r['cost_store_mb'] for r in mm)/1024:.1f} GB** "
 f"raw store disk / {sum(r['landable_vints'] for r in mm):,} deep vintages; the **full 115-variable corpus ~{tot/1024:.1f} GB** "
 f"(Qv-optimized) / {sum(r['landable_vints'] for r in dec):,} vintages.")
L.append(f"- **62 of the 105 non-member variables carry ZERO pre-2000 real-time depth** (first vintage after 1990-07) — "
 f"pure disk cost, no unique-history value. 105 non-member bases = **{sum(r['cost_store_mb'] for r in oth)/1024:.1f} GB**.")
L.append("- Boot-health and rebuild held **flat** at RUC scale (F1 attestation cache); the wall is **raw disk**, not boot/rebuild.")
L.append("- **Cost lever:** for quarterly concepts land the `QvQd`/`QvMd` (quarterly-vintage) file, not `MvQd`/`MvMd`. "
 "Monthly-vintage variants triple vintage count for identical quarterly data. This alone cuts the full corpus from ~24.8 GB to ~16.5 GB.")
L.append("")
L.append("## 1. Cost calibration (from B-LAND-4-R2)")
L.append("| anchor | value |")
L.append("|---|---|")
L.append("| RUC landed | 217 deep vintages → **+180 MB** raw store disk |")
L.append("| per-vintage | **~0.83 MB/landable-vintage** (primary model driver) |")
L.append("| per-record | 116,743 recs → 180 MB = ~1.6 KB/record (cross-check) |")
L.append("| deep window | MAX vintage **2019-11** (RUC 217/243 vints land; 26 vints = 2020+ tail deferred) |")
L.append("| cap | 1,139 vintages/base (deep_vintage_window.v1.json) — no RTDSM base exceeds it |")
L.append("| boot/rebuild | bh doctor 0.16→0.12s, verify --full 4.34→3.59s — **flat** (F1 content-addressed attestation) |")
L.append("")
L.append("_Cost model = landable_vintages × 0.83 MB. Landable_vintages = contiguous vintage periods from first_vintage "
 "to 2019-11 (arithmetic reproduces RUC=217 exactly). Value = # NBER recessions whose peak ≥ the base's first real-time "
 "vintage AND < 2000 — i.e. real-time turning points ALFRED generally cannot replay (its vintages mostly start 1990s+)._")
L.append("")
L.append("## 2. Tranche A — 9 remaining member-mapped bases (ranked value ÷ cost)")
L.append("| var | fq | firstV | land_v | cost MB | pre-2000 rec | 2020+ tail | rec/GB | FRED concept |")
L.append("|---|---|---|---|---|---|---|---|---|")
for r in mm: L.append(row(r,CONCEPT.get(r["var"])))
L.append(f"| **sum** | | | **{sum(r['landable_vints'] for r in mm):,}** | **{sum(r['cost_store_mb'] for r in mm):.0f}** | | | | |")
L.append("")
L.append("Reading: **cpi/m1/m2** (quarterly-vintage, 180 MB, 5 pre-2000 recessions each) are the cheapest depth per GB "
 "(27.8 rec/GB). **hstarts/employ/ipt/ipm** are monthly-vintage (~520–570 MB) but parallel core Watch channels "
 "(payrolls, IP, housing) and each reach 5 pre-2000 recessions. **cum** reaches 3 (1980/81/90); **cut** only 1 (1990) "
 "— capacity-util real-time history is shallow.")
L.append("")
L.append("## 3. Tranche B — 105 non-member bases (national-accounts detail)")
L.append(f"- Aggregate **{sum(r['cost_store_mb'] for r in oth)/1024:.1f} GB** / {sum(r['landable_vints'] for r in oth):,} vintages.")
L.append(f"- **{sum(1 for r in oth if r['pre2000_recessions']==0)} of 105** have zero pre-2000 real-time depth (recent series, e.g. the `*M` monthly PCE detail added post-2018).")
L.append(f"- **{sum(1 for r in oth if r['pre2000_recessions']>=5)}** reach the full 5 pre-2000 recessions (65Q4 GDP-accounting series: routput, noutput, rcon, ncon, npi, ndpi, monetary-base/reserves basebasa/nbrbasa/trbasa, etc.).")
L.append("- None parallel a *current* Watch channel; they are GDP/income-account subcomponents. Land only on demand when a specific V2 unit requires the component.")
L.append("")
L.append("Highest-value non-member candidates (if a broader real-GDP/real-time-nowcast unit is ever admitted):")
L.append("| var | fq | firstV | land_v | cost MB | pre-2000 rec | concept |")
L.append("|---|---|---|---|---|---|---|")
for r in oth[:8]: L.append(f'| {r["var"]} | {r["freq"]} | {r["first_vintage"]} | {r["landable_vints"]} | {r["cost_store_mb"]:.0f} | {r["pre2000_recessions"]} | {r["label"][:40]} |')
L.append("")
L.append("## 4. Tranche C — 3 special-format bases (own-lane, own transcoder)")
L.append("| var | files | bytes | note |")
L.append("|---|---|---|---|")
L.append(f'| gdpplus | 2 | ~464 KB | Philly GDPplus (own coincident GDP measure); date-stamped vintages (GDPPLUS_MMDDYY); ~154 vintages. Not a FRED member — own-base, own parser. |')
L.append(f'| ads | 2 | ~812 KB | Aruoba-Diebold-Scotti daily business-conditions index; single most-current-vintage file + accuracy sheet. Not a vintage matrix. |')
L.append(f'| atsix | 1 | ~1.0 MB | ATSIX inflation-expectation term structure (infexp3…infexp120 = horizons, not vintages). Forecast-class, not real-time realized data. |')
L.append("These need bespoke offline-bind logic like RUC did; defer to a dedicated batch. GDPplus is the only recession-relevant one.")
L.append("")
L.append("## 5. Recommended rollout")
L.append("1. **Tranche A1 (next data sitting, ~0.5 GB):** land `cpi`, `m1`, `m2` — quarterly-vintage, cheapest depth/GB, "
 "and they fill price/money channels currently absent from any landed real-time lane. Lowest scale risk (each ~= RUC).")
L.append("2. **Tranche A2 (~2.2 GB, one base per sitting):** `employ`, `ipt`, `ipm`, `hstarts` — monthly-vintage; parallel "
 "PAYEMS/INDPRO/HOUST core channels; 5 pre-2000 recessions each. Land one per sitting and re-measure boot/rebuild — "
 "660–685 vintages is 3× RUC and beyond the proven single-base scale point.")
L.append("3. **Tranche A3 (~0.8 GB):** `cum` (3 recessions), then `cut` (1) — capacity util, lower marginal value.")
L.append("4. **Defer Tranche B (12.9 GB):** land individual national-accounts components only when a unit needs them. "
 "Never bulk-land; 62 of them add cost with zero real-time-history value.")
L.append("5. **Defer Tranche C** to a special-format offline-bind batch (GDPplus first).")
L.append("")
L.append("**Always pick the `Qv` lane for quarterly concepts** (3× disk saving vs `Mv`). **The 2020+ shallow tail "
 "(~26 quarterly / ~80 monthly vintages per base) is out of the deep window** and needs a separate `.ASOF` shallow "
 "lane — enumerate, don't silently drop.")
L.append("")
L.append("## 6. Owner pop-up questions (plain language)")
L.append("**Q1 — How deep do you want the real-time history to go?** RTDSM is the only source that lets the monitor see "
 "unemployment/payrolls/IP *as they were first reported* back to the 1960s — before the modern ALFRED vintages start "
 "(~1990s). Landing all 9 core series costs ~3.5 GB of disk. Do you want (a) just price+money (cpi/m1/m2, ~0.5 GB), "
 "(b) all 9 core series (~3.5 GB), or (c) core + the deep GDP-accounts too (~16 GB)?")
L.append("")
L.append("**Q2 — Land the monthly-vintage giants one at a time?** employ/ipt/ipm/hstarts are each ~3× the size of the "
 "proven RUC landing (~550 MB, 660–685 vintages). RUC proved boot/rebuild stay flat, but not at this scale. OK to land "
 "one per sitting and re-measure before the next, rather than batching all four?")
L.append("")
L.append("**Q3 — The 2020-to-today tail.** The deep lane stops at Nov-2019 (the same window rule as every other deep base). "
 "That drops the last ~5 years of real-time vintages for each RTDSM series (the COVID + 2022 period). Do you want a "
 "separate shallow real-time lane for 2020+ now, or defer until the deep lanes are in?")
L.append("")
L.append("**Q4 — GDPplus.** Philly publishes its own GDP growth measure (GDPplus) with real-time vintages. It parallels "
 "no FRED series and needs its own parser. Is it in scope as a comparator, or out (forecast/own-index class)?")
L.append("")
L.append("**Q5 — The 62 zero-history components.** 62 of the 105 GDP-account subcomponents only have real-time data from "
 "after 2018 — they add disk with no pre-2000 depth. Confirm we NEVER bulk-land these and only pull one if a specific "
 "unit calls for it?")
L.append("")
open("research/rtdsm_rollout_dossier_v1.md","w").write("\n".join(L))
print("wrote research/rtdsm_rollout_dossier_v1.md",len("\n".join(L)),"chars")
