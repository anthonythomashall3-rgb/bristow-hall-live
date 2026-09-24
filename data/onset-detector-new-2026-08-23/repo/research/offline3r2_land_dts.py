"""B-OFFLINE-3-R2 item 2 — land the Treasury DTS Table-I "Operating Cash Balance"
merged body as ONE offline-current lane (10 clean literal series), per director
rulings 20260806T084233Z (A=Option 2 single-manifest receipt + committed 17-page
sidecar; B=Option 1 ten clean series, SPLICE NOTHING) and 20260806T153123Z
(per-sub_table value column: legacy 'Type of account' -> close_today_bal, post-2022
'Cash Balance Details' -> open_today_bal; 4 binding conditions).

Zero network. The BOUND body is the deterministic MERGED body (16,498 rows, all
table_nbr='I') built by merge_operating_cash_pages + serialize_merged_body; its
sha256 is the bound-object sha and attests every page's content. The 17 individual
page manifests go in a COMMITTED sidecar under live_data/ because the offline-current
receipt field set is an exact frozenset that could not be extended without breaking
the already-landed WEI / GDPNow / B-OFFLINE-2 receipts (Option 2).

Bound to the already-registered `treasury_dts` family (access A, diagnostic_candidate)
-- no new family, no owner family admission. enabled:false + archival:true. Converge
via a TARGETED refresh of THIS disabled source only (never a full refresh).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "live_data")
from rmv2_live.config import load_config
from rmv2_live.pipeline import RefreshPipeline
from rmv2_live import feed_factory
from rmv2_live.adapters import normalize
from rmv2_live.offline_binding import bind_offline_current
from rmv2_live.treasury_dts_operating_cash import (
    merge_operating_cash_pages,
    serialize_merged_body,
)

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
CACHE_DIR = ROOT / "research/prefetch/dts"
MANIFEST = CACHE_DIR / "_manifest.jsonl"
SIDECAR = ROOT / "live_data/provenance/treasury_dts_operating_cash_pages.v1.json"
SOURCE_ID = "treasury_dts_operating_cash_current"
ENDPOINT = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
            "v1/accounting/dts/operating_cash_balance")
UNIT = "USD millions"
AS_OF = "2026-08-06T15:31:00Z"

_LEGACY_NOTE = (
    "Treasury DTS Table I Operating Cash Balance, %r line (legacy 'Type of account' "
    "structure). Value from close_today_bal, the daily closing-balance column as "
    "published before the 2022-04-18 restructure. Own DTS_OCB_* id; NOT aliased or "
    "spliced to any other line -- the Federal Reserve Account -> Treasury General "
    "Account rename/split is an account-identity question that stays owner territory "
    "and is unmade here. Frozen archival offline-current evidence.")
_MODERN_NOTE = (
    "Treasury DTS Table I Operating Cash Balance, %r line (post-2022-04-18 'Cash "
    "Balance Details' structure). Value from open_today_bal: in the restructure this "
    "line reports its single figure in open_today_bal while close_today_bal is "
    "literally 'null' on all of its rows; the column was selected by measurement "
    "over the cached corpus, not by judgment. The 2022-04-18 boundary is a "
    "FEED-STRUCTURE change, explicitly distinct from the still-open account-identity "
    "question. Own DTS_OCB_* id; not spliced. Frozen archival offline-current "
    "evidence.")

# (series_id, account_type, value_field). Legacy 6 -> close_today_bal; modern 4 ->
# open_today_bal. The adapter enforces value_field against the row's sub_table_name.
_MEMBER_SPEC = [
    ("DTS_OCB_FEDERAL_RESERVE_ACCOUNT", "Federal Reserve Account", "close_today_bal"),
    ("DTS_OCB_SUPPLEMENTARY_FINANCING_PROGRAM_ACCOUNT",
     "Supplementary Financing Program Account", "close_today_bal"),
    ("DTS_OCB_SHORT_TERM_CASH_INVESTMENTS",
     "Short-Term Cash Investments (Table V)", "close_today_bal"),
    ("DTS_OCB_TAX_AND_LOAN_NOTE_ACCOUNTS",
     "Tax and Loan Note Accounts (Table V)", "close_today_bal"),
    ("DTS_OCB_FINANCIAL_INSTITUTION_ACCOUNT",
     "Financial Institution Account", "close_today_bal"),
    ("DTS_OCB_TGA", "Treasury General Account (TGA)", "close_today_bal"),
    ("DTS_OCB_TGA_OPENING_BALANCE",
     "Treasury General Account (TGA) Opening Balance", "open_today_bal"),
    ("DTS_OCB_TGA_TOTAL_DEPOSITS", "Total TGA Deposits (Table II)", "open_today_bal"),
    ("DTS_OCB_TGA_TOTAL_WITHDRAWALS",
     "Total TGA Withdrawals (Table II) (-)", "open_today_bal"),
    ("DTS_OCB_TGA_CLOSING_BALANCE",
     "Treasury General Account (TGA) Closing Balance", "open_today_bal"),
]

# The 6 truncation / field-shift variants the ruling says to enumerate (never merge)
# -- recorded in the sidecar with counts and the fixed-field-width measurement.
_TRUNCATION_VARIANTS = [
    {"account_type": "Supplementary Financing Program", "rows": 849,
     "kind": "prefix", "width": 31,
     "canonical_guess": "Supplementary Financing Program Account",
     "note": "31-char prefix of the canonical account; NOT the 28-char fixed width "
             "of the two clear truncations, and 'Supplementary Financing Program' "
             "is also the real program name -- genuinely ambiguous, owner call."},
    {"account_type": "Supplementary Financing Prog", "rows": 229,
     "kind": "fixed_width_truncation", "width": 28,
     "canonical_guess": "Supplementary Financing Program Account",
     "note": "exactly canonical[:28] -- clean 28-char fixed-width truncation."},
    {"account_type": "Supplementary Financing Programs", "rows": 1,
     "kind": "trailing_s_typo", "width": 32,
     "canonical_guess": "Supplementary Financing Program Account",
     "note": "trailing 's' variant; NOT a prefix truncation of any canonical."},
    {"account_type": "Financial Institution Accoun", "rows": 164,
     "kind": "fixed_width_truncation", "width": 28,
     "canonical_guess": "Financial Institution Account",
     "note": "exactly canonical[:28] -- clean 28-char fixed-width truncation."},
    {"account_type": "Account Tax and Loan Note Accounts (Table V)", "rows": 84,
     "kind": "leading_account_field_shift", "width": 44,
     "canonical_guess": "Tax and Loan Note Accounts (Table V)",
     "note": "leading 'Account ' prefix; strip it -> exact canonical. Field-shift "
             "of the sub_table label into the value, not a truncation."},
    {"account_type": "Account Short-Term Cash Investments (Table V)", "rows": 64,
     "kind": "leading_account_field_shift", "width": 45,
     "canonical_guess": "Short-Term Cash Investments (Table V)",
     "note": "leading 'Account ' prefix; strip it -> exact canonical. Field-shift, "
             "not a truncation."},
]
_FIELD_WIDTH_FINDING = (
    "Fixed-field-width measurement (director's cheap test before escalation): two of "
    "the six variants ('Supplementary Financing Prog', 'Financial Institution "
    "Accoun') are each EXACTLY their canonical string truncated at 28 characters -- a "
    "constant-width feed artifact. Two more ('Account Tax and Loan Note Accounts "
    "(Table V)', 'Account Short-Term Cash Investments (Table V)') are a leading "
    "'Account ' field-shift that yields the exact canonical when the prefix is "
    "stripped. The remaining two ('Supplementary Financing Program' len 31, "
    "'Supplementary Financing Programs' len 32 trailing-s) are NOT explained by a "
    "single constant width and 'Supplementary Financing Program' is also the real "
    "program name -- those two remain a genuine merge/identity question for the owner. "
    "None are merged here.")


def _members():
    members = []
    for series_id, account_type, value_field in _MEMBER_SPEC:
        note = (_LEGACY_NOTE if value_field == "close_today_bal" else _MODERN_NOTE)
        members.append({
            "series_id": series_id,
            "account_type": account_type,
            "value_field": value_field,
            "label": note % account_type,
        })
    return members


def _source():
    return {
        "adapter": "treasury_dts_operating_cash",
        "allowed_hosts": ["api.fiscaldata.treasury.gov"],
        "archival": True,
        "coverage_source_ids": ["treasury_dts"],
        "enabled": False,
        "endpoint": ENDPOINT,
        "expected_content_types": ["application/json", "text/json"],
        "frequency": "daily",
        "information_set_mode": "current_revised",
        "label": (
            "Treasury Daily Treasury Statement Table I Operating Cash Balance "
            "(10 clean account lines, merged 17-page body) [OFFLINE-CURRENT flat "
            "lane; per-sub_table value column; own DTS_OCB_* ids, no splice; "
            "B-OFFLINE-3-R2]"
        ),
        "max_bytes": 12000000,
        "method_version": "treasury_dts_operating_cash_offline.v1",
        "poll_seconds": 86400,
        "publisher": "U.S. Department of the Treasury, Bureau of the Fiscal Service",
        "publisher_release_clock": (
            "Daily Treasury Statement released each business day ~16:00 "
            "America/New_York; Table I Operating Cash Balance"
        ),
        "rights_status": "public_government_source_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "index_label": "Treasury DTS Table I Operating Cash Balance",
            "unit": UNIT,
            "members": _members(),
        },
        "source_id": SOURCE_ID,
        "value_status": "actual",
    }


def _load_pages_and_manifests():
    manifests = [json.loads(l) for l in open(MANIFEST) if l.strip()]
    if len(manifests) != 17:
        raise SystemExit("expected 17 page manifests, got %d" % len(manifests))
    pages = []
    page_provenance = []
    for i in range(1, 18):
        path = CACHE_DIR / ("operating_cash_balance_p%03d.json" % i)
        body = path.read_bytes()
        sha = hashlib.sha256(body).hexdigest()
        rec = manifests[i - 1]
        # manifest sha/length guard at bind
        if sha != rec["sha256"]:
            raise SystemExit("PAGE %d SHA MISMATCH: %s vs %s" % (i, sha, rec["sha256"]))
        if len(body) != rec["bytes"]:
            raise SystemExit("PAGE %d LENGTH MISMATCH" % i)
        pages.append(json.loads(body))
        page_provenance.append({
            "page": i,
            "file": path.name,
            "url": rec["url"],
            "fetch_utc": rec["fetch_utc"],
            "sha256": sha,
            "bytes": rec["bytes"],
        })
    return pages, page_provenance, manifests


def _write_sidecar(page_provenance, merged_sha, merged_len):
    SIDECAR.parent.mkdir(parents=True, exist_ok=True)
    sidecar = {
        "schema_version": "recession-monitor-v2.dts-operating-cash-page-provenance.v1",
        "batch": "B-OFFLINE-3-R2_DTS_TABLE_I",
        "bound_source_id": SOURCE_ID,
        "bound_merged_sha256": merged_sha,
        "bound_merged_bytes": merged_len,
        "endpoint": ENDPOINT,
        "why_this_file_exists": (
            "This committed sidecar carries all 17 DTS page manifests (url + "
            "fetch_utc + sha256 + bytes each) because the offline-current receipt "
            "field set is an EXACT frozenset that could not be extended to hold 17 "
            "page shas without breaking re-verification of the already-landed WEI / "
            "GDPNow / B-OFFLINE-2 receipts. Director ruling 20260806T084233Z relaxed "
            "the 'receipt cites all 17' condition to Option 2: the bound merged "
            "sha256 attests every page's content (the merged body contains every "
            "row), and this sidecar records the per-page provenance. Chain: receipt "
            "-> merged sha -> this sidecar -> 17 page shas -> cache manifest. "
            "DTS may be re-bound under a proper merged receipt once B-OFFLINE-6's "
            "offline_current_merged_cache schema lands; this Option-2 landing is "
            "archival/additive, so re-binding later is clean."
        ),
        "pages": page_provenance,
        "truncation_variants_not_landed": _TRUNCATION_VARIANTS,
        "truncation_field_width_finding": _FIELD_WIDTH_FINDING,
        "account_identity_note": (
            "Federal Reserve Account -> Treasury General Account (TGA) -> TGA Closing "
            "Balance is a three-segment identity claim across two renames and a "
            "structural split; SPLICED NOTHING. Each of the 10 clean lines lands "
            "under its own DTS_OCB_* id. Owner territory, filed for follow-up."
        ),
    }
    tmp = str(SIDECAR) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(sidecar, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, SIDECAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    pages, page_provenance, _ = _load_pages_and_manifests()
    merged = merge_operating_cash_pages(pages)
    body = serialize_merged_body(merged)
    merged_sha = hashlib.sha256(body).hexdigest()
    merged_len = len(body)
    print("MERGED rows=%d sha=%s len=%d" % (merged["row_count"], merged_sha[:16], merged_len))

    # Option-2 single manifest: url = shared endpoint, fetch_utc = latest page
    # fetch, sha/length = merged body.
    latest_fetch = max(p["fetch_utc"] for p in page_provenance)
    manifest = {
        "fetch_utc": latest_fetch,
        "source_bytes_length": merged_len,
        "source_sha256": merged_sha,
        "url": ENDPOINT,
    }

    src = _source()
    cfg = load_config(CFG_PATH)
    if SOURCE_ID in {s["source_id"] for s in cfg["sources"]}:
        raise SystemExit("COLLISION: %s already in config" % SOURCE_ID)
    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()
    # clobber-proof: append-only family + registry-binding gate BEFORE any write.
    feed_factory._validate_source_candidate(ROOT, cfg, src)
    recs = normalize(src, body, AS_OF)
    by_series = {}
    unavailable = 0
    for r in recs:
        by_series[r["series_id"]] = by_series.get(r["series_id"], 0) + 1
        if r.get("value_status") == "unavailable":
            unavailable += 1
    print("GATE PASS. records=%d series=%d unavailable=%d"
          % (len(recs), len(by_series), unavailable))
    print("series counts:", json.dumps(by_series, sort_keys=True))
    plan = {"records": len(recs), "series": len(by_series),
            "unavailable": unavailable, "series_counts": by_series,
            "merged_sha256": merged_sha, "merged_bytes": merged_len}
    json.dump(plan, open("research/OFFLINE3R2_land_plan.json", "w"), indent=1)
    if a.dry:
        print("DRY: gated + parsed, no writes")
        return

    # committed sidecar first (pure provenance, no store risk)
    _write_sidecar(page_provenance, merged_sha, merged_len)
    print("SIDECAR written", SIDECAR)

    oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
    print("BOUND", oc["outcome"], "records", oc["record_count"],
          "receipt", oc["receipt_sha256"][:12])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))

    # TARGETED zero-network refresh of THIS disabled source only -> republish
    # generation + write operational_status in the same step.
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=[SOURCE_ID], due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    json.dump({"bound": oc, "refresh": {"outcomes": outcomes, "pointer": pointer},
               "merged_sha256": merged_sha, "merged_bytes": merged_len},
              open("research/OFFLINE3R2_land_out.json", "w"), indent=1, default=str)


main()
