"""Analyze mounted Recession Monitor V2 catalogs and legacy data views.

The output is descriptive and operational. It does not admit a dataset to a
scientific model, alter chronology, or reinterpret missing first-release proof
as missing economic data.
"""
from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .gap_registry import build_registry, summarize_registry

ANALYSIS_SCHEMA = "recession-monitor-v2.uploaded-evidence-analysis.v1"


@dataclasses.dataclass(frozen=True)
class InputResolution:
    path: Path
    identical_duplicate_count: int
    duplicate_paths: Tuple[str, ...]
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_input(root: Path, canonical_name: str) -> InputResolution:
    """Resolve one canonical upload and refuse divergent numbered duplicates."""
    root = Path(root).resolve()
    canonical = root / canonical_name
    name_path = Path(canonical_name)
    pattern = re.compile(
        r"^%s\(\d+\)%s$" % (re.escape(name_path.stem), re.escape(name_path.suffix))
    )
    candidates = []
    if canonical.is_file():
        candidates.append(canonical)
    candidates.extend(sorted(
        path for path in root.iterdir()
        if path.is_file() and pattern.match(path.name)
    ))
    if not candidates:
        raise FileNotFoundError("required input is missing: %s" % canonical_name)
    hashes = {_sha256(path) for path in candidates}
    if len(hashes) != 1:
        raise ValueError("conflicting duplicate uploads for %s" % canonical_name)
    selected = canonical if canonical in candidates else candidates[0]
    duplicates = tuple(str(path.name) for path in candidates if path != selected)
    return InputResolution(selected, len(duplicates), duplicates, next(iter(hashes)))


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _integer(value: Any) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def _json_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _counter(rows: Iterable[Mapping[str, Any]], field: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "") for row in rows).items()))


def _optional_resolution(root: Path, name: str) -> Optional[InputResolution]:
    try:
        return resolve_input(root, name)
    except FileNotFoundError:
        return None


def _coverage_count(data: Mapping[str, Any], key: str) -> int:
    return sum(1 for row in data.values() if isinstance(row, Mapping) and key in row)


def _analyze_geography(root: Path, resolutions: Dict[str, InputResolution]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    county_econ = _read_json(resolutions["county_econ.json"].path)
    county_data = county_econ.get("data") or {}
    result["county_econ"] = {
        "county_count": len(county_data),
        "coverage": {key: _coverage_count(county_data, key) for key in ("hpi", "pcpi", "gdp", "mhi", "poverty")},
    }

    county_hist = _read_json(resolutions["county_hist.json"].path)
    years = county_hist.get("years") or []
    result["county_hist"] = {
        "annual_counties": len(county_hist.get("annual") or {}),
        "monthly_counties": len(county_hist.get("monthly") or {}),
        "labor_force_monthly_counties": len(county_hist.get("lfm") or {}),
        "year_count": len(years),
        "first_year": years[0] if years else None,
        "last_year": years[-1] if years else None,
        "monthly_key_count": len(county_hist.get("mkeys") or []),
        "preliminary_record_count": len(county_hist.get("prelim") or {}),
    }

    county_industry = _read_json(resolutions["county_industry.json"].path)
    industry_years = county_industry.get("years") or []
    result["county_industry"] = {
        "county_count": len(county_industry.get("data") or {}),
        "sector_count": len(county_industry.get("sectors") or []),
        "first_year": industry_years[0] if industry_years else None,
        "last_year": industry_years[-1] if industry_years else None,
    }

    qcew = _read_json(resolutions["county_qcew.json"].path)
    qtrs = qcew.get("qtrs") or []
    result["county_qcew"] = {
        "county_count": len(qcew.get("data") or {}),
        "quarter_count": len(qtrs),
        "first_quarter": qtrs[0] if qtrs else None,
        "last_quarter": qtrs[-1] if qtrs else None,
    }

    industry_geo = _read_json(resolutions["industry_geo.json"].path)
    result["industry_geo"] = {
        "state_area_count": len(industry_geo.get("states") or {}),
        "metro_area_count": len(industry_geo.get("metros") or {}),
        "sector_count": len(industry_geo.get("sectors") or []),
        "first_month": industry_geo.get("m0"),
    }

    metro_econ = _read_json(resolutions["metro_econ.json"].path)
    metro_econ_data = metro_econ.get("metros") or {}
    result["metro_econ"] = {
        "record_count": len(metro_econ_data),
        "hpi_record_count": _coverage_count(metro_econ_data, "hpi"),
        "gdp_record_count": _coverage_count(metro_econ_data, "gdp"),
    }

    metros = _read_json(resolutions["metros.json"].path)
    result["metros"] = {
        "metro_count": len(metros.get("metros") or {}),
        "missing_count": len(metros.get("missing") or []),
        "capital_mapping_count": len(metros.get("capitals") or {}),
    }

    state_econ = _read_json(resolutions["state_econ.json"].path)
    result["state_econ"] = {"state_or_dc_count": len(state_econ.get("states") or {})}

    state_metrics = _read_json(resolutions["state_metrics.json"].path)
    months = state_metrics.get("months") or []
    result["state_metrics"] = {
        "state_count": len(state_metrics.get("states") or {}),
        "metric_count": len(state_metrics.get("meta") or []),
        "month_count": len(months),
        "first_month": months[0] if months else None,
        "last_month": months[-1] if months else None,
    }
    return result


def _analyze_predlog(path: Path) -> Dict[str, Any]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError("invalid predlog JSON at line %d" % line_number) from exc
    contiguous = all(row.get("seq") == index for index, row in enumerate(rows))
    linked = contiguous
    for index, row in enumerate(rows):
        expected = "0" * 64 if index == 0 else rows[index - 1].get("hash")
        if row.get("prev") != expected:
            linked = False
    return {
        "record_count": len(rows),
        "first_as_of": rows[0].get("as_of") if rows else None,
        "last_as_of": rows[-1].get("as_of") if rows else None,
        "contiguous_sequence": contiguous,
        "linked_chain": linked,
        "hash_format_valid": all(
            isinstance(row.get("hash"), str) and re.fullmatch(r"[0-9a-f]{64}", row.get("hash") or "")
            for row in rows
        ),
        "note": "Linkage and hash format are checked; scientific payload values are not revalidated by this data-layer audit.",
    }


def _reported_readme_counts(root: Path) -> Dict[str, Any]:
    # README(1).md is a distinct uploaded document (the data-vault README), not
    # necessarily a duplicate of the live-service README. Read the exact canonical
    # name here rather than applying numbered-duplicate identity rules.
    path = Path(root) / "README.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "active_routes_reported": r"There are\s+(\d+)\s+enabled acquisition routes",
        "registered_families_reported": r"registry contains\s+(\d+)\s+source-family records",
        "reserved_routes_reported": r"(\d+)\s+(?:additional,\s+)?disabled collector identities",
    }
    result: Dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = int(match.group(1))
    return result


def analyze_evidence(
    input_root: Path,
    generated_at: Optional[str] = None,
    include_strict_realtime: bool = True,
) -> Dict[str, Any]:
    input_root = Path(input_root).resolve()
    generated_at = generated_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    required = (
        "metric_catalog.csv", "local_series_inventory.csv", "dataset_catalog.csv", "external_source_registry.csv",
        "county_econ.json", "county_hist.json", "county_industry.json", "county_qcew.json",
        "industry_geo.json", "metro_econ.json", "metros.json", "state_econ.json", "state_metrics.json", "predlog.jsonl",
    )
    resolutions = {name: resolve_input(input_root, name) for name in required}
    metrics = _read_csv(resolutions["metric_catalog.csv"].path)
    locals_ = _read_csv(resolutions["local_series_inventory.csv"].path)
    datasets = _read_csv(resolutions["dataset_catalog.csv"].path)
    externals = _read_csv(resolutions["external_source_registry.csv"].path)

    planned_resolution = _optional_resolution(input_root, "planned_sources.v1.json")
    planned_rows = None
    if planned_resolution:
        planned_document = _read_json(planned_resolution.path)
        if isinstance(planned_document, list):
            planned_rows = planned_document
        elif isinstance(planned_document, Mapping):
            planned_rows = next((planned_document.get(key) for key in ("sources", "planned_sources", "rows") if isinstance(planned_document.get(key), list)), None)

    registry = build_registry(
        metrics, locals_, datasets, externals,
        include_strict_realtime=include_strict_realtime,
        include_known_reservations=planned_rows is None,
        planned_rows=planned_rows,
    )
    storage = {
        "dataset_family_count": len(datasets),
        "file_count": sum(_integer(row.get("file_count")) for row in datasets),
        "byte_count": sum(_integer(row.get("byte_count")) for row in datasets),
        "parsed_row_count": sum(_integer(row.get("parsed_row_count")) for row in datasets),
    }
    parse_sets = [set(str(value).lower() for value in _json_list(row.get("parse_statuses_json"))) for row in metrics]
    malformed_count = sum(any("html" in value or "parse_error" in value or "nonadmissible" in value for value in statuses) for statuses in parse_sets)
    duplicate_count = sum(resolution.identical_duplicate_count for resolution in resolutions.values())

    holdings = {
        "storage": storage,
        "catalogs": {
            "represented_series": len(metrics),
            "local_series_rows": len(locals_),
            "external_source_families": len(externals),
            "dataset_families": len(datasets),
            "access_classes": _counter(externals, "access_class"),
        },
        "metric_profile": {
            "categories": _counter(metrics, "category"),
            "publishers": _counter(metrics, "publisher"),
            "frequencies": _counter(metrics, "observation_frequency"),
            "coverage_1950": _counter(metrics, "local_1950_coverage_status"),
            "revision_classes": _counter(metrics, "revision_class"),
            "rights_statuses": _counter(metrics, "rights_status"),
            "named_vintage_statuses": _counter(metrics, "named_vintage_local_status"),
            "strict_first_release_statuses": _counter(metrics, "strict_first_release_local_status"),
        },
    }

    report = {
        "schema_version": ANALYSIS_SCHEMA,
        "generated_at": generated_at,
        "policy": {
            "publisher_first_release_required_for_data_acquisition": False,
            "publisher_first_release_required_for_strict_historical_realtime_claims": True,
            "scientific_model_admission_granted": False,
            "bhi2_modified": False,
        },
        "holdings": holdings,
        "quality": {
            "malformed_payload_series": malformed_count,
            "unknown_coverage_series": sum(row.get("local_1950_coverage_status") == "unknown_unparsed" for row in metrics),
            "unresolved_frequency_series": sum(row.get("observation_frequency") in ("", "unknown", "unresolved") for row in metrics),
            "unresolved_publisher_series": sum(row.get("publisher") in ("", "unknown", "unresolved") for row in metrics),
            "unclassified_series": sum(row.get("category") in ("", "unclassified_quantitative") for row in metrics),
            "identical_duplicate_uploads_ignored": duplicate_count,
        },
        "geography": _analyze_geography(input_root, resolutions),
        "forecast_ledger": _analyze_predlog(resolutions["predlog.jsonl"].path),
        "gap_summary": summarize_registry(registry),
        "gap_registry": registry,
        "acquisition_scope": {
            "complete_planned_source_registry_available": planned_rows is not None,
            "known_named_reservations_used": planned_rows is None,
            "known_named_reservation_count": 0 if planned_rows is not None else 4,
            "limitation": (
                "The complete production planned_sources.v1.json was not among the mounted uploads; "
                "the acquisition queue therefore includes catalog-derived repair items and four explicitly documented reservations only."
                if planned_rows is None else "The mounted planned-source registry was used."
            ),
        },
        "runtime_reported_state": _reported_readme_counts(input_root),
        "inputs": {
            name: {
                "selected": resolution.path.name,
                "sha256": resolution.sha256,
                "identical_duplicates_ignored": list(resolution.duplicate_paths),
            }
            for name, resolution in sorted(resolutions.items())
        },
        "next_actions": [
            "Repair and re-fetch the 17 HTML/nonadmissible series before expanding ordinary acquisition.",
            "Load the complete planned-source registry from the live project to replace the four-reservation fallback queue.",
            "Activate reviewed official EIA-930 and DOL claims-release archive recipes first.",
            "Resolve public-export rights before adding any source to a Cloudflare generation.",
            "Keep strict first-release work in a separate optional historical-validation lane.",
        ],
    }
    return report


def write_gap_csv(registry: Mapping[str, Any], path: Path) -> None:
    fields = [
        "gap_id", "priority", "gap_class", "gap_type", "entity_type", "entity_id",
        "data_missing", "automatable", "status", "blockers", "evidence", "recommended_action", "source_url",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in registry.get("items") or []:
            row = dict(item)
            row["blockers"] = "|".join(item.get("blockers") or [])
            writer.writerow({field: row.get(field, "") for field in fields})


def _number(value: Any) -> str:
    return format(int(value), ",") if isinstance(value, (int, float)) else html.escape(str(value))


def render_html(report: Mapping[str, Any]) -> str:
    holdings = report["holdings"]
    storage = holdings["storage"]
    catalogs = holdings["catalogs"]
    quality = report["quality"]
    gap = report["gap_summary"]
    geography = report["geography"]
    items = list(report["gap_registry"].get("items") or [])
    priority_items = [item for item in items if item.get("data_missing") or item.get("priority") in ("P0", "P1")][:100]

    def row(label: str, value: Any) -> str:
        return "<tr><th>%s</th><td>%s</td></tr>" % (html.escape(label), _number(value))

    queue_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            html.escape(str(item["priority"])), html.escape(str(item["gap_class"])),
            html.escape(str(item["entity_id"])), html.escape(str(item["gap_type"])),
            html.escape(str(item["recommended_action"])),
        ) for item in priority_items
    )
    county = geography["county_econ"]
    actions = "".join("<li>%s</li>" % html.escape(value) for value in report["next_actions"])
    limitation = html.escape(report["acquisition_scope"]["limitation"])
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recession Monitor V2 Data Holdings and Gap Audit</title>
<style>
:root{color-scheme:light dark;--bg:#f5f7fa;--card:#fff;--text:#152033;--muted:#596579;--line:#d8dee8;--accent:#244a8f;--warn:#8b3e00} @media(prefers-color-scheme:dark){:root{--bg:#0e1420;--card:#151d2b;--text:#eef3fb;--muted:#aab5c6;--line:#344055;--accent:#82aaff;--warn:#ffb066}}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1180px;margin:auto;padding:36px 22px 72px}h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.05;margin:.1em 0 .35em}h2{margin-top:2.2em;border-bottom:1px solid var(--line);padding-bottom:.3em}.lede{font-size:1.15rem;max-width:900px;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:24px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 6px 20px rgba(0,0,0,.05)}.metric{font-size:2rem;font-weight:750}.label{color:var(--muted)}table{width:100%%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}th{font-weight:650}.scroll{overflow:auto;border-radius:12px}.note{border-left:4px solid var(--warn);padding:12px 16px;background:var(--card)}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}footer{margin-top:42px;color:var(--muted);font-size:.9rem}
</style></head><body><main>
<h1>Recession Monitor V2 Data Holdings and Gap Audit</h1>
<p class="lede"><strong>The system already holds a substantial data foundation.</strong> The immediate priorities are repairing malformed payloads, loading the complete planned-source queue, activating the highest-value official feeds, and publishing only rights-cleared immutable data generations. Missing publisher-first-release proof is tracked separately and is not counted as missing economic data.</p>
<div class="grid">
<div class="card"><div class="metric">%s</div><div class="label">checksum-governed files cataloged</div></div>
<div class="card"><div class="metric">%s</div><div class="label">bytes cataloged</div></div>
<div class="card"><div class="metric">%s</div><div class="label">stored parsed rows</div></div>
<div class="card"><div class="metric">%s</div><div class="label">represented series</div></div>
<div class="card"><div class="metric">%s</div><div class="label">external source families researched</div></div>
<div class="card"><div class="metric">%s</div><div class="label">malformed/HTML payload series requiring repair</div></div>
</div>
<h2>Executive findings</h2>
<ul><li><strong>%s missing-data/repair conditions across %s affected entities</strong> are in the current fallback queue; capability and metadata gaps are counted separately.</li><li><strong>%s gap items are automatable</strong>; %s remain blocked by rights, credentials, or historical-release evidence.</li><li>The geographic layer includes %s county economic records and %s metros.</li><li>The forecast ledger contains %s linked records from %s through %s; this audit checks linkage, not the scientific values.</li></ul>
<div class="note"><strong>Scope limitation.</strong> %s</div>
<h2>Catalog and quality profile</h2><div class="grid">
<div class="card"><table>%s%s%s%s</table></div>
<div class="card"><table>%s%s%s%s</table></div>
</div>
<h2>Geographic holdings</h2><div class="scroll"><table><thead><tr><th>Layer</th><th>Coverage</th></tr></thead><tbody>
<tr><td>County economic</td><td>%s counties; HPI %s; personal income %s; GDP %s; median income %s; poverty %s</td></tr>
<tr><td>County unemployment history</td><td>%s counties; %s–%s annual history</td></tr>
<tr><td>County industry</td><td>%s counties; %s sectors</td></tr>
<tr><td>County QCEW</td><td>%s counties; %s quarters</td></tr>
<tr><td>State metrics</td><td>%s states; %s metrics; %s months (%s–%s)</td></tr>
<tr><td>Metros</td><td>%s metro records; %s unresolved</td></tr>
</tbody></table></div>
<h2>Priority acquisition and remediation queue</h2><p>The table shows the first 100 P0/P1 or true data-gap items. The complete queue is in <code>data_gap_registry.json</code> and <code>data_gap_summary.csv</code>.</p><div class="scroll"><table><thead><tr><th>Priority</th><th>Class</th><th>Entity</th><th>Gap</th><th>Action</th></tr></thead><tbody>%s</tbody></table></div>
<h2>Recommended next actions</h2><ol>%s</ol>
<h2>Governance boundary</h2><p>This artifact grants no scientific-model admission, changes no chronology, and does not modify BHI2. Public Cloudflare generations must use an explicit rights allowlist and must be uploaded generation-first with the active pointer switched last.</p>
<footer>Generated %s from mounted Recession Monitor V2 catalogs and legacy geographic outputs. Exact input hashes are retained in <code>data_holdings_summary.json</code>.</footer>
</main></body></html>""" % (
        _number(storage["file_count"]), _number(storage["byte_count"]), _number(storage["parsed_row_count"]),
        _number(catalogs["represented_series"]), _number(catalogs["external_source_families"]), _number(quality["malformed_payload_series"]),
        _number(gap["data_missing_count"]), _number(gap["data_missing_entity_count"]), _number(gap["automatable_count"]), _number(gap["blocked_count"]),
        _number(county["county_count"]), _number(geography["metros"]["metro_count"]),
        _number(report["forecast_ledger"]["record_count"]), html.escape(str(report["forecast_ledger"]["first_as_of"])), html.escape(str(report["forecast_ledger"]["last_as_of"])), limitation,
        row("Dataset families", storage["dataset_family_count"]), row("Metric series", catalogs["represented_series"]), row("External families", catalogs["external_source_families"]), row("Identical duplicate uploads ignored", quality["identical_duplicate_uploads_ignored"]),
        row("Unknown coverage", quality["unknown_coverage_series"]), row("Unresolved frequency", quality["unresolved_frequency_series"]), row("Unresolved publisher", quality["unresolved_publisher_series"]), row("Unclassified series", quality["unclassified_series"]),
        _number(county["county_count"]), _number(county["coverage"]["hpi"]), _number(county["coverage"]["pcpi"]), _number(county["coverage"]["gdp"]), _number(county["coverage"]["mhi"]), _number(county["coverage"]["poverty"]),
        _number(geography["county_hist"]["annual_counties"]), geography["county_hist"]["first_year"], geography["county_hist"]["last_year"],
        _number(geography["county_industry"]["county_count"]), _number(geography["county_industry"]["sector_count"]),
        _number(geography["county_qcew"]["county_count"]), _number(geography["county_qcew"]["quarter_count"]),
        _number(geography["state_metrics"]["state_count"]), _number(geography["state_metrics"]["metric_count"]), _number(geography["state_metrics"]["month_count"]), html.escape(str(geography["state_metrics"]["first_month"])), html.escape(str(geography["state_metrics"]["last_month"])),
        _number(geography["metros"]["metro_count"]), _number(geography["metros"]["missing_count"]), queue_rows, actions, html.escape(str(report["generated_at"])),
    )


def write_artifacts(report: Mapping[str, Any], output_root: Path) -> Dict[str, str]:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    paths = {
        "holdings": output_root / "data_holdings_summary.json",
        "registry": output_root / "data_gap_registry.json",
        "csv": output_root / "data_gap_summary.csv",
        "html": output_root / "data_gap_report.html",
    }
    paths["holdings"].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["registry"].write_text(json.dumps(report["gap_registry"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_gap_csv(report["gap_registry"], paths["csv"])
    paths["html"].write_text(render_html(report), encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}
