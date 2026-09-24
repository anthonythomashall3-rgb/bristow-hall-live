#!/usr/bin/env python3
"""B-EXT-1948 step 5: coverage manifest + gap map for the VALIDATION-ONLY lane.
Distinct third lane -- NOT merged into the production realtime_coverage_manifest /
asof_surface_gap_map (that would violate the owner 'never merged' ruling + §3.6)."""
import os, json, datetime as dt, tempfile, hashlib
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
ARCHIVE = REPO / "data_archive" / "current_revised_and_spatial"
SRC = (REPO / "method_source" / "index_v1.py").read_text()
CS = ["ICSA","IURSA","SAHMREALTIME","UNRATE","INDPRO","CMRMTSPL","TCU","GACDFSA066MSFRBPHI",
    "NASDAQCOM","BAA","AAA","BAA10Y","NFCI","VIXCLS","HOUST","PERMIT","UMCSENT","W875RX1",
    "GS10","GS1","USRECD","RRSFS","MORTGAGE30US","PAYEMS","CCSA","DBAA","DAAA"]

os.environ["NOWCAST_DISABLE"] = "1"
ns = {"__name__": "__gen__", "__file__": str(REPO/"method_source"/"index_v1.py")}
with tempfile.TemporaryDirectory() as t:
    raw = Path(t)/"raw"; raw.mkdir()
    for s in CS: (raw/(s+".csv")).symlink_to(ARCHIVE/(s+".csv"))
    (raw/"vintages").symlink_to(ARCHIVE/"vintages")
    os.environ["INDEX_OUT"] = str(Path(t)/"o.json")
    cwd=os.getcwd(); os.chdir(t)
    try: exec(compile(SRC,"gen","exec"), ns)
    finally: os.chdir(cwd)

zval = ns["zval"]; CHANNELS = ns["CHANNELS"]

# CH-R102 structural-vs-gap tags (adopted verbatim, member-level)
STRUCT = {
 "UNRATEv": "structural_floor_BLS_CPS_monthly_1948", "INDPRO": "deep_1919_available",
 "BAAAAA": "deep_1919_available", "UMCSENT": "measurement_start_1952",
 "SAHM": "derived_construct_start_1959", "HOUST": "measurement_start_1959",
 "W875": "measurement_start_1959", "PERMIT": "measurement_start_1960",
 "ICSA": "measurement_start_1967", "CMRMT": "measurement_start_1967",
 "TCU": "measurement_start_1967", "PHILLY": "structural_survey_founded_1968",
 "NFCI": "structural_index_created_1971", "IURSA": "measurement_start_1971",
 "NASDAQ": "structural_exchange_founded_1971", "BAA10Y": "series_start_1986",
 "VIX": "structural_cboe_instrument_1990"}

def months(a, b):
    y,m = a.year, a.month
    while (y,m) <= (b.year, b.month):
        yield dt.date(y,m,1)
        m += 1
        if m==13: m=1; y+=1

# monthly member/channel presence + weight_share, 1948-01 .. 1976-06
manifest_rows = []
first_avail = {}
for d in months(dt.date(1948,1,1), dt.date(1976,6,1)):
    present = {name: [m for m in members if zval(m,d) is not None] for name,(w,members) in CHANNELS.items()}
    chans = sorted(k for k,v in present.items() if v)
    nmem = sum(len(v) for v in present.values())
    wshare = round(sum(w for name,(w,members) in CHANNELS.items() if present[name]), 3)
    manifest_rows.append({"month": d.isoformat(), "n_members": nmem,
                          "weight_share": wshare, "channels_nonempty": chans})
    for name, got in present.items():
        for mem in got:
            if mem not in first_avail: first_avail[mem] = d.isoformat()

manifest = {
 "schema_version": "recession-monitor-v2.ext1948-coverage-manifest.v1",
 "lane_label": "validation_only_1948_analog_lane",
 "distinct_third_lane": True, "never_merged": True,
 "semantics": "channel counts full weight if >=1 member available; weight_share = sum(available channel weights). Channel-generous (CH-R102 semantics).",
 "window": ["1948-01-01","1976-06-01"], "n_months": len(manifest_rows),
 "monthly": manifest_rows}

gapmap = {
 "schema_version": "recession-monitor-v2.ext1948-gap-map.v1",
 "lane_label": "validation_only_1948_analog_lane",
 "distinct_third_lane": True, "never_merged": True,
 "member_first_available_in_lane": first_avail,
 "member_structural_vs_gap": STRUCT,
 "channels_structurally_empty_pre1971": ["finconditions (NFCI created 1971)"],
 "note": "Two whole channels are absent/thin pre-1953: finconditions structurally empty until NFCI 1971; housingincome empty until UMCSENT 1952-11. 3-of-5 channels at 1948, 4-of-5 at 1953. This is the DIFFERENT-INSTRUMENT boundary (CH-R102 §3.1)."}

mp = REPO/"research"/"ext1948"/"coverage_manifest.v1.json"
gp = REPO/"research"/"ext1948"/"gap_map.v1.json"
mp.write_text(json.dumps(manifest, indent=1, sort_keys=True))
gp.write_text(json.dumps(gapmap, indent=1, sort_keys=True))
for p in (mp, gp):
    print(p.name, "sha256", hashlib.sha256(p.read_bytes()).hexdigest())
print("first_available:", json.dumps(first_avail))
