#!/usr/bin/env python3
"""CH-R79 ROUTE_BUILD BACKLOG RANKING (read-only probe).

Reconciles CH-R70 reservation triage (blocker classes) with CH-R71 timemode
census (run-only vs archive-needed) into ONE ranked adapter build/run program.

Inputs (read-only):
  - research/reservation_triage/reservation_triage.v1.json   (CH-R70, 85 rows)
  - live_data/config/planned_sources.v1.json                  (75 reservations; fields cited)
  - live_data/rmv2_live/adapters.py                           (34 proven parse_* shapes)
  - research/timemode_census/timemode_census.v1.json          (CH-R71, run-only vs archive)

Outputs:
  - research/route_backlog/route_backlog_rank.v1.csv
  - research/route_backlog/tranches.v1.json

NO store/config writes. NO network.
"""
import json, csv, re

TRIAGE = json.load(open("research/reservation_triage/reservation_triage.v1.json"))
PS = {s["source_id"]: s for s in json.load(open("live_data/config/planned_sources.v1.json"))["sources"]}
PROVEN = set(re.findall(r"def (parse_[a-z0-9_]+)", open("live_data/rmv2_live/adapters.py").read()))

# ---------------------------------------------------------------------------
# 1. SHAPE-FAMILY MAP. Each rule cites a proven parse_* fn (shape_status=PROVEN)
#    or names a NEW shape family. Cited evidence field = endpoint host +
#    endpoint_status + name-match to the proven parser. Per-source column maps
#    on a PROVEN shape are CONFIG, not a new parser (owner cap counts NEW shapes
#    only, CLAUDE_CODE_PROGRESS 2026-08-03).
# ---------------------------------------------------------------------------
# PROVEN: source_id -> (proven_parser_fn, why)
PROVEN_MAP = {
    # fiscaldata.treasury.gov JSON datasets  (parse_fiscaldata_json / _mts)
    "treasury_auction":     ("parse_fiscaldata_json", "fiscaldata.treasury.gov dataset JSON, same API family as landed treasury_* fiscaldata routes"),
    "treasury_debt_penny":  ("parse_fiscaldata_json", "fiscaldata.treasury.gov DebtToThePenny dataset JSON"),
    "treasury_ui_advances": ("parse_fiscaldata_json", "fiscaldata.treasury.gov dataset JSON (UI trust-fund advances)"),
    "treasury_mts":         ("parse_treasury_mts_totals_json", "dedicated MTS totals parser already exists; route reconfirm only"),
    # Socrata open-data JSON  (parse_socrata_json)
    "bts_tsi":       ("parse_socrata_json", "data.bts.gov OPEN_DATASET = Socrata; matches proven socrata shape"),
    "sba_7a_504":    ("parse_socrata_json", "data.sba.gov PUBLIC_DATASET = Socrata"),
    "cfpb_complaints": ("parse_socrata_json", "consumerfinance.gov complaints DB = Socrata-backed JSON API"),
    # exact-name proven parsers
    "cfpb_mortgage_performance": ("parse_cfpb_mortgage_performance_state_csv", "exact proven parser exists"),
    "census_btos":   ("parse_census_btos_xlsx", "exact proven parser exists (route DISCOVERY_ONLY, shape proven)"),
    "census_qss":    ("parse_census_qss_zip", "exact proven parser exists"),
    "fema_disasters": ("parse_fema_disaster_declarations_json", "exact proven parser (OpenFEMA v2 JSON)"),
    "tsa_throughput": ("parse_tsa_passenger_html", "exact proven parser (TSA web-table HTML)"),
    # Fed district survey xlsx  (parse_regional_survey_xlsx) — per-district col map = CONFIG
    "dallas_tmos":   ("parse_regional_survey_xlsx", "Dallas TMOS survey xlsx = proven regional-survey shape; col map=config"),
    "dallas_tssos":  ("parse_regional_survey_xlsx", "Dallas TSSOS survey xlsx = same shape"),
    "nyfed_empire":  ("parse_regional_survey_xlsx", "Empire State mfg survey xlsx = same shape"),
    "nyfed_business_leaders": ("parse_regional_survey_xlsx", "NY Business Leaders survey xlsx = same shape"),
    "richmond_mfg":  ("parse_regional_survey_xlsx", "Richmond mfg survey xlsx = same shape (route DISCOVERY_ONLY)"),
    "richmond_services": ("parse_regional_survey_xlsx", "Richmond services survey xlsx = same shape (route DISCOVERY_ONLY)"),
    "kansascity_mfg": ("parse_regional_survey_xlsx", "KC mfg survey xlsx = same shape"),
    "philly_mbos":   ("parse_regional_survey_xlsx", "Philly MBOS survey xlsx = same shape"),
    "philly_nmbos":  ("parse_regional_survey_xlsx", "Philly NMBOS survey xlsx = same shape"),
    "chicago_cfsec": ("parse_regional_survey_xlsx", "Chicago CFSEC survey data = same shape (route DISCOVERY_ONLY)"),
    "nyfed_sce":     ("parse_regional_survey_xlsx", "NY SCE core survey xlsx = same shape (periodic modules=config)"),
    "dallas_tmos_x": None,
    # Fed DDP csv  (parse_fed_ddp_csv)
    "fed_scoos":     ("parse_fed_ddp_csv", "federalreserve.gov DDP_ROUTE = proven fed_ddp csv shape"),
    # published-output tabular csv/xlsx  (parse_tabular_csv / parse_fred_graph_csv)
    "chicago_carts": ("parse_tabular_csv", "chicagofed.org published-output index csv/xlsx = tabular shape"),
    "nyfed_gscpi":   ("parse_tabular_csv", "GSCPI published-output xlsx single-series = tabular shape"),
    "atlanta_wage_growth_tracker": ("parse_tabular_csv", "Atlanta wage tracker published-output xlsx = tabular shape"),
    "fed_fci_g":     ("parse_tabular_csv", "FCI-G published-output csv = tabular shape"),
    "usda_food_price_outlook": ("parse_tabular_csv", "ERS food-price-outlook csv download = tabular shape"),
    # FRED-MD named panel archives (landed B-LAND-3C, panel handling proven)
    "fred_macro_panel_archives": ("parse_forecast_xlsx", "FRED-MD named monthly panel archives; panel landing proven B-LAND-3C (reuse panel/xlsx shape)"),
}

# NEW shape families: source_id -> shape_family_name
NEW_MAP = {
    # Wayback CDX snapshot protocol (1 shape covers 3)
    "bls_empsit_cdx_wayback_snapshots": "wayback_cdx_snapshot",
    "bls_jolts_cdx_wayback_snapshots":  "wayback_cdx_snapshot",
    "dol_ui_cdx_wayback_snapshots":     "wayback_cdx_snapshot",
    # EIA bulk-zip snapshot manifest (1 shape covers 5)
    "eia_bulk_eba":         "eia_bulk_zip",
    "eia_bulk_ng":          "eia_bulk_zip",
    "eia_bulk_pet":         "eia_bulk_zip",
    "eia_bulk_pet_imports": "eia_bulk_zip",
    "eia_bulk_steo":        "eia_bulk_zip",
    # SDMX dataflow XML (1 shape, 1 row now; feeds OECD revision lanes)
    "oecd_revision_us_sdmx_dataflow": "sdmx_dataflow_xml",
    # CDC WONDER POST-XML API / provisional
    "cdc_provisional_deaths": "cdc_wonder_postxml",
    "cdc_respviruses":        "cdc_respnet_dataset",
    # Fed HTML table hub scrape (multi-table)
    "fed_ach":                "fed_html_table_hub",
    "fed_chargeoff_delinquency": "fed_release_table",
    # BLS bulk flat-file directory + data-table variants
    "bls_bed":   "bls_flatfile_series",
    "bls_laus":  "bls_flatfile_series",
    "bls_mxp":   "bls_flatfile_series",
    "bls_work_stoppages": "bls_data_table",
    # Census download/program variants beyond btos/qss
    "census_qfr":  "census_program_download",
    "census_qtax": "census_program_download",
    "census_hps_htops": "census_program_download",
    "census_economic_indicators_release_packages": "census_release_package",
    "bea_release_packages": "bea_release_package",
    # DOL ETA weekly release archive (html release archive)
    "dol_ui_national_weekly_release_archive": "dol_release_archive_html",
    # Housing / mortgage program downloads
    "hud_fha_single_family": "hud_program_download",
    "hud_fha_multifamily":   "hud_program_download",
    "ffiec_hmda":            "ffiec_bulk_download",
    # Bank/credit-union regulatory bulk
    "ncua_call_reports":     "ncua_call_report_zip",
    # Treasury TIC release+archive (html/csv mix)
    "treasury_tic":          "treasury_tic_release",
    # CFTC COT weekly
    "cftc_cot":              "cftc_cot_flatfile",
    # Courts / transport / disaster / food-assist bulk
    "uscourts_bankruptcy":   "uscourts_table_download",
    "fhwa_tvt":              "fhwa_report_download",
    "fhwa_ucr":              "fhwa_report_download",
    "noaa_storm_events":     "noaa_bulk_ftp",
    "usda_snap":             "usda_admin_program",
    # Fed/NYFed markets & survey landings (html)
    "fed_sfos":              "fed_release_table",
    "nyfed_primary_dealers": "nyfed_markets_release",
}

# ---------------------------------------------------------------------------
# 2. VALUE SCORE (explicit, no unstated weights).
#    value = 3*cadence + 2*novelty + 1*depth + 1*automatable_bonus
#    cadence: from cadence field.  novelty: channel diversity vs landed universe
#    (CH-R58 diversity logic + role field).  depth: history length hint.
# ---------------------------------------------------------------------------
def cadence_score(cad):
    c = cad.lower()
    if c.startswith("daily") or "daily" in c: return 4
    if "weekly" in c or "biweekly" in c: return 3
    if "monthly" in c: return 2
    if "quarter" in c: return 1
    return 0   # annual / release_event / irregular / auction_event

# novelty by channel (0-3). Landed universe already dense in: rates/yield-curve,
# NIPA/IP/labor headline, financial-conditions(NFCI). CH-R58: real-time diversity
# lifts come from oil/FX/mobility/freight/energy, NOT more NIPA or credit spreads.
NOVELTY = {
    # high-novelty real-activity / high-freq disturbance channels
    "eia_bulk_eba": 3, "eia_bulk_ng": 3, "eia_bulk_pet": 3, "eia_bulk_pet_imports": 3, "eia_bulk_steo": 2,
    "fhwa_tvt": 3, "fhwa_ucr": 2, "bts_tsi": 3, "chicago_carts": 3, "tsa_throughput": 3,
    "cfpb_complaints": 2, "noaa_storm_events": 2, "cdc_provisional_deaths": 2, "cdc_respviruses": 1,
    "nyfed_gscpi": 3, "cftc_cot": 2, "treasury_tic": 2,
    # labor breadth / diffusion (S15) — medium
    "bls_bed": 2, "bls_laus": 2, "bls_mxp": 1, "bls_work_stoppages": 1,
    "atlanta_wage_growth_tracker": 2, "nyfed_sce": 2,
    # regional Fed diffusion surveys (S15 breadth) — medium (many, correlated)
    "dallas_tmos": 2, "dallas_tssos": 1, "nyfed_empire": 2, "nyfed_business_leaders": 1,
    "richmond_mfg": 2, "richmond_services": 1, "kansascity_mfg": 2, "philly_mbos": 2,
    "philly_nmbos": 1, "chicago_cfsec": 1, "fed_sfos": 1, "fed_scoos": 1,
    # credit-quality / damage-index inputs — medium
    "fed_chargeoff_delinquency": 2, "ncua_call_reports": 1, "hud_fha_single_family": 1,
    "hud_fha_multifamily": 1, "ffiec_hmda": 1, "sba_7a_504": 1, "usda_snap": 2,
    "cfpb_mortgage_performance": 2, "fed_ach": 1, "fed_fci_g": 0,
    # treasury fiscal — low novelty (already have DTS/MTS landed)
    "treasury_auction": 1, "treasury_debt_penny": 1, "treasury_ui_advances": 2, "treasury_mts": 0,
    # census real-activity
    "census_btos": 2, "census_qss": 1, "census_qfr": 1, "census_qtax": 1, "census_hps_htops": 2,
    "census_economic_indicators_release_packages": 1, "bea_release_packages": 0,
    "fema_disasters": 1, "uscourts_bankruptcy": 2, "usda_food_price_outlook": 1,
    # vintage / methodology instrumentation
    "bls_empsit_cdx_wayback_snapshots": 3, "dol_ui_cdx_wayback_snapshots": 3,
    "bls_jolts_cdx_wayback_snapshots": 3, "oecd_revision_us_sdmx_dataflow": 2,
    "fred_macro_panel_archives": 2,
}

def depth_score(sid, s):
    # long-history / vintage-bearing = episode-replay value
    if sid.endswith("cdx_wayback_snapshots"): return 1  # as-of first-print instrumentation
    if "sdmx" in sid or "panel_archives" in sid: return 1
    rev = (s.get("revision_policy") or "").lower()
    return 1 if ("history" in rev or "vintage" in rev) else 0

rows = []
tech = [x for x in TRIAGE["entries"] if x["blocker_class"] == "technical_route_missing"]
cred = [x for x in TRIAGE["entries"] if x["blocker_class"] == "needs_credential"]

for x in tech:
    sid = x["source_id"]
    s = PS.get(sid)
    if s is None:  # philadelphia_ads = matrix-only, captured-but-unparsed
        rows.append(dict(source_id=sid, shape_status="NEW", shape_family="ads_capture_parse",
                         proven_parser="", cadence="daily_business_day?", cadence_score=4,
                         novelty=1, depth=0, route_automatable=False,
                         route_status="matrix_only_captured_unparsed", value=0, tranche="",
                         evidence="CH-R70: philadelphia_ads captured-but-unparsed, no vintages (CH-R58)"))
        continue
    cad = s["cadence"]; est = s["endpoint_status"]
    automatable = "DISCOVERY_ONLY_NOT_AUTOMATABLE" not in est and "NOT_AUTOMATABLE" not in est
    if sid in PROVEN_MAP and PROVEN_MAP[sid]:
        fn, why = PROVEN_MAP[sid]
        assert fn in PROVEN, f"cited parser {fn} not in adapters.py"
        shape_status, shape_family, proven = "PROVEN", fn, fn
        ev = f"{why}; endpoint_status={est}"
    elif sid in NEW_MAP:
        shape_status, shape_family, proven = "NEW", NEW_MAP[sid], ""
        ev = f"no proven parse_* covers {est}; new shape={NEW_MAP[sid]}; host={s['endpoint'][:40]}"
    else:
        shape_status, shape_family, proven = "NEW", "UNCLASSIFIED", ""
        ev = f"unmapped; endpoint_status={est}"
    cs = cadence_score(cad); nov = NOVELTY.get(sid, 1); dep = depth_score(sid, s)
    autob = 1 if automatable else 0
    value = 3*cs + 2*nov + dep + autob
    rows.append(dict(source_id=sid, shape_status=shape_status, shape_family=shape_family,
                     proven_parser=proven, cadence=cad, cadence_score=cs, novelty=nov, depth=dep,
                     route_automatable=automatable,
                     route_status=("automatable" if automatable else "discovery_only_reconfirm_first"),
                     value=value, tranche="", evidence=ev))

# ---------------------------------------------------------------------------
# 3. RANK + TRANCHE PACK.  Eligible = route_automatable. DISCOVERY_ONLY rows go
#    to a reconfirm-first pool (own tranche tail). Greedy: sort value desc; pack
#    8-12 routes/tranche; a tranche admits a NEW shape only if it keeps distinct
#    NEW shapes <=5 (owner cap). PROVEN shapes are free (0 new shapes).
# ---------------------------------------------------------------------------
elig = sorted([r for r in rows if r["route_automatable"]], key=lambda r: (-r["value"], r["source_id"]))
recon = sorted([r for r in rows if not r["route_automatable"]], key=lambda r: (-r["value"], r["source_id"]))

tranches = []
cur, cur_shapes = [], set()
def flush():
    global cur, cur_shapes
    if cur:
        tranches.append((cur, set(cur_shapes)))
    cur, cur_shapes = [], set()

for r in elig:
    new_shape = r["shape_family"] if r["shape_status"] == "NEW" else None
    would = cur_shapes | ({new_shape} if new_shape else set())
    if len(cur) >= 12 or (len(would) > 5):
        flush()
    elif len(cur) >= 8 and new_shape and new_shape not in cur_shapes and len(would) > 5:
        flush()
    cur.append(r)
    if new_shape: cur_shapes.add(new_shape)
flush()

# assign tranche ids; reconfirm-first pool = its own trailing tranche(s)
tid = 0
out_tranches = []
for members, shapes in tranches:
    tid += 1
    name = f"T{tid}"
    for r in members: r["tranche"] = name
    out_tranches.append(dict(tranche=name, n_routes=len(members),
                             new_shapes=sorted(s for s in shapes),
                             n_new_shapes=len(shapes),
                             route_ids=[r["source_id"] for r in members],
                             value_range=[members[-1]["value"], members[0]["value"]]))
# reconfirm pool
if recon:
    tid += 1
    name = f"T{tid}_RECONFIRM_FIRST"
    rshapes = set(r["shape_family"] for r in recon if r["shape_status"] == "NEW")
    for r in recon: r["tranche"] = name
    out_tranches.append(dict(tranche=name, n_routes=len(recon),
                             new_shapes=sorted(rshapes), n_new_shapes=len(rshapes),
                             route_ids=[r["source_id"] for r in recon],
                             note="endpoint_status=DISCOVERY_ONLY_NOT_AUTOMATABLE: a URL/discovery reconfirm step precedes the parser build; NOT a clean 8-12 build tranche",
                             value_range=[recon[-1]["value"], recon[0]["value"]] if recon else []))

# ---------------------------------------------------------------------------
# 4. EMIT
# ---------------------------------------------------------------------------
allrows = elig + recon
cols = ["source_id","tranche","value","shape_status","shape_family","proven_parser",
        "cadence","cadence_score","novelty","depth","route_automatable","route_status","evidence"]
with open("research/route_backlog/route_backlog_rank.v1.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in allrows: w.writerow({k: r[k] for k in cols})

cred_list = [dict(source_id=x["source_id"], prerequisite=x["prerequisite"],
                  rights=x.get("rights",""), note=x.get("notes","")) for x in cred]

# Alternate lens: PROVEN-FAST program = zero-new-parser routes, packed 8-12/tranche.
# Recommended B-ROUTE-1 opener: ships value with 0 parser risk (config+wiring only).
pf = sorted([r for r in elig if r["shape_status"] == "PROVEN"], key=lambda r: (-r["value"], r["source_id"]))
proven_fast = []
for i in range(0, len(pf), 12):
    chunk = pf[i:i+12]
    proven_fast.append(dict(tranche=f"PF{i//12+1}", n_routes=len(chunk), n_new_shapes=0,
                            route_ids=[r["source_id"] for r in chunk],
                            value_range=[chunk[-1]["value"], chunk[0]["value"]]))

doc = dict(
    probe="CH-R79_ROUTE_BACKLOG_RANKING",
    authority="CH-R70 reservation_triage.v1.json + CH-R71 timemode_census.v1.json",
    scoring_rule="value = 3*cadence_score + 2*novelty + 1*depth + 1*automatable_bonus; "
                 "cadence(daily=4,weekly/biweekly=3,monthly=2,quarterly=1,else=0); "
                 "novelty 0-3 by channel diversity vs landed universe (CH-R58); "
                 "depth 1 if vintage/long-history else 0; automatable_bonus 1 if route not DISCOVERY_ONLY",
    owner_caps="8-12 routes/tranche, <=5 NEW parser shapes/tranche (CLAUDE_CODE_PROGRESS 2026-08-03); "
               "PROVEN shapes reuse existing parse_* fn = 0 new shapes",
    n_technical=len(rows), n_automatable=len(elig), n_reconfirm_first=len(recon),
    n_credential_bound=len(cred_list),
    proven_shape_count=sum(1 for r in rows if r["shape_status"]=="PROVEN"),
    new_shape_count=sum(1 for r in rows if r["shape_status"]=="NEW"),
    distinct_new_shapes=sorted(set(r["shape_family"] for r in rows if r["shape_status"]=="NEW")),
    tranches=out_tranches,
    proven_fast_program=dict(
        note="RECOMMENDED B-ROUTE-1 opener: 25 PROVEN-shape automatable routes, 0 new parsers, "
             "config+route-wiring only. Ship these before any new-shape tranche to front-load "
             "value at minimal parser risk.",
        n_routes=len(pf), tranches=proven_fast),
    credential_owner_signup_list=cred_list,
    feeds="B-ROUTE-1_RESERVATION_ADAPTERS_T1 (W1)",
    caveats=[
      "PROVEN = format matches an existing parse_* shape; per-source column/route wiring still needed but NOT a new parser (CH-R71: 'whether a RESERVED_ONLY collector works is the run, not tested here').",
      "DISCOVERY_ONLY rows carry a proven-or-new shape BUT need a URL/route reconfirm first; kept out of clean build tranches.",
      "novelty weights are a documented judgment (channel-level), not measured loadings; re-score if CH-R74 candidate x-check lands.",
      "vintage_gap_map.v1.json still ABSENT (CH-R71) — route-b/archive lanes not in this build program (those are B-ARCHIVE, not adapter build).",
    ],
)
json.dump(doc, open("research/route_backlog/tranches.v1.json","w"), indent=1)

# console summary (small)
print("technical rows:", len(rows), "| automatable:", len(elig), "| reconfirm-first:", len(recon), "| credential:", len(cred_list))
print("PROVEN:", doc["proven_shape_count"], "NEW:", doc["new_shape_count"], "| distinct new shapes:", len(doc["distinct_new_shapes"]))
for t in out_tranches:
    print(f"  {t['tranche']:>22}: {t['n_routes']:2d} routes, {t['n_new_shapes']} new shapes {t['new_shapes']} val {t['value_range']}")
print("T1 ids:", out_tranches[0]["route_ids"])
