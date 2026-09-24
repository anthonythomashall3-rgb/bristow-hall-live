"""B-REG-FORECAST-PDFS-R2 — land FOMC SEP projection-table comparators, offline, ZERO network.

Lands ONLY the SEP compilation documents whose Table 1 passes the strict anti-fabrication
validators in rmv2_live.forecast_sep_pdf (all-or-nothing per document). Every other document
in the CH-R119 dated index is recorded as a FAILURE with a reason string (brief: never a
silent skip). Each landed document is bound as its OWN offline-current source (raw PDF bytes
preserved) under the registered family fomc_sep, mode substituted_diagnostic, enabled:false +
archival:true. Knowledge (meeting-end) date is encoded in each series id and forecast_origin.
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
from rmv2_live import forecast_sep_pdf as sep_mod

ROOT = Path(".").resolve()
CFG_PATH = ROOT / "live_data/config/sources.v1.json"
INDEX = json.load(open("research/forecast_pdfs/pdf_dated_index.v1.json"))
SEP_MAN = json.load(open("research/prefetch/forecasts/fomc_sep/MANIFEST.sha256.json"))
FETCH_UTC = "2026-08-06T05:20Z"    # SEP prefetch MANIFEST.generated_utc (measured)
AS_OF = "2026-08-08T00:00:00Z"
FAMILY = "fomc_sep"
SEP_PAGE = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

FIREWALL = ("FOMC SEP participant projections: LABELED substituted_diagnostic comparator, "
            "family fomc_sep; participant views, NOT staff/official forecast; NEVER a member, "
            "never fitted, never an NBER recession-LABEL product (CLAUDE.md forecast firewall; "
            "§22.4). B-REG-FORECAST-PDFS-R2.")

# manifest sha index (basename -> row) to attest bytes before binding
_SEP_SHA = {row["path"].split("/")[-1]: row for row in SEP_MAN["files"]}


def _source(base, meeting_date, outputs):
    sid = "fomc_sep_compilation_%s_offline" % meeting_date.replace("-", "")
    return {
        "adapter": "forecast_sep_pdf",
        "allowed_hosts": ["www.federalreserve.gov"],
        "archival": True,
        "coverage_source_ids": [FAMILY],
        "enabled": False,
        "endpoint": "%s#%s" % (SEP_PAGE, base),
        "expected_content_types": ["application/pdf", "application/octet-stream"],
        "frequency": "event_driven",
        "information_set_mode": "substituted_diagnostic",
        "label": ("FOMC Summary of Economic Projections Table 1 (Central tendency + Range), "
                  "meeting %s [OFFLINE-CURRENT frozen comparator; CH-R119 cache; %s]"
                  % (meeting_date, FIREWALL)),
        "max_bytes": 16777216,
        "method_version": "forecast_sep_pdf_offline.v1",
        "poll_seconds": 86400,
        "publisher": "Federal Reserve Board",
        "publisher_release_clock": ("SEP released with the FOMC statement at 2:00 p.m. ET on "
                                    "the meeting's final day; offline-current frozen snapshot "
                                    "keyed by the meeting-end knowledge date"),
        "rights_status": "Board_public_domain_with_caveats",
        "secret_env": None,
        "secret_required": False,
        "series": {"forecast_shape": "fomc_sep", "meeting_date": meeting_date,
                   "outputs": outputs},
        "source_id": sid,
        "value_status": "actual",
    }


def _manifest(body, base):
    sha = hashlib.sha256(body).hexdigest()
    row = _SEP_SHA.get(base)
    if row is None:
        raise SystemExit("NO SEP manifest row for %s" % base)
    if sha != row["sha256"] or len(body) != row["bytes"]:
        raise SystemExit("SEP CACHE MISMATCH %s" % base)
    return {"fetch_utc": FETCH_UTC, "source_bytes_length": len(body),
            "source_sha256": sha, "url": "%s#%s" % (SEP_PAGE, base)}


def build():
    comps = sorted([r for r in INDEX if r["base"].endswith("SEPcompilation.pdf")],
                   key=lambda r: r["meeting_or_doc_date"])
    plan, ledger = [], []
    for r in comps:
        body = Path(r["path"]).read_bytes()
        res = sep_mod.parse_sep_compilation(body, r["meeting_or_doc_date"])
        if res["ok"]:
            outputs = [{"series_id": t[0]} for t in
                       sep_mod.sep_records(r["meeting_or_doc_date"], res["cells"])]
            src = _source(r["base"], r["meeting_or_doc_date"], outputs)
            plan.append((src, body, _manifest(body, r["base"])))
            ledger.append({"base": r["base"], "date": r["meeting_or_doc_date"],
                           "class": "forecast_fomc_sep", "landed": True,
                           "n_vars": res["n_vars"], "years": res["years"]})
        else:
            ledger.append({"base": r["base"], "date": r["meeting_or_doc_date"],
                           "class": "forecast_fomc_sep", "landed": False,
                           "reason": "sep_table_not_extractable:%s" % res["reason"]})
    # §19.4 NO SILENT CAPS — classify EVERY remaining index row with a specific reason.
    def other_reason(base, cls):
        if cls == "forecast_livingston":
            return ("livingston_not_landed: pre-2000 image-only (no text layer) OR modern "
                    "bare-number table without a delimiter — not safely text-extractable "
                    "without a positional layout parser (follow-up)")
        if cls in ("documentation_fredmd", "documentation_nfci"):
            return "documentation_pdf_not_data"
        # forecast_fomc_sep non-compilation variants
        if base.endswith("SEPkey.pdf"):
            return "sep_key_legend_not_data"
        if "tealbook" in base.lower():
            return ("tealbook_staff_document_not_sep_participant_projection; different "
                    "instrument (Fed staff Tealbook/Greenbook), overlaps B-ACQ-GREENBOOK; "
                    "mis-classed as fomc_sep in CH-R119 index; NOT landed under fomc_sep")
        if base.startswith("fomcprojtabl"):
            return ("modern_sep_projection_table_rendered_as_vector_figures; numeric Table 1 "
                    "not present in the PDF text layer (only axis labels/captions) — not "
                    "safely text-extractable without a positional/graphics parser (follow-up)")
        return "not_a_landable_sep_projection_table"

    seen = {(x["base"], x.get("date")) for x in ledger}
    for r in INDEX:
        key = (r["base"], r.get("meeting_or_doc_date"))
        if key in seen:
            continue
        ledger.append({"base": r["base"], "date": r.get("meeting_or_doc_date"),
                       "class": r["cls"], "landed": False,
                       "reason": other_reason(r["base"], r["cls"])})
    return plan, ledger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    plan, ledger = build()
    cfg = load_config(CFG_PATH)
    existing = {s["source_id"] for s in cfg["sources"]}
    for src, _b, _m in plan:
        if src["source_id"] in existing:
            raise SystemExit("COLLISION: %s already in config" % src["source_id"])

    pipeline = RefreshPipeline(ROOT, cfg)
    pipeline.store.initialize()

    running = dict(cfg)
    running["sources"] = list(cfg["sources"])
    report = {}
    all_series = set()
    for src, body, _m in plan:
        feed_factory._validate_source_candidate(ROOT, running, src)
        recs = normalize(src, body, AS_OF)
        sids = sorted({r["series_id"] for r in recs})
        declared = sorted({o["series_id"] for o in src["series"]["outputs"]})
        if sids != declared:
            raise SystemExit("ID DRIFT %s: emitted!=declared" % src["source_id"])
        dup = all_series.intersection(sids)
        if dup:
            raise SystemExit("SERIES COLLISION across docs: %r" % sorted(dup)[:5])
        all_series.update(sids)
        periods = sorted({r["observation_period"] for r in recs})
        report[src["source_id"]] = {"records": len(recs), "n_series": len(sids),
                                    "periods": periods}
        running["sources"] = list(running["sources"]) + [src]
    landed_docs = len(plan)
    failed = [x for x in ledger if not x["landed"]]
    print("GATE PASS %d SEP docs, %d distinct series, %d records; %d recorded failures"
          % (landed_docs, len(all_series),
             sum(v["records"] for v in report.values()), len(failed)))

    summary = {"n_docs_landed": landed_docs, "n_series": len(all_series),
               "n_records": sum(v["records"] for v in report.values()),
               "n_failures_recorded": len(failed), "report": report, "ledger": ledger}
    if a.dry:
        json.dump(summary, open("research/BREG_FORECAST_R2_plan.json", "w"),
                  indent=1, sort_keys=True)
        print("DRY: gated + parsed, no writes.")
        return

    bound = {}
    for src, body, manifest in plan:
        oc = bind_offline_current(pipeline, src, body, manifest, AS_OF)
        bound[src["source_id"]] = {"records": oc["record_count"],
                                   "receipt": oc["receipt_sha256"],
                                   "latest": oc["latest_observation_period"],
                                   "source_bytes_sha256": oc["source_bytes_sha256"]}
        print("BOUND", src["source_id"], oc["record_count"], oc["receipt_sha256"][:12])

    raw = json.load(open(CFG_PATH))
    raw["sources"] = list(raw["sources"]) + [src for src, _b, _m in plan]
    tmp = str(CFG_PATH) + ".tmp"
    json.dump(raw, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CFG_PATH)
    print("CONFIG written; n_sources", len(raw["sources"]))

    ids = [src["source_id"] for src, _b, _m in plan]
    cfg2 = load_config(CFG_PATH)
    pipe2 = RefreshPipeline(ROOT, cfg2)
    result = pipe2.refresh(source_ids=ids, due_only=False)
    outcomes = result.get("outcomes") if isinstance(result, dict) else None
    pointer = result.get("pointer") if isinstance(result, dict) else None
    print("TARGETED REFRESH outcomes:", json.dumps(outcomes))
    print("POINTER generation:", (pointer or {}).get("generation_sha256", "<none>"))
    summary["bound"] = bound
    summary["refresh"] = {"outcomes": outcomes, "pointer": pointer}
    json.dump(summary, open("research/BREG_FORECAST_R2_land_out.json", "w"),
              indent=1, default=str, sort_keys=True)


main()
