#!/usr/bin/env python3
"""Publisher-direct collection for an isolated Recession Monitor V2 source pack.

This module intentionally does not edit or import the main ``live_data``
service. It emits content-addressed evidence that Main can independently
review and integrate.
"""

from __future__ import absolute_import

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


SCHEMA_NORMALIZED = "recession-monitor-v2.free-official-normalized.v1"
SCHEMA_RECEIPT = "recession-monitor-v2.free-official-evidence-receipt.v1"
SCHEMA_ATTEMPT = "recession-monitor-v2.free-official-retrieval-attempt.v1"
SCHEMA_GENERATION = "recession-monitor-v2.free-official-generation.v1"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
QUARTER_END_RE = re.compile(r"^\d{8}$")
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
SCIENTIFIC_DECIMAL_RE = re.compile(
    r"^-?(?:0|[1-9]\d*)(?:\.\d+)?[eE][+-]?\d+$"
)


class CollectorError(RuntimeError):
    """A source or artifact violated the contributor-pack contract."""


def utc_now():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_bytes(data):
    if not isinstance(data, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value):
    _validate_json_tree(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _validate_json_tree(value, path="$"):
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        raise CollectorError("%s contains a floating-point value" % path)
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_tree(item, "%s[%d]" % (path, index))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CollectorError("%s contains a non-string key" % path)
            _validate_json_tree(item, "%s.%s" % (path, key))
        return
    raise CollectorError("%s contains unsupported type %s" % (path, type(value)))


def strict_json_loads(data):
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CollectorError("JSON is not UTF-8") from exc

    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CollectorError("duplicate JSON key %r" % key)
            result[key] = value
        return result

    try:
        return json.loads(
            data,
            object_pairs_hook=reject_duplicates,
            parse_float=lambda value: value,
            parse_int=lambda value: value,
            parse_constant=lambda value: (_ for _ in ()).throw(
                CollectorError("non-finite JSON value %r" % value)
            ),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, CollectorError):
            raise
        raise CollectorError("invalid JSON: %s" % exc) from exc


def load_registry(path):
    registry = strict_json_loads(Path(path).read_bytes())
    if registry.get("schema_version") != (
        "recession-monitor-v2.free-official-source-registry.v1"
    ):
        raise CollectorError("unexpected source registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise CollectorError("source registry must contain sources")
    ids = [source.get("source_id") for source in sources]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise CollectorError("source IDs must be sorted and unique")
    return registry


def _decimal_or_none(value, field):
    if value in ("", None):
        return None
    value = str(value)
    if DECIMAL_RE.fullmatch(value):
        return value
    if SCIENTIFIC_DECIMAL_RE.fullmatch(value):
        try:
            normalized = format(Decimal(value), "f")
        except InvalidOperation as exc:
            raise CollectorError(
                "%s is not an exact decimal: %r" % (field, value)
            ) from exc
        if not DECIMAL_RE.fullmatch(normalized):
            raise CollectorError(
                "%s did not normalize to a canonical decimal: %r"
                % (field, value)
            )
        return normalized
    raise CollectorError("%s is not a canonical decimal: %r" % (field, value))


def parse_fhfa_hpi_monthly_us(raw):
    expected = [
        "hpi_type",
        "hpi_flavor",
        "frequency",
        "level",
        "place_name",
        "place_id",
        "yr",
        "period",
        "index_nsa",
        "index_sa",
        "rstderr",
        "note",
    ]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CollectorError("FHFA CSV is not UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != expected:
        raise CollectorError("FHFA CSV header changed")
    observations = []
    seen = set()
    for row in reader:
        if (
            row["hpi_type"] != "traditional"
            or row["hpi_flavor"] != "purchase-only"
            or row["frequency"] != "monthly"
            or row["level"] != "USA or Census Division"
            or row["place_name"] != "United States"
            or row["place_id"] != "USA"
        ):
            continue
        year = row["yr"]
        month = row["period"]
        if not re.fullmatch(r"\d{4}", year) or not re.fullmatch(r"\d{1,2}", month):
            raise CollectorError("FHFA observation period is malformed")
        month_number = int(month)
        if not 1 <= month_number <= 12:
            raise CollectorError("FHFA month is outside 1..12")
        period = "%s-%02d" % (year, month_number)
        if period in seen:
            raise CollectorError("duplicate FHFA national monthly period %s" % period)
        seen.add(period)
        nsa = _decimal_or_none(row["index_nsa"], "FHFA index_nsa")
        sa = _decimal_or_none(row["index_sa"], "FHFA index_sa")
        if nsa is None and sa is None:
            raise CollectorError("FHFA row has no index value")
        observations.append(
            {
                "observation_period": period,
                "index_nsa": nsa,
                "index_sa": sa,
                "relative_standard_error": _decimal_or_none(
                    row["rstderr"], "FHFA rstderr"
                ),
                "note": row["note"] or None,
            }
        )
    observations.sort(key=lambda row: row["observation_period"])
    if not observations:
        raise CollectorError("FHFA CSV contained no national monthly purchase-only rows")
    return {
        "series": "traditional_purchase_only_monthly_united_states",
        "units": "index",
        "observations": observations,
    }


def parse_ofr_fsi_daily(raw):
    expected = [
        "Date",
        "OFR FSI",
        "Credit",
        "Equity valuation",
        "Safe assets",
        "Funding",
        "Volatility",
        "United States",
        "Other advanced economies",
        "Emerging markets",
    ]
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CollectorError("OFR CSV is not UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != expected:
        raise CollectorError("OFR FSI CSV header changed")
    mapping = [
        ("OFR FSI", "ofr_fsi"),
        ("Credit", "credit"),
        ("Equity valuation", "equity_valuation"),
        ("Safe assets", "safe_assets"),
        ("Funding", "funding"),
        ("Volatility", "volatility"),
        ("United States", "united_states"),
        ("Other advanced economies", "other_advanced_economies"),
        ("Emerging markets", "emerging_markets"),
    ]
    observations = []
    seen = set()
    for row in reader:
        date = row["Date"]
        if not DATE_RE.fullmatch(date):
            raise CollectorError("OFR FSI date is malformed")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError as exc:
            raise CollectorError("OFR FSI date is not a calendar date") from exc
        if date in seen:
            raise CollectorError("duplicate OFR FSI date %s" % date)
        seen.add(date)
        output = {"observation_period": date}
        for source_field, target_field in mapping:
            output[target_field] = _decimal_or_none(
                row[source_field], "OFR %s" % source_field
            )
        if output["ofr_fsi"] is None:
            raise CollectorError("OFR FSI total is missing")
        observations.append(output)
    observations.sort(key=lambda row: row["observation_period"])
    if not observations:
        raise CollectorError("OFR CSV contained no observations")
    return {
        "series": "ofr_financial_stress_index_and_contributions",
        "units": "index_contribution",
        "observations": observations,
    }


def _integer_string(value, field):
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9]\d*)", value):
        return value
    raise CollectorError("%s is not an integer" % field)


def parse_fdic_quarterly_aggregate(raw):
    payload = strict_json_loads(raw)
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise CollectorError("FDIC response has no data rows")
    observations = []
    seen = set()
    required = [
        "REPDTE",
        "count",
        "sum_ASSET",
        "sum_DEP",
        "sum_LNLSNET",
        "sum_NETINC",
    ]
    for wrapper in rows:
        if not isinstance(wrapper, dict) or not isinstance(wrapper.get("data"), dict):
            raise CollectorError("FDIC aggregate row has wrong shape")
        row = wrapper["data"]
        if set(row) != set(required):
            raise CollectorError("FDIC aggregate fields changed")
        raw_date = row["REPDTE"]
        if not isinstance(raw_date, str) or not QUARTER_END_RE.fullmatch(raw_date):
            raise CollectorError("FDIC report date is malformed")
        try:
            parsed_date = datetime.strptime(raw_date, "%Y%m%d")
        except ValueError as exc:
            raise CollectorError("FDIC report date is not a calendar date") from exc
        if parsed_date.month not in (3, 6, 9, 12):
            raise CollectorError("FDIC report date is not a quarter end")
        date = parsed_date.strftime("%Y-%m-%d")
        if date in seen:
            raise CollectorError("duplicate FDIC report date %s" % date)
        seen.add(date)
        observations.append(
            {
                "observation_period": date,
                "institution_count": _integer_string(row["count"], "FDIC count"),
                "assets_thousand_usd": _integer_string(
                    row["sum_ASSET"], "FDIC sum_ASSET"
                ),
                "deposits_thousand_usd": _integer_string(
                    row["sum_DEP"], "FDIC sum_DEP"
                ),
                "net_loans_leases_thousand_usd": _integer_string(
                    row["sum_LNLSNET"], "FDIC sum_LNLSNET"
                ),
                "net_income_ytd_thousand_usd": _integer_string(
                    row["sum_NETINC"], "FDIC sum_NETINC"
                ),
            }
        )
    observations.sort(key=lambda row: row["observation_period"])
    return {
        "series": "fdic_reporting_institutions_quarterly_aggregate",
        "units": "thousand_usd_except_count",
        "observations": observations,
    }


PARSERS = {
    "fdic_quarterly_aggregate_v1": parse_fdic_quarterly_aggregate,
    "fhfa_hpi_monthly_us_v1": parse_fhfa_hpi_monthly_us,
    "ofr_fsi_daily_v1": parse_ofr_fsi_daily,
}


def fetch_source(source):
    endpoint = source["endpoint"]
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or parsed.hostname not in source["allowed_hosts"]:
        raise CollectorError("source endpoint is outside its HTTPS host allowlist")
    request = Request(
        endpoint,
        headers={
            "Accept": ", ".join(source["expected_content_types"]),
            "User-Agent": "RecessionMonitorV2-FreeOfficialContributor/1.0",
        },
    )
    with urlopen(request, timeout=45) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname not in source["allowed_hosts"]:
            raise CollectorError("source redirect left the HTTPS host allowlist")
        if response.getcode() != 200:
            raise CollectorError("publisher returned HTTP %s" % response.getcode())
        content_type = response.headers.get("Content-Type", "")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type not in source["expected_content_types"]:
            raise CollectorError("publisher content type changed: %r" % content_type)
        raw = response.read(int(source["max_bytes"]) + 1)
        if len(raw) > int(source["max_bytes"]):
            raise CollectorError("publisher response exceeded max_bytes")
        if not raw:
            raise CollectorError("publisher response is empty")
        headers = {
            "content_type": content_type,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
    return raw, headers


def normalize(source, raw):
    parser_name = source["parser"]
    if parser_name not in PARSERS:
        raise CollectorError("unknown parser %s" % parser_name)
    body = PARSERS[parser_name](raw)
    observations = body["observations"]
    return {
        "schema_version": SCHEMA_NORMALIZED,
        "source_id": source["source_id"],
        "publisher": source["publisher"],
        "endpoint": source["endpoint"],
        "parser_version": parser_name,
        "native_frequency": source["native_frequency"],
        "information_set_mode": source["information_set_mode"],
        "value_status": "published_current_revised",
        "scientific_admission": False,
        "series": body["series"],
        "units": body["units"],
        "observation_count": len(observations),
        "first_observation_period": observations[0]["observation_period"],
        "latest_observation_period": observations[-1]["observation_period"],
        "observations": observations,
    }


def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, str(path))
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _write_if_absent_or_equal(path, data):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise CollectorError("immutable path collision: %s" % path)
        return
    _atomic_write(path, data)


def collect_one(source, output_root, retrieved_at=None):
    retrieved_at = retrieved_at or utc_now()
    raw, headers = fetch_source(source)
    normalized = normalize(source, raw)
    normalized_bytes = canonical_json_bytes(normalized)
    raw_sha = sha256_bytes(raw)
    normalized_sha = sha256_bytes(normalized_bytes)
    evidence = {
        "schema_version": SCHEMA_RECEIPT,
        "source_id": source["source_id"],
        "endpoint": source["endpoint"],
        "parser_version": source["parser"],
        "information_set_mode": source["information_set_mode"],
        "native_frequency": source["native_frequency"],
        "raw_sha256": raw_sha,
        "normalized_sha256": normalized_sha,
        "observation_count": normalized["observation_count"],
        "first_observation_period": normalized["first_observation_period"],
        "latest_observation_period": normalized["latest_observation_period"],
        "etag": headers["etag"],
        "last_modified": headers["last_modified"],
        "rights": source["rights"],
        "scientific_admission": False,
    }
    evidence_bytes = canonical_json_bytes(evidence)
    evidence_sha = sha256_bytes(evidence_bytes)
    attempt = {
        "schema_version": SCHEMA_ATTEMPT,
        "source_id": source["source_id"],
        "retrieved_at": retrieved_at,
        "content_type": headers["content_type"],
        "raw_bytes": len(raw),
        "evidence_receipt_sha256": evidence_sha,
    }
    attempt_bytes = canonical_json_bytes(attempt)
    attempt_sha = sha256_bytes(attempt_bytes)
    root = Path(output_root)
    _write_if_absent_or_equal(root / "raw" / source["source_id"] / (raw_sha + ".bin"), raw)
    _write_if_absent_or_equal(
        root / "normalized" / source["source_id"] / (normalized_sha + ".json"),
        normalized_bytes,
    )
    _write_if_absent_or_equal(
        root / "receipts" / source["source_id"] / (evidence_sha + ".json"),
        evidence_bytes,
    )
    _write_if_absent_or_equal(
        root / "attempts" / source["source_id"] / (attempt_sha + ".json"),
        attempt_bytes,
    )
    latest = {
        "source_id": source["source_id"],
        "evidence_receipt_sha256": evidence_sha,
        "attempt_sha256": attempt_sha,
    }
    _atomic_write(
        root / "latest" / (source["source_id"] + ".json"),
        canonical_json_bytes(latest),
    )
    return {
        "source_id": source["source_id"],
        "evidence_receipt_sha256": evidence_sha,
        "attempt_sha256": attempt_sha,
        "raw_sha256": raw_sha,
        "normalized_sha256": normalized_sha,
        "observation_count": normalized["observation_count"],
        "latest_observation_period": normalized["latest_observation_period"],
    }


def collect_all(registry_path, output_root):
    registry = load_registry(registry_path)
    retrieved_at = utc_now()
    members = [
        collect_one(source, output_root, retrieved_at=retrieved_at)
        for source in registry["sources"]
    ]
    core = {
        "schema_version": SCHEMA_GENERATION,
        "source_ids": [member["source_id"] for member in members],
        "members": [
            {
                "source_id": member["source_id"],
                "evidence_receipt_sha256": member["evidence_receipt_sha256"],
            }
            for member in members
        ],
    }
    generation_id = sha256_bytes(canonical_json_bytes(core))
    manifest = dict(core)
    manifest["generation_id"] = generation_id
    manifest["retrieved_at"] = retrieved_at
    manifest["status"] = "CONTRIBUTOR_EVIDENCE_NOT_SCIENTIFICALLY_ADMITTED"
    manifest_bytes = canonical_json_bytes(manifest)
    root = Path(output_root)
    _write_if_absent_or_equal(
        root / "generations" / (generation_id + ".json"), manifest_bytes
    )
    _atomic_write(
        root / "latest_generation.json",
        canonical_json_bytes(
            {
                "generation_id": generation_id,
                "manifest_sha256": sha256_bytes(manifest_bytes),
            }
        ),
    )
    return manifest


def verify_output(registry_path, output_root):
    registry = load_registry(registry_path)
    root = Path(output_root)
    pointer = strict_json_loads((root / "latest_generation.json").read_bytes())
    generation_id = pointer.get("generation_id")
    manifest_path = root / "generations" / (generation_id + ".json")
    manifest_bytes = manifest_path.read_bytes()
    if sha256_bytes(manifest_bytes) != pointer.get("manifest_sha256"):
        raise CollectorError("generation manifest hash mismatch")
    manifest = strict_json_loads(manifest_bytes)
    if manifest.get("generation_id") != generation_id:
        raise CollectorError("generation ID mismatch")
    expected_ids = [source["source_id"] for source in registry["sources"]]
    if manifest.get("source_ids") != expected_ids:
        raise CollectorError("generation source exact set/order mismatch")
    members = manifest.get("members")
    if not isinstance(members, list) or len(members) != len(expected_ids):
        raise CollectorError("generation member count mismatch")
    for member in members:
        source_id = member["source_id"]
        receipt_sha = member["evidence_receipt_sha256"]
        receipt_path = root / "receipts" / source_id / (receipt_sha + ".json")
        receipt_bytes = receipt_path.read_bytes()
        if sha256_bytes(receipt_bytes) != receipt_sha:
            raise CollectorError("evidence receipt hash mismatch for %s" % source_id)
        receipt = strict_json_loads(receipt_bytes)
        raw_path = root / "raw" / source_id / (receipt["raw_sha256"] + ".bin")
        normalized_path = (
            root
            / "normalized"
            / source_id
            / (receipt["normalized_sha256"] + ".json")
        )
        if sha256_bytes(raw_path.read_bytes()) != receipt["raw_sha256"]:
            raise CollectorError("raw hash mismatch for %s" % source_id)
        normalized_bytes = normalized_path.read_bytes()
        if sha256_bytes(normalized_bytes) != receipt["normalized_sha256"]:
            raise CollectorError("normalized hash mismatch for %s" % source_id)
        normalized = strict_json_loads(normalized_bytes)
        if normalized["observation_count"] != receipt["observation_count"]:
            raise CollectorError("observation count mismatch for %s" % source_id)
        latest = strict_json_loads(
            (root / "latest" / (source_id + ".json")).read_bytes()
        )
        if latest["evidence_receipt_sha256"] != receipt_sha:
            raise CollectorError("latest pointer mismatch for %s" % source_id)
    return {
        "generation_id": generation_id,
        "source_count": len(expected_ids),
        "status": "VERIFIED_CONTRIBUTOR_EVIDENCE_NOT_SCIENTIFICALLY_ADMITTED",
    }


def main(argv=None):
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation", choices=("collect", "verify"), help="operation to perform"
    )
    parser.add_argument(
        "--registry", default=str(base / "source_registry.v1.json")
    )
    parser.add_argument("--output", default=str(base / "snapshots"))
    args = parser.parse_args(argv)
    if args.operation == "collect":
        result = collect_all(args.registry, args.output)
    else:
        result = verify_output(args.registry, args.output)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
