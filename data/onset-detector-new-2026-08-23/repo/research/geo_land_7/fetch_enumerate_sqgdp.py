"""B-GEO-LAND-7: fetch + byte-exact verify + enumerate BEA SQGDP.zip.

Route PROVEN by B-GEO-MAP-1948: apps.bea.gov/regional/zip/SQGDP.zip =
3,639,953 B, application/x-zip-compressed, 255 table CSVs. Brief-named table
SQGDP1__ALL_AREAS_2005_2026.csv, quarterly, state GDP, span 2005:Q1..2026.

This step ONLY fetches, verifies byte-exact against the route proof, and
enumerates every TABLE__ALL_AREAS member with the SAME geo classification the
adapter uses (_bea_cainc_geography_type). NO store write. Emits:
research/geo_land_7/SQGDP.zip, route_verify.json, zip_enumeration.json.
"""
import hashlib
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))
from live_data.rmv2_live.adapters import _bea_cainc_geography_type, _BEA_CAINC_META_COLS
import csv

ENDPOINT = "https://apps.bea.gov/regional/zip/SQGDP.zip"
ROUTE_PROOF_BYTES = 3639953  # B-GEO-MAP-1948 measured
OUT = REPO / "research/geo_land_7"


def enumerate_member(text):
    reader = csv.reader(io.StringIO(text, newline=""), skipinitialspace=True)
    header = next(reader, None)
    if not header or header[0] != "GeoFIPS" or header[3] != "TableName":
        raise SystemExit("header not exact: %r" % (header[:4] if header else None))
    period_cols = header[_BEA_CAINC_META_COLS:]
    if period_cols and all(re.match(r"^\d{4}$", p) for p in period_cols):
        freq, span = "annual", (period_cols[0], period_cols[-1])
    elif period_cols and all(re.match(r"^\d{4}:Q[1-4]$", p) for p in period_cols):
        freq, span = "quarterly", (period_cols[0], period_cols[-1])
    else:
        raise SystemExit("period cols malformed: %r" % period_cols[:3])
    ncol = len(header)
    geo_counts = {"national_us": 0, "bea_region": 0, "state_or_dc": 0, "county": 0}
    linecodes = set()
    table_name = None
    for row in reader:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) != ncol:
            continue
        geo_fips = row[0].strip()
        if not re.match(r"^\d{5}$", geo_fips):
            continue
        table_name = row[3].strip()
        line_code = row[4].strip()
        gt = _bea_cainc_geography_type(geo_fips)
        geo_counts[gt] += 1
        linecodes.add(line_code)
    return {
        "table": table_name,
        "freq": freq,
        "span": list(span),
        "periods": len(period_cols),
        "linecodes": len(linecodes),
        "geo_series": geo_counts,
        "series_ex_other_ex_county": geo_counts["national_us"]
        + geo_counts["bea_region"] + geo_counts["state_or_dc"],
        "records_est_state_geo": (geo_counts["national_us"] + geo_counts["bea_region"]
                                  + geo_counts["state_or_dc"]) * len(period_cols),
    }


def main():
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "bristow-hall-rmv2/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        ctype = resp.headers.get("Content-Type")
        body = resp.read()
    n = len(body)
    sha = hashlib.sha256(body).hexdigest()
    byte_exact = (n == ROUTE_PROOF_BYTES)
    (OUT / "SQGDP.zip").write_bytes(body)
    route = {
        "url": ENDPOINT, "http": 200, "content_type": ctype,
        "bytes_measured": n, "bytes_route_proof": ROUTE_PROOF_BYTES,
        "byte_exact_match": byte_exact, "sha256": sha,
    }
    (OUT / "route_verify.json").write_text(json.dumps(route, indent=1))
    print("FETCH bytes=%d route_proof=%d byte_exact=%s ctype=%s sha=%s"
          % (n, ROUTE_PROOF_BYTES, byte_exact, ctype, sha[:12]))
    if not byte_exact:
        print("WARN byte mismatch vs route proof; enumerating anyway for record")

    archive = zipfile.ZipFile(io.BytesIO(body))
    members = [nm for nm in archive.namelist()
               if re.search(r"__ALL_AREAS_\d{4}_\d{4}\.csv$", nm)]
    tables = []
    for nm in sorted(members):
        text = archive.read(nm).decode("latin-1")
        info = enumerate_member(text)
        info["member"] = nm
        tables.append(info)
    total_state_geo = sum(t["series_ex_other_ex_county"] for t in tables)
    enum = {
        "zip": "SQGDP.zip", "bytes": n, "sha256": sha,
        "all_areas_tables": len(tables),
        "total_table_files_in_zip": len(archive.namelist()),
        "tables": tables,
        "state_geo_series_total_all_tables": total_state_geo,
    }
    (OUT / "zip_enumeration.json").write_text(json.dumps(enum, indent=1))
    print("ENUM all_areas_tables=%d total_files=%d state_geo_series_total=%d"
          % (len(tables), len(archive.namelist()), total_state_geo))
    for t in tables:
        print("  %-10s %s %s..%s lc=%d geo(nat/reg/state/cty)=%d/%d/%d/%d"
              % (t["table"], t["freq"], t["span"][0], t["span"][1], t["linecodes"],
                 t["geo_series"]["national_us"], t["geo_series"]["bea_region"],
                 t["geo_series"]["state_or_dc"], t["geo_series"]["county"]))


if __name__ == "__main__":
    main()
