"""Deterministic, fixture-backed onboarding for the existing live-data spine."""

from __future__ import absolute_import

import csv
import io
import json
import os
import re
import secrets
import stat
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .adapters import PublisherHttpClient, normalize, validate_response
from .canonical import (
    CanonicalDataError,
    atomic_write,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
    utc_now,
)
from .config import load_config
from .store import safe_regular_file


SPEC_SCHEMA = "recession-monitor-v2.feed-onboarding-spec.v1"
RECEIPT_SCHEMA = "recession-monitor-v2.feed-onboarding-receipt.v1"
BUNDLE_SCHEMA = "recession-monitor-v2.feed-onboarding-bundle.v3"
DISCOVERY_SCHEMA = "recession-monitor-v2.feed-discovery-spec.v1"
SPEC_FIELDS = frozenset((
    "activation",
    "expected_normalization",
    "fixture",
    "reservation",
    "schema_version",
    "source",
))
ACTIVATION_FIELDS = frozenset(("scientific_effect", "website_effect"))
EXPECTED_FIELDS = frozenset((
    "first_observation_period",
    "last_observation_period",
    "record_count",
    "series_ids",
    "units",
    "value_statuses",
))
FIXTURE_FIELDS = frozenset((
    "bytes",
    "path",
    "retrieved_at",
    "sha256",
))
RESERVATION_FIELDS = frozenset(("action", "source_id"))
RECEIPT_FIELDS = frozenset((
    "candidate_config_sha256",
    "candidate_planned_sha256",
    "fixture_bytes",
    "fixture_sha256",
    "normalized_sha256",
    "predecessor_config_sha256",
    "predecessor_planned_sha256",
    "record_count",
    "schema_version",
    "scientific_effect",
    "series_ids",
    "source_id",
    "spec_sha256",
    "status",
    "website_effect",
))
NORMALIZED_FIELDS = frozenset((
    "parser_id",
    "records",
    "retrieved_at",
    "schema_version",
    "source_bytes_sha256",
    "source_id",
))
PLANNED_SOURCE_FIELD_ORDER = (
    "source_id",
    "registry_status",
    "enabled",
    "publisher",
    "endpoint",
    "endpoint_status",
    "auth_env",
    "cadence",
    "release_timezone",
    "release_clock",
    "observation_period",
    "revision_policy",
    "rights",
    "parser_version",
    "role",
    "clock_notes",
    "split_or_bias_guard",
    "coverage_source_family_ids",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
)
AI_HOST_TOKENS = ("anthropic", "chatgpt", "claude", "gemini", "openai")
RAW_MEMBER_RE = re.compile(r"^fixture\.raw\.([0-9a-f]{64})\.bin$")
EXPLICIT_OUTPUT_ID_ADAPTERS = frozenset((
    # ATSIX InfExp lands a fixed 4-horizon slice; each series_id is declared in
    # the member map (static ATSIX_INFEXP* ids), so the exact output identity is
    # the collected member ids (B-ACQ-REALTIME-EXPECTATIONS item 4).
    "atsix_termstructure_xlsx",
    "bea_api",
    "bls_json",
    "census_api",
    "dallas_wei_xlsx",
    # B-ACQ-AGGREGATORS: dbnomics_json configures exactly one member whose
    # series_id is the complete, static output identity (the adapter refuses any
    # doc whose provider/dataset/series triple disagrees with that member), so the
    # exact output id set is the collected member id.
    "dbnomics_json",
    "dol_ui_weekly_claims_report_html",
    "eia_v2_json",
    "fiscaldata_json",
    "forecast_sep_pdf",
    "fred_graph_csv",
    "fred_json_api",
    "greenbook_row_xlsx",
    "nber_macrohistory_dat",
    "philadelphia_ads_xlsx",
    "regional_survey_xlsx",
    "socrata_json",
    "tabular_csv",
    # B-OFFLINE-3-R2: the 10 clean DTS operating-cash lines are declared
    # explicitly in the member map (each a static DTS_OCB_* series_id), unlike
    # the data-derived FRED/SPF lanes, so the exact output identity is the
    # collected member ids.
    "treasury_dts_operating_cash",
))
LIVE_POINTER_FIELDS = frozenset((
    "coverage_sha256",
    "generation_sha256",
    "manifest_sha256",
    "schema_version",
    "snapshot_sha256",
    "status_sha256",
    "updated_at",
))
LIVE_GENERATION_MEMBERS = frozenset((
    "coverage.json",
    "snapshot.json",
    "status.json",
))


def _require_exact_keys(value, fields, context):
    if not isinstance(value, dict):
        raise CanonicalDataError("%s must be an object" % context)
    missing = sorted(fields - frozenset(value))
    extra = sorted(frozenset(value) - fields)
    if missing or extra:
        raise CanonicalDataError(
            "%s key mismatch; missing=%r extra=%r" %
            (context, missing, extra)
        )


def _unique_sorted_strings(value, context, allow_empty=False):
    if (
        not isinstance(value, list) or
        (not value and not allow_empty) or
        any(not isinstance(item, str) or not item for item in value)
    ):
        raise CanonicalDataError("%s must be a nonempty string list" % context)
    if len(value) != len(set(value)):
        raise CanonicalDataError("%s contains duplicates" % context)
    if value != sorted(value):
        raise CanonicalDataError("%s must be lexicographically sorted" % context)
    return value


def _package_json_bytes(value):
    """Serialize JSON without disturbing identity-bearing package field order."""
    canonical_json_bytes(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _project_file(project_root, relative_path):
    project_root = Path(project_root).resolve()
    if not isinstance(relative_path, str) or not relative_path:
        raise CanonicalDataError("fixture path is invalid")
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise CanonicalDataError("fixture path must be project-relative")
    expected_root = (project_root / "live_data" / "feed_factory").resolve()
    candidate = (project_root / path).absolute()
    try:
        candidate.relative_to(expected_root)
    except ValueError:
        raise CanonicalDataError(
            "fixture must be inside live_data/feed_factory"
        )
    return candidate, safe_regular_file(candidate, expected_root)


def _read_spec_bytes(project_root, spec_path):
    project_root = Path(project_root).resolve()
    recipe_root = (
        project_root / "live_data" / "feed_factory" / "recipes"
    ).resolve()
    raw_path = Path(spec_path).absolute()
    path = raw_path.parent.resolve() / raw_path.name
    return path, safe_regular_file(path, recipe_root)


def _read_draft_bytes(project_root, draft_path):
    project_root = Path(project_root).resolve()
    draft_root = (
        project_root / "live_data" / "feed_factory" / "drafts"
    ).resolve()
    raw_path = Path(draft_path).absolute()
    path = raw_path.parent.resolve() / raw_path.name
    return path, safe_regular_file(path, draft_root)


def _validate_onboarding_spec(spec):
    _require_exact_keys(spec, SPEC_FIELDS, "onboarding spec")
    if spec["schema_version"] != SPEC_SCHEMA:
        raise CanonicalDataError("unsupported onboarding spec schema")
    _require_exact_keys(
        spec["activation"],
        ACTIVATION_FIELDS,
        "activation",
    )
    if spec["activation"]["scientific_effect"] != "none":
        raise CanonicalDataError(
            "feed onboarding cannot authorize scientific effect"
        )
    if (
        spec["activation"]["website_effect"] !=
        "measurement_catalog_and_status_only"
    ):
        raise CanonicalDataError("unsupported website effect")

    _require_exact_keys(
        spec["expected_normalization"],
        EXPECTED_FIELDS,
        "expected_normalization",
    )
    expected = spec["expected_normalization"]
    if (
        not isinstance(expected["record_count"], int) or
        expected["record_count"] < 1
    ):
        raise CanonicalDataError("expected record_count is invalid")
    _unique_sorted_strings(expected["series_ids"], "expected series_ids")
    _unique_sorted_strings(expected["units"], "expected units")
    _unique_sorted_strings(
        expected["value_statuses"],
        "expected value_statuses",
    )
    for name in ("first_observation_period", "last_observation_period"):
        if not isinstance(expected[name], str) or not expected[name]:
            raise CanonicalDataError("%s is invalid" % name)
    if expected["first_observation_period"] > expected["last_observation_period"]:
        raise CanonicalDataError("expected observation range is reversed")

    _require_exact_keys(spec["fixture"], FIXTURE_FIELDS, "fixture")
    fixture = spec["fixture"]
    if not isinstance(fixture["bytes"], int) or fixture["bytes"] < 1:
        raise CanonicalDataError("fixture byte count is invalid")
    if (
        not isinstance(fixture["sha256"], str) or
        not SHA256_RE.match(fixture["sha256"])
    ):
        raise CanonicalDataError("fixture SHA-256 is invalid")
    if (
        not isinstance(fixture["retrieved_at"], str) or
        not TIMESTAMP_RE.match(fixture["retrieved_at"])
    ):
        raise CanonicalDataError("fixture retrieved_at is invalid")

    _require_exact_keys(
        spec["reservation"],
        RESERVATION_FIELDS,
        "reservation",
    )
    action = spec["reservation"]["action"]
    reservation_id = spec["reservation"]["source_id"]
    if action not in ("none", "remove_exact", "retain_exact"):
        raise CanonicalDataError("reservation action is invalid")
    if action == "none":
        if reservation_id is not None:
            raise CanonicalDataError(
                "reservation source_id must be null for action none"
            )
    elif not isinstance(reservation_id, str) or not reservation_id:
        raise CanonicalDataError(
            "reservation source_id is required for this action"
        )
    if not isinstance(spec["source"], dict):
        raise CanonicalDataError("source is invalid")
    return spec


def load_onboarding_spec(project_root, spec_path):
    """Read one strict recipe without performing network or live-store writes."""
    _, data = _read_spec_bytes(project_root, spec_path)
    return _validate_onboarding_spec(strict_json_loads(data))


def _load_discovery_spec(project_root, draft_path):
    _, data = _read_draft_bytes(project_root, draft_path)
    draft = strict_json_loads(data)
    _require_exact_keys(
        draft,
        frozenset((
            "activation",
            "reservation",
            "schema_version",
            "source",
        )),
        "discovery spec",
    )
    if draft["schema_version"] != DISCOVERY_SCHEMA:
        raise CanonicalDataError("unsupported discovery spec schema")
    _require_exact_keys(
        draft["activation"],
        ACTIVATION_FIELDS,
        "activation",
    )
    if (
        draft["activation"].get("scientific_effect") != "none" or
        draft["activation"].get("website_effect") !=
        "measurement_catalog_and_status_only"
    ):
        raise CanonicalDataError("discovery activation boundary is invalid")
    _require_exact_keys(
        draft["reservation"],
        RESERVATION_FIELDS,
        "reservation",
    )
    action = draft["reservation"]["action"]
    reservation_id = draft["reservation"]["source_id"]
    if action not in ("none", "remove_exact", "retain_exact"):
        raise CanonicalDataError("discovery reservation action is invalid")
    if action == "none" and reservation_id is not None:
        raise CanonicalDataError(
            "discovery reservation source_id must be null"
        )
    if (
        action != "none" and
        (not isinstance(reservation_id, str) or not reservation_id)
    ):
        raise CanonicalDataError(
            "discovery reservation source_id is required"
        )
    return draft


def _registry_rows(project_root):
    path = (
        Path(project_root) / "data_vault" / "catalog" /
        "external_source_registry.csv"
    )
    data = safe_regular_file(
        path,
        Path(project_root) / "data_vault" / "catalog",
    )
    with io.StringIO(
        data.decode("utf-8", errors="strict"),
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    by_id = {}
    for row in rows:
        source_id = row.get("source_id")
        if not source_id or source_id in by_id:
            raise CanonicalDataError("source registry identity is invalid")
        by_id[source_id] = row
    return by_id


def _ensure_safe_output_directory(path, allowed_root):
    """Create a directory tree while rejecting linked/special ancestors."""
    path = Path(path).absolute()
    allowed_root = Path(allowed_root).absolute()
    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        raise CanonicalDataError("feed-factory output escaped its root")
    if any(part in ("", ".", "..") for part in relative.parts):
        raise CanonicalDataError("feed-factory output path is invalid")
    current = allowed_root
    try:
        root_info = current.lstat()
    except OSError as exc:
        raise CanonicalDataError(
            "feed-factory output root is unavailable"
        ) from exc
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise CanonicalDataError("feed-factory output root is unsafe")
    for part in relative.parts:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            try:
                current.mkdir(mode=0o755)
            except OSError as exc:
                raise CanonicalDataError(
                    "feed-factory output directory cannot be created"
                ) from exc
            info = current.lstat()
        except OSError as exc:
            raise CanonicalDataError(
                "feed-factory output directory is unavailable"
            ) from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise CanonicalDataError(
                "feed-factory output ancestor is unsafe"
            )
    return path


def _write_immutable(path, data, allowed_root, mode=0o444):
    """Publish a new file atomically without replacing any existing identity."""
    path = Path(path).absolute()
    parent = _ensure_safe_output_directory(path.parent, allowed_root)
    temp = parent / (".%s.%s.tmp" % (path.name, secrets.token_hex(8)))
    descriptor = None
    try:
        descriptor = os.open(
            str(temp),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL |
            getattr(os, "O_NOFOLLOW", 0),
            mode,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(str(temp), str(path), follow_symlinks=False)
        except FileExistsError as exc:
            raise CanonicalDataError(
                "immutable feed-factory output already exists"
            ) from exc
        os.unlink(str(temp))
        try:
            directory_fd = os.open(str(parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            warnings.warn(
                "feed-factory directory fsync unavailable: %s" % exc,
                RuntimeWarning,
            )
    except OSError as exc:
        raise CanonicalDataError(
            "immutable feed-factory output cannot be written"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temp.unlink()
        except FileNotFoundError:
            temp = None


def _validate_family_bindings(project_root, source):
    registry = _registry_rows(project_root)
    family_ids = source.get("coverage_source_ids")
    if not isinstance(family_ids, list) or not family_ids:
        raise CanonicalDataError("source coverage_source_ids are invalid")
    for family_id in family_ids:
        row = registry.get(family_id)
        if row is None:
            raise CanonicalDataError(
                "source family is absent from the registry: %s" % family_id
            )
        if (
            row.get("access_class") in ("C", "D") or
            row.get("role") in ("licensed_only", "target_quarantine")
        ):
            raise CanonicalDataError(
                "source family is blocked or target-quarantined: %s" %
                family_id
            )


def _collect_series_ids(value):
    result = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "series_id" and isinstance(item, str) and item:
                result.add(item)
            result.update(_collect_series_ids(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_collect_series_ids(item))
    return result


FRED_VINTAGE_APPROVED_BASES = frozenset((
    "CMRMTSPL",
    "GACDFSA066MSFRBPHI",
    "GDPC1",
    "HOUST",
    "ICSA",
    "INDPRO",
    "IURSA",
    "NFCI",
    "PAYEMS",
    "PERMIT",
    "SAHMREALTIME",
    "TCU",
    "UMCSENT",
    "UNRATE",
    "W875RX1",
    # B-LAND-3C-R2, owner ruling 2026-08-05 (Option 4, strict): the two FRED-MD
    # panel constructs land under their OWN distinct ids, NEAR IDENTITY class.
    # They are NOT ALFRED-canonical bases and are NEVER aliased onto ICSA /
    # CMRMTSPL; their NEAR identity is carried by coverage_source_ids =
    # fred_md_official_panels (registry NEAR family), not by this allowlist. The
    # allowlist only gates which bases may carry a .DEEPASOF vintage lane at all.
    "CLAIMSx",     # FRED-MD spliced initial-claims construct (NEAR of ICSA)
    "CMRMTSPLx",   # FRED-MD spliced real mfg & trade sales construct (NEAR of CMRMTSPL)
    # B-LAND-4-R2, owner ruling 2026-08-06 (Option 2, own-base): the Philadelphia
    # Fed Real-Time Data Set unemployment-rate construct lands under its OWN id
    # RTDSM_RUC (NEAR/research class), NEVER aliased onto UNRATE, per the standing
    # CLAIMSx/CMRMTSPLx precedent (IPT/IPM->INDPRO 2-to-1 makes aliasing
    # mechanically impossible; own-base is the roster-wide ruling). Its NEAR
    # relation to UNRATE is research, carried by coverage_source_ids =
    # philadelphia_rtdsm (registry family), not by an alias.
    # (answers/20260805T232615Z_B-LAND-4_RTDSM.md)
    "RTDSM_RUC",   # Philadelphia Fed RTDSM real-time unemployment rate (own-base)
    # B-LAND-10-R2, owner ruling 2026-08-06 (Option 2, DEPTH/replay acquisition):
    # tranche A1 (cpi/m1/m2) lands under its OWN ids RTDSM_CPI / RTDSM_M1 /
    # RTDSM_M2, NEVER aliased to CPIAUCSL / M1SL / M2SL, per the RTDSM_RUC
    # own-base precedent. This is a real-time DEPTH acquisition, NOT a channel-
    # diversity claim (CH-R58 measured RTDSM's diversity payoff as collinear with
    # the already-covered output factor). NEAR relation carried by
    # coverage_source_ids = philadelphia_rtdsm, never by an alias.
    # (answers/20260806T120326Z_B-LAND-10_RTDSM_ROLLOUT_T1.md)
    "RTDSM_CPI",   # Philadelphia Fed RTDSM real-time CPI (own-base)
    "RTDSM_M1",    # Philadelphia Fed RTDSM real-time money stock M1 (own-base)
    "RTDSM_M2",    # Philadelphia Fed RTDSM real-time money stock M2 (own-base)
    # B-RTDSM-ROLL TRANCHE A2: CH-R103 lane decision of record (IDENTITY=0,
    # grid-disjoint -> land RTDSM own-base, never dual-land ALFRED) + director
    # batch B-RTDSM-ROLL_TRANCHE_A2 (gated on CH-R103 COMPLETE in DONE.md).
    # +5 RTDSM NEAR-deeper constructs land under their OWN ids per the
    # roster-wide own-base ruling (L534), NEVER aliased onto
    # PCEC96/DSPIC96/PSAVERT/CUMFNS. DEPTH/replay acquisition, delegated
    # reversible acquisition decision under the 2026-08-08 delegation ruling
    # (not §22.2 universe closure, not a rights/product/§22.4 change; NEAR
    # relation carried by coverage_source_ids=philadelphia_rtdsm, never an alias).
    # CH-R103 measured these as the RTDSM-deeper NEAR pairs not landed in A1/ruc.
    "RTDSM_RCON",     # RTDSM real real personal consumption (near of PCEC96)
    "RTDSM_NDPI",     # RTDSM nominal disposable personal income (near of DSPIC96)
    "RTDSM_NPSAV",    # RTDSM nominal personal saving (near of PSAVERT concept)
    "RTDSM_RATESAV",  # RTDSM personal saving rate (near of PSAVERT)
    "RTDSM_CUM",      # RTDSM capacity utilization, manufacturing (near of CUMFNS)
    # B-ACQ-RTDSM-GDI: the 24 Philadelphia Fed RTDSM Gross Domestic Income
    # (GDI-account) variables (gen_doc_GDI) land under their OWN ids per the
    # roster-wide RTDSM own-base ruling (L534), NEVER aliased onto any GDP-side
    # FRED series -- GDI is the INCOME side of the national accounts, NOT GDP
    # (Phil Fed states the two use largely independent source data; §3.1).
    # DEPTH/replay acquisition (§22.4 acquisition only, NOTHING DERIVES).
    # Delegated reversible acquisition decision under the 2026-08-08 delegation
    # ruling (not §22.2 closure, not rights/product/§22.4). MEASURED shallow
    # real-time depth: headline YNGDI/YRGDI/YNSD first vintage 2005-02; the other
    # 21 components first vintage 2015-05 -> zero pre-2000 real-time recessions.
    # NEAR relation carried by coverage_source_ids=philadelphia_rtdsm, never an
    # alias. The 24 accounting-identity components are pervasively collinear
    # (they sum to GDI); which to keep is a post-closure derivation decision.
    "RTDSM_YNGDI",     # Nominal gross domestic income
    "RTDSM_YRGDI",     # Real gross domestic income
    "RTDSM_YPDGDP",    # GDI-side price index / deflator
    "RTDSM_YNCOMPEP",  # Compensation of employees, paid
    "RTDSM_YNWS",      # Wage and salary disbursements
    "RTDSM_YNSWS",     # Supplements to wages and salaries
    "RTDSM_YNSD",      # Wage and salary, other (disbursements detail)
    "RTDSM_YNTAXR",    # Taxes on production and imports, receipts
    "RTDSM_YNCTAX",    # Corporate income taxes
    "RTDSM_YNGSUB",    # Subsidies (less)
    "RTDSM_YNOS",      # Net operating surplus
    "RTDSM_YNOSG",     # Net operating surplus, government enterprises
    "RTDSM_YNOSP",     # Net operating surplus, private enterprises
    "RTDSM_YNCFC",     # Consumption of fixed capital
    "RTDSM_YNCFCG",    # Consumption of fixed capital, government
    "RTDSM_YNCFCP",    # Consumption of fixed capital, private
    "RTDSM_YNCPRFW",   # Corporate profits with IVA & CCAdj
    "RTDSM_YNCPRFATW", # Corporate profits after tax with IVA & CCAdj
    "RTDSM_YNUCPRFW",  # Undistributed corporate profits with IVA & CCAdj
    "RTDSM_YNIPAID",   # Net interest and misc payments
    "RTDSM_YNDPAID",   # Net dividends paid
    "RTDSM_YNPINCW",   # Proprietors' income with IVA & CCAdj
    "RTDSM_YNRINC",    # Rental income of persons with CCAdj
    "RTDSM_YNTRPAY",   # Business current transfer payments
))
FRED_VINTAGE_SERIES_FIELDS = frozenset(("label", "series_id", "unit"))
FRED_VINTAGE_FAMILY_SUFFIX = ".ASOF"
# The deep lane emits <BASE>.DEEPASOF<YYYYMMDD>. ".DEEPASOF" (never ".ASOFDEEP")
# is required: ".ASOFDEEP" starts with ".ASOF" and would false-collide against
# the append-only .ASOF family prefix gate below.
FRED_VINTAGE_DEEP_FAMILY_SUFFIX = ".DEEPASOF"
FRED_VINTAGE_ADAPTERS = frozenset((
    "fred_json_api_vintages",
    "fred_json_api_vintages_deep",
))


def _fred_vintage_family_suffix(source):
    """The append-only family prefix suffix for a vintage source's lane.

    B-LAND-3D: a deep-lane source may carry a ``vintage_provider_tag`` naming a
    non-primary provider (e.g. FRED-MD alongside ALFRED on the same base). The
    tag is inserted BEFORE ``.DEEPASOF`` so the emitted family prefix
    ``<BASE>.<TAG>.DEEPASOF`` is disjoint in both directions from the primary
    ``<BASE>.DEEPASOF`` family, making the append-only gate per-(base, provider).
    The tag never applies to the shallow ``.ASOF`` lane.
    """
    if source.get("adapter") == "fred_json_api_vintages_deep":
        tag = source.get("vintage_provider_tag")
        if tag:
            return "." + tag + FRED_VINTAGE_DEEP_FAMILY_SUFFIX
        return FRED_VINTAGE_DEEP_FAMILY_SUFFIX
    return FRED_VINTAGE_FAMILY_SUFFIX


def _fred_vintage_base(source):
    """Return the validated, owner-in-scope ALFRED vintage base, else None.

    The vintage lane emits open-ended <BASE>.ASOF<YYYYMMDD> family IDs that
    cannot be declared ahead of the fetch (each as-of snapshot is a distinct
    output identity derived from the returned columns).  Onboarding is gated on
    the base being one of the six owner-approved bases; collision is enforced on
    the family prefix, not an exact ID set.
    """
    if source.get("adapter") not in FRED_VINTAGE_ADAPTERS:
        return None
    series = source.get("series")
    if (
        not isinstance(series, dict) or
        frozenset(series) != FRED_VINTAGE_SERIES_FIELDS
    ):
        raise CanonicalDataError(
            "fred_json_api_vintages series metadata was not exact"
        )
    base = series.get("series_id")
    if not isinstance(base, str) or base not in FRED_VINTAGE_APPROVED_BASES:
        raise CanonicalDataError(
            "fred_json_api_vintages base is outside the approved vintage scope"
        )
    label = series.get("label")
    unit = series.get("unit")
    if (
        not isinstance(label, str) or not label or
        not isinstance(unit, str) or not unit
    ):
        raise CanonicalDataError(
            "fred_json_api_vintages label or unit was invalid"
        )
    return base


def _adapter_output_series_ids(source, require_complete):
    """Derive exact configured output IDs for collision detection.

    Factory onboarding is intentionally narrower than the runtime adapter
    registry.  An adapter whose complete output identity cannot be derived
    from its reviewed configuration must gain an explicit rule here before it
    can be onboarded through the factory.
    """
    adapter = source.get("adapter")
    series = source.get("series")
    explicit = _collect_series_ids(series)
    if adapter == "fed_ddp_csv":
        if not isinstance(series, dict):
            raise CanonicalDataError(
                "fed_ddp_csv output series identity is invalid"
            )
        prefix = series.get("series_id_prefix")
        columns = series.get("expected_columns")
        if (
            not isinstance(prefix, str) or not prefix or
            not isinstance(columns, list) or not columns or
            any(not isinstance(item, str) or not item for item in columns) or
            len(columns) != len(set(columns))
        ):
            raise CanonicalDataError(
                "fed_ddp_csv output series identity is invalid"
            )
        derived = {prefix + column for column in columns}
        if (
            len(derived) != len(columns) or
            any(not item or len(item) > 128 for item in derived)
        ):
            raise CanonicalDataError(
                "fed_ddp_csv output series identity is invalid"
            )
        if explicit and explicit != derived:
            raise CanonicalDataError(
                "fed_ddp_csv explicit and derived output identities differ"
            )
        return derived
    if adapter in FRED_VINTAGE_ADAPTERS:
        # Validates series shape and owner scope (raises on violation).  The
        # concrete <BASE>.ASOF/.DEEPASOF<YYYYMMDD> IDs are data-dependent —
        # derived at parse time from the returned vintage columns — so no exact
        # set can be enumerated here.  Each vintage lane emits ONLY its own
        # <BASE>.<suffix>* identities, never the bare <BASE>, so it coexists
        # with the current lane's <BASE> and with the other vintage lane;
        # returning an empty exact set avoids a false collision.  Re-admission
        # is blocked on the (per-lane) family prefix in
        # _validate_source_candidate.
        _fred_vintage_base(source)
        return frozenset()
    if adapter == "forecast_xlsx":
        if not isinstance(series, dict):
            raise CanonicalDataError(
                "forecast_xlsx output series identity is invalid"
            )
        shape = series.get("forecast_shape")
        if shape == "anxious_index":
            sid = series.get("series_id")
            if not isinstance(sid, str) or not sid.startswith("SPF_"):
                raise CanonicalDataError(
                    "forecast_xlsx anxious series_id is invalid"
                )
            derived = frozenset([sid])
            if explicit and explicit != derived:
                raise CanonicalDataError(
                    "forecast_xlsx explicit and derived output identities differ"
                )
            return derived
        if shape == "spf_aggregate":
            # The SPF_<VARCODE>_<MEAN|MEDIAN> ids are derived from the xlsx header
            # columns, not available at onboarding — exactly like the FRED vintage
            # lane. Validate shape + namespace and return an empty exact set so the
            # append-only family gate (coverage family + source_id) governs
            # re-admission; the lander proves cross-file series uniqueness before
            # any write.
            stat = series.get("statistic")
            prefix = series.get("id_prefix")
            sheet = series.get("sheet")
            if (
                stat not in ("MEAN", "MEDIAN") or
                not isinstance(prefix, str) or not prefix or
                not isinstance(sheet, str) or not sheet
            ):
                raise CanonicalDataError(
                    "forecast_xlsx spf_aggregate output series identity is invalid"
                )
            return frozenset()
        if shape == "spf_individual":
            # The SPF_<VARCODE>_IND_<HORIZON> ids are derived from the panel's
            # horizon columns, not available at onboarding — like spf_aggregate.
            # Validate shape + namespace and return an empty exact set so the
            # append-only family gate (coverage family + source_id) governs
            # re-admission; the lander proves cross-file series uniqueness before
            # any write.
            varcode = series.get("spf_target_code")
            prefix = series.get("id_prefix")
            sheet = series.get("sheet")
            if (
                not isinstance(varcode, str) or not varcode or
                not isinstance(prefix, str) or not prefix or
                not isinstance(sheet, str) or not sheet
            ):
                raise CanonicalDataError(
                    "forecast_xlsx spf_individual output series identity is invalid"
                )
            return frozenset()
        if shape == "nyfed_nowcast":
            # The NY Fed "By Horizon" sheet has a FIXED three-column contract, so
            # the <id_base>_{BACKCAST,NOWCAST,FORECAST} ids ARE enumerable at
            # onboarding (unlike the data-dependent spf_aggregate columns).
            # Return the derived set so the append-only family gate gets exact
            # collision protection.
            id_base = series.get("id_base")
            sheet = series.get("sheet")
            if (
                not isinstance(id_base, str) or
                not id_base.startswith("NYFED_") or
                not isinstance(sheet, str) or not sheet
            ):
                raise CanonicalDataError(
                    "forecast_xlsx nyfed_nowcast output series identity is invalid"
                )
            derived = frozenset(
                "%s_%s" % (id_base, suffix)
                for suffix in ("BACKCAST", "NOWCAST", "FORECAST")
            )
            if explicit and explicit != derived:
                raise CanonicalDataError(
                    "forecast_xlsx explicit and derived output identities differ"
                )
            return derived
        raise CanonicalDataError(
            "forecast_xlsx forecast_shape is unsupported: %r" % (shape,)
        )
    if adapter == "geo_panel_json":
        # The <id_prefix>.<unit>.<metric> ids are data-dependent — the geo unit
        # set (states/FIPS/CBSA) comes from the cached file, not the config —
        # exactly like the SPF aggregate lane. Validate shape + namespace and
        # return an empty exact set so the append-only family gate (coverage
        # family + source_id) governs re-admission; the lander proves
        # cross-series uniqueness before any write.
        if not isinstance(series, dict):
            raise CanonicalDataError("geo_panel output series identity is invalid")
        container_key = series.get("container_key")
        id_prefix = series.get("id_prefix")
        metrics = series.get("metrics")
        if (
            not isinstance(container_key, str) or not container_key or
            not isinstance(id_prefix, str) or not id_prefix or
            not isinstance(metrics, dict) or not metrics
        ):
            raise CanonicalDataError("geo_panel output series identity is invalid")
        for metric, mspec in metrics.items():
            if (
                not isinstance(metric, str) or not metric or
                not isinstance(mspec, dict) or
                mspec.get("offset_key") not in ("m0", "q0", "y0") or
                mspec.get("freq") not in ("m", "q", "a") or
                not isinstance(mspec.get("unit"), str) or not mspec.get("unit")
            ):
                raise CanonicalDataError(
                    "geo_panel metric identity is invalid: %r" % (metric,)
                )
        return frozenset()
    if adapter == "geo_grid_json":
        # <id_prefix>.<unit>.<code> ids are data-dependent (geo unit set comes
        # from the cached file). Validate block shape + namespace and return an
        # empty exact set; the family gate + lander govern re-admission.
        if not isinstance(series, dict):
            raise CanonicalDataError("geo_grid output series identity is invalid")
        id_prefix = series.get("id_prefix")
        blocks = series.get("blocks")
        if (
            not isinstance(id_prefix, str) or not id_prefix or
            not isinstance(blocks, list) or not blocks
        ):
            raise CanonicalDataError("geo_grid output series identity is invalid")
        for block in blocks:
            if (
                not isinstance(block, dict) or
                not isinstance(block.get("axis_key"), str) or not block.get("axis_key") or
                not isinstance(block.get("container_key"), str) or not block.get("container_key")
            ):
                raise CanonicalDataError("geo_grid block identity is invalid")
            if block.get("metric_level"):
                metrics = block.get("metrics")
                if not isinstance(metrics, dict) or not metrics or any(
                    not isinstance(m, dict) or not isinstance(m.get("unit"), str)
                    or not m.get("unit")
                    for m in metrics.values()
                ):
                    raise CanonicalDataError("geo_grid metric identity is invalid")
            else:
                if (
                    not isinstance(block.get("metric_suffix"), str) or
                    not block.get("metric_suffix") or
                    not isinstance(block.get("unit"), str) or not block.get("unit")
                ):
                    raise CanonicalDataError("geo_grid block identity is invalid")
        return frozenset()
    if adapter == "dol_eta539_csv":
        # The <source_id>.<STATE>.<label> ids are data-dependent — the state set
        # comes from the cached ETA-539 file, not the config — exactly like the
        # geo_panel / spf_aggregate lanes. Validate the retention shape and return
        # an empty exact set so the append-only family gate (coverage family +
        # source_id) governs re-admission; the lander proves cross-series
        # uniqueness before any write. (B-ACQ-PUBLISHER-DIRECT: enables the proven
        # dol_eta539_csv adapter to land via the offline-current binder.)
        if not isinstance(series, dict):
            raise CanonicalDataError(
                "dol_eta539_csv output series identity is invalid"
            )
        keep = series.get("retention_rows_per_state")
        if not isinstance(keep, int) or isinstance(keep, bool) or keep <= 0:
            raise CanonicalDataError(
                "dol_eta539_csv output series identity is invalid"
            )
        return frozenset()
    if adapter == "fhfa_hpi_at_geo_csv":
        # The <prefix>.<place>[.RSTDERR] ids are data-dependent — the state or
        # CBSA set comes from the cached headerless file, not the config —
        # exactly like the geo_panel / dol_eta539 lanes. Validate the layout
        # contract + namespace and return an empty exact set so the append-only
        # family gate (coverage family + source_id) governs re-admission; the
        # lander proves cross-series uniqueness before any write.
        if not isinstance(series, dict):
            raise CanonicalDataError(
                "fhfa_hpi_at_geo_csv output series identity is invalid"
            )
        layout = series.get("layout")
        prefix = series.get("series_id_prefix")
        if (
            layout not in ("state", "metro") or
            not isinstance(prefix, str) or not prefix or
            not isinstance(series.get("geography_type"), str) or
            not series.get("geography_type") or
            not isinstance(series.get("index_semantics"), str) or
            not series.get("index_semantics") or
            not isinstance(series.get("index_unit"), str) or
            not series.get("index_unit")
        ):
            raise CanonicalDataError(
                "fhfa_hpi_at_geo_csv output series identity is invalid"
            )
        if layout == "metro" and (
            not isinstance(series.get("stderr_unit"), str) or
            not series.get("stderr_unit")
        ):
            raise CanonicalDataError(
                "fhfa_hpi_at_geo_csv metro output series identity is invalid"
            )
        return frozenset()
    if adapter == "bea_regional_cainc_zip":
        # The {prefix}.{GeoFIPS}.L{LineCode} ids are data-dependent — the geo
        # set for the requested cross-section comes from the cached ALL_AREAS
        # file, not the config — same as the fhfa_hpi_at_geo / dol_eta539
        # lanes. Validate the geography + namespace contract and return an
        # empty exact set so the append-only family gate governs re-admission;
        # the lander proves cross-series uniqueness before any write.
        if not isinstance(series, dict):
            raise CanonicalDataError(
                "bea_regional_cainc_zip output series identity is invalid"
            )
        if (
            series.get("geography_type") not in (
                "national_us", "bea_region", "state_or_dc", "county") or
            not isinstance(series.get("series_id_prefix"), str) or
            not series.get("series_id_prefix") or
            not isinstance(series.get("table"), str) or
            not series.get("table")
        ):
            raise CanonicalDataError(
                "bea_regional_cainc_zip output series identity is invalid"
            )
        return frozenset()
    if adapter in EXPLICIT_OUTPUT_ID_ADAPTERS:
        if explicit:
            return explicit
        raise CanonicalDataError(
            "%s output series identity is incomplete" % adapter
        )
    if require_complete:
        raise CanonicalDataError(
            "%s output series identity derivation is unsupported" % adapter
        )
    return explicit


def _configured_project_root(project_root, relative_path, context):
    if not isinstance(relative_path, str) or not relative_path:
        raise CanonicalDataError("%s is invalid" % context)
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise CanonicalDataError("%s is invalid" % context)
    project_root = Path(project_root).resolve()
    candidate = (project_root / relative).resolve()
    if candidate != project_root and project_root not in candidate.parents:
        raise CanonicalDataError("%s escaped the project root" % context)
    return candidate


def _read_immutable_generation_file(path, generations_root):
    path = Path(path).absolute()
    try:
        info = path.lstat()
    except OSError as exc:
        raise CanonicalDataError(
            "active generation member is unavailable"
        ) from exc
    if (
        stat.S_ISLNK(info.st_mode) or
        not stat.S_ISREG(info.st_mode) or
        info.st_nlink != 1 or
        stat.S_IMODE(info.st_mode) != 0o444
    ):
        raise CanonicalDataError(
            "active generation member is not immutable"
        )
    return safe_regular_file(path, generations_root)


def _active_measurement_series_ids(project_root, active_config):
    """Authenticate the current generation and return its exact series set."""
    project_root = Path(project_root).resolve()
    store = active_config.get("store")
    if not isinstance(store, dict):
        raise CanonicalDataError("active configuration store is invalid")
    public_root = _configured_project_root(
        project_root,
        store.get("public"),
        "active public root",
    )
    store_root = _configured_project_root(
        project_root,
        store.get("root"),
        "active store root",
    )
    generations_root = (store_root / "generations").resolve()
    if store_root not in generations_root.parents:
        raise CanonicalDataError("active generation root escaped its store")
    pointer_path = public_root / "latest.pointer.json"
    try:
        pointer_bytes_before = safe_regular_file(
            pointer_path,
            public_root,
        )
    except (FileNotFoundError, OSError) as exc:
        raise CanonicalDataError(
            "active generation pointer is unavailable"
        ) from exc
    pointer = strict_json_loads(pointer_bytes_before)
    _require_exact_keys(
        pointer,
        LIVE_POINTER_FIELDS,
        "active generation pointer",
    )
    if pointer["schema_version"] != "recession-monitor-v2.live-pointer.v2":
        raise CanonicalDataError("active generation pointer schema differs")
    for field in (
        "coverage_sha256",
        "generation_sha256",
        "manifest_sha256",
        "snapshot_sha256",
        "status_sha256",
    ):
        if (
            not isinstance(pointer[field], str) or
            not SHA256_RE.match(pointer[field])
        ):
            raise CanonicalDataError(
                "active generation pointer digest is invalid"
            )
    if pointer["generation_sha256"] != pointer["manifest_sha256"]:
        raise CanonicalDataError(
            "active generation and manifest identities differ"
        )

    generation_root = (
        generations_root / pointer["generation_sha256"]
    )
    try:
        generation_info = generation_root.lstat()
        actual_names = {path.name for path in generation_root.iterdir()}
    except OSError as exc:
        raise CanonicalDataError(
            "active generation directory is unavailable"
        ) from exc
    if (
        stat.S_ISLNK(generation_info.st_mode) or
        not stat.S_ISDIR(generation_info.st_mode) or
        actual_names != LIVE_GENERATION_MEMBERS | {"manifest.json"}
    ):
        raise CanonicalDataError(
            "active generation directory is invalid"
        )
    manifest_path = generation_root / "manifest.json"
    manifest_bytes = _read_immutable_generation_file(
        manifest_path,
        generations_root,
    )
    if (
        sha256_bytes(manifest_bytes) != pointer["manifest_sha256"] or
        generation_root.name != pointer["generation_sha256"]
    ):
        raise CanonicalDataError("active generation manifest hash differs")
    manifest = strict_json_loads(manifest_bytes)
    _require_exact_keys(
        manifest,
        frozenset((
            "created_at",
            "members",
            "schema_version",
            "source_head_receipt_sha256",
        )),
        "active generation manifest",
    )
    if (
        manifest["schema_version"] !=
        "recession-monitor-v2.live-generation-manifest.v2" or
        not isinstance(manifest["members"], dict) or
        frozenset(manifest["members"]) != LIVE_GENERATION_MEMBERS
    ):
        raise CanonicalDataError("active generation manifest policy differs")

    member_bytes = {}
    pointer_fields = {
        "coverage.json": "coverage_sha256",
        "snapshot.json": "snapshot_sha256",
        "status.json": "status_sha256",
    }
    for name in sorted(LIVE_GENERATION_MEMBERS):
        binding = manifest["members"].get(name)
        if (
            not isinstance(binding, dict) or
            frozenset(binding) !=
            frozenset(("bytes", "schema_version", "sha256")) or
            not isinstance(binding["bytes"], int) or
            binding["bytes"] < 1 or
            not isinstance(binding["sha256"], str) or
            not SHA256_RE.match(binding["sha256"]) or
            pointer[pointer_fields[name]] != binding["sha256"]
        ):
            raise CanonicalDataError(
                "active generation member binding is invalid"
            )
        data = _read_immutable_generation_file(
            generation_root / name,
            generations_root,
        )
        if (
            len(data) != binding["bytes"] or
            sha256_bytes(data) != binding["sha256"]
        ):
            raise CanonicalDataError(
                "active generation member hash differs"
            )
        member_bytes[name] = data

    snapshot = strict_json_loads(member_bytes["snapshot.json"])
    if (
        snapshot.get("schema_version") !=
        manifest["members"]["snapshot.json"]["schema_version"] or
        snapshot.get("schema_version") !=
        "recession-monitor-v2.live-snapshot.v1" or
        not isinstance(snapshot.get("sources"), list) or
        not isinstance(snapshot.get("series"), dict)
    ):
        raise CanonicalDataError("active generation snapshot is malformed")
    # A published generation binds every enabled live source and MAY also bind
    # archival (enabled:false) heads (B-LAND-3B: build_snapshot includes bound
    # archival heads; an unbound archival family is simply absent). So the
    # generation-member set is bounded: enabled ⊆ published ⊆ enabled ∪ archival.
    # The gate must accept that whole band, or the first bind AFTER any archival
    # family is published false-trips "stale or mixed" (enabled-only 190 !=
    # published 197); requiring exact enabled∪archival equality would instead
    # reject a legitimate generation that omits an unbound archival head.
    # B-LAND-3C-R2 fix (was: enabled-only exact equality).
    enabled_source_ids = {
        source.get("source_id")
        for source in active_config.get("sources", [])
        if source.get("enabled") is True
    }
    archival_source_ids = {
        source.get("source_id")
        for source in active_config.get("sources", [])
        if source.get("archival") is True
    }
    active_source_ids = enabled_source_ids | archival_source_ids
    if (
        not enabled_source_ids or
        None in active_source_ids or
        len(active_source_ids) != sum(
            1 for source in active_config.get("sources", [])
            if source.get("enabled") is True or source.get("archival") is True
        )
    ):
        raise CanonicalDataError(
            "active configuration source identity is invalid"
        )
    snapshot_receipts = {}
    for binding in snapshot["sources"]:
        if not isinstance(binding, dict):
            raise CanonicalDataError(
                "active generation snapshot source is malformed"
            )
        source_id = binding.get("source_id")
        receipt_sha256 = binding.get("receipt_sha256")
        if (
            not isinstance(source_id, str) or not source_id or
            source_id in snapshot_receipts or
            not isinstance(receipt_sha256, str) or
            not SHA256_RE.match(receipt_sha256)
        ):
            raise CanonicalDataError(
                "active generation snapshot source is malformed"
            )
        snapshot_receipts[source_id] = receipt_sha256
    manifest_receipts = manifest["source_head_receipt_sha256"]
    published_ids = set(snapshot_receipts)
    if (
        not isinstance(manifest_receipts, dict) or
        snapshot_receipts != manifest_receipts or
        # not stale: every enabled source is published; not mixed: nothing
        # outside the enabled ∪ archival config membership leaked in.
        not (enabled_source_ids <= published_ids <= active_source_ids)
    ):
        raise CanonicalDataError(
            "active generation source set is stale or mixed"
        )

    measurement_ids = set()
    for series_id, binding in snapshot["series"].items():
        if (
            not isinstance(series_id, str) or not series_id or
            not isinstance(binding, dict) or
            binding.get("series_id") != series_id or
            binding.get("source_id") not in active_source_ids
        ):
            raise CanonicalDataError(
                "active generation measurement identity is malformed"
            )
        measurement_ids.add(series_id)
    if not measurement_ids:
        raise CanonicalDataError(
            "active generation measurement set is empty"
        )

    if (
        _read_immutable_generation_file(
            manifest_path,
            generations_root,
        ) != manifest_bytes or
        _read_immutable_generation_file(
            generation_root / "snapshot.json",
            generations_root,
        ) != member_bytes["snapshot.json"] or
        safe_regular_file(pointer_path, public_root) != pointer_bytes_before
    ):
        raise CanonicalDataError(
            "active generation changed during collision validation"
        )
    return measurement_ids


def _validate_source_candidate(project_root, active_config, source):
    source_id = source.get("source_id")
    if source_id in {
        row.get("source_id") for row in active_config.get("sources", [])
    }:
        raise CanonicalDataError("source_id is already active: %s" % source_id)
    endpoint = str(source.get("endpoint", "")).lower()
    allowed_hosts = [str(item).lower() for item in source.get("allowed_hosts", [])]
    if any(
        token in value
        for value in [endpoint] + allowed_hosts
        for token in AI_HOST_TOKENS
    ):
        raise CanonicalDataError("AI endpoint token is prohibited")

    existing_series = _active_measurement_series_ids(
        project_root,
        active_config,
    )
    candidate_series = _adapter_output_series_ids(
        source,
        require_complete=True,
    )
    collisions = sorted(existing_series & candidate_series)
    if collisions:
        raise CanonicalDataError(
            "candidate series IDs already exist: %r" % collisions
        )

    vintage_base = _fred_vintage_base(source)
    if vintage_base is not None:
        # Append-only immutable: the <BASE>.<suffix><YYYYMMDD> family is
        # open-ended, so a re-admission of the SAME base on the SAME lane
        # collides against the realized family IDs already in the active
        # generation.  Enforce on the per-lane family prefix (.ASOF for the
        # shallow lane, .DEEPASOF for the deep lane), so the deep lane can be
        # admitted alongside an already-live shallow family for the same base
        # and vice versa.  The exact-set intersection above cannot see prefix
        # overlap.
        family_prefix = vintage_base + _fred_vintage_family_suffix(source)
        family_collisions = sorted(
            series_id for series_id in existing_series
            if series_id.startswith(family_prefix)
        )
        if family_collisions:
            raise CanonicalDataError(
                "candidate vintage family already present: %r"
                % family_collisions[:8]
            )

    candidate = dict(active_config)
    candidate["sources"] = list(active_config["sources"]) + [source]
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "candidate.json"
        path.write_bytes(canonical_json_bytes(candidate))
        load_config(path)
    _validate_family_bindings(project_root, source)
    return candidate


def _candidate_planned(planned, reservation):
    action = reservation["action"]
    reservation_id = reservation["source_id"]
    candidate = dict(planned)
    rows = list(planned["sources"])
    for row in rows:
        if tuple(row) != PLANNED_SOURCE_FIELD_ORDER:
            raise CanonicalDataError(
                "planned source package field order differs"
            )
    matches = [
        index for index, row in enumerate(rows)
        if row.get("source_id") == reservation_id
    ]
    if action in ("remove_exact", "retain_exact") and len(matches) != 1:
        raise CanonicalDataError(
            "reservation transition did not resolve exactly once"
        )
    if action == "remove_exact":
        del rows[matches[0]]
    candidate["sources"] = rows
    candidate["scope"] = dict(planned["scope"])
    candidate["scope"]["reservation_count"] = len(rows)
    return candidate


def _normalization_summary(records):
    periods = sorted({
        row.get("observation_period")
        for row in records
        if isinstance(row.get("observation_period"), str)
    })
    if not periods:
        raise CanonicalDataError(
            "normalized fixture has no observation periods"
        )
    return {
        "first_observation_period": periods[0],
        "last_observation_period": periods[-1],
        "record_count": len(records),
        "series_ids": sorted({
            row.get("series_id") for row in records
            if isinstance(row.get("series_id"), str)
        }),
        "units": sorted({
            row.get("unit") for row in records
            if isinstance(row.get("unit"), str)
        }),
        "value_statuses": sorted({
            row.get("value_status") for row in records
            if isinstance(row.get("value_status"), str)
        }),
    }


ADMISSION_SCHEMA = "recession-monitor-v2.feed-admission-gate.v1"
MARKUP_PREFIXES = (b"<!doctype", b"<html", b"<?xml", b"<!--", b"<head")
MARKUP_BEARING_ADAPTERS = frozenset((
    "census_btos_xlsx",
    "census_qss_timeseries_zip",
    "raw_capture",
    "regional_survey_xlsx",
    "treasury_yield_xml",
    "tsa_passenger_html",
))
PROPRIETARY_RIGHTS_MARKERS = (
    "proprietary",
    "restricted",
    "license_required",
    "not_redistributable",
)


def evaluate_admission_gate(
    receipt,
    summary,
    fixture_bytes,
    adapter,
    rights,
    active_series_ids,
    active_source_ids,
    record_floor=1,
):
    """Decide admission from bytes and counts alone, with no judgment.

    Every check is recomputable from the candidate bundle and the active
    configuration. The gate exists so that automatic activation cannot
    publish a payload that is not data. It grants no scientific admission:
    an admitted feed is still only an acquisition route.
    """
    checks = []

    def record(name, passed, detail):
        checks.append({
            "check": name,
            "detail": detail,
            "passed": bool(passed),
        })

    head = bytes(fixture_bytes or b"")[:512].lstrip().lower()
    markup = head.startswith(MARKUP_PREFIXES)
    record(
        "payload_is_data_not_markup",
        (not markup) or adapter in MARKUP_BEARING_ADAPTERS,
        "adapter=%s markup_prefix=%s" % (adapter, markup),
    )
    count = receipt.get("record_count")
    record(
        "record_count_at_or_above_floor",
        isinstance(count, int) and count >= record_floor,
        "record_count=%r floor=%d" % (count, record_floor),
    )
    series_ids = receipt.get("series_ids")
    record(
        "series_identities_present",
        (
            isinstance(series_ids, list) and
            bool(series_ids) and
            all(
                isinstance(item, str) and item
                for item in series_ids
            )
        ),
        "series_count=%d" % (
            len(series_ids) if isinstance(series_ids, list) else -1
        ),
    )
    collisions = sorted(
        set(series_ids or []) & set(active_series_ids or ())
    )
    record(
        "no_series_identity_collision",
        not collisions,
        "collisions=%r" % collisions[:5],
    )
    source_id = receipt.get("source_id")
    record(
        "no_source_identity_collision",
        source_id not in set(active_source_ids or ()),
        "source_id=%r" % source_id,
    )
    first = (summary or {}).get("first_observation_period")
    last = (summary or {}).get("last_observation_period")
    record(
        "observation_periods_ordered",
        (
            isinstance(first, str) and isinstance(last, str) and
            bool(first) and first <= last
        ),
        "first=%r last=%r" % (first, last),
    )
    lowered = rights.lower() if isinstance(rights, str) else ""
    record(
        "rights_declared_and_not_proprietary",
        bool(lowered) and not any(
            marker in lowered for marker in PROPRIETARY_RIGHTS_MARKERS
        ),
        "rights=%r" % rights,
    )
    record(
        "normalized_identity_is_bound",
        bool(SHA256_RE.match(receipt.get("normalized_sha256") or "")),
        "normalized_sha256=%r" % receipt.get("normalized_sha256"),
    )
    failures = sorted(
        item["check"] for item in checks if not item["passed"]
    )
    return {
        "admitted": not failures,
        "checks": sorted(checks, key=lambda item: item["check"]),
        "failed_checks": failures,
        "schema_version": ADMISSION_SCHEMA,
        "scientific_effect": "none",
        "source_id": source_id,
        "verdict": "ADMITTED" if not failures else "BLOCKED_NOT_DATA",
    }


def probe_onboarding_source(
    project_root,
    draft_path,
    http_client=None,
    clock=utc_now,
):
    """Fetch and normalize one source in an isolated, non-active probe lane."""
    project_root = Path(project_root).resolve()
    draft_path, draft_bytes = _read_draft_bytes(
        project_root,
        draft_path,
    )
    draft = _load_discovery_spec(project_root, draft_path)
    active_path = project_root / "live_data" / "config" / "sources.v1.json"
    active = strict_json_loads(safe_regular_file(
        active_path,
        project_root / "live_data" / "config",
    ))
    _validate_source_candidate(
        project_root,
        active,
        draft["source"],
    )
    retrieved_at = clock()
    if (
        not isinstance(retrieved_at, str) or
        not TIMESTAMP_RE.match(retrieved_at)
    ):
        raise CanonicalDataError("probe clock is invalid")
    now = datetime.strptime(
        retrieved_at,
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=timezone.utc)
    client = http_client or PublisherHttpClient()
    response = client.fetch(
        draft["source"],
        now=now,
        conditional_headers={},
    )
    validate_response(draft["source"], response)
    final_host = urlparse(response.url).hostname
    if final_host not in draft["source"]["allowed_hosts"]:
        raise CanonicalDataError(
            "probe response host is outside the source allowlist"
        )
    records = normalize(
        draft["source"],
        response.body,
        retrieved_at,
    )
    summary = _normalization_summary(records)
    raw_sha256 = sha256_bytes(response.body)
    source_id = draft["source"]["source_id"]
    normalized = {
        "parser_id": "rmv2-live/%s" % draft["source"]["adapter"],
        "records": records,
        "retrieved_at": retrieved_at,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": raw_sha256,
        "source_id": source_id,
    }
    normalized_bytes = canonical_json_bytes(normalized)
    attempt_identity = {
        "content_type": response.headers.get("content-type"),
        "draft_sha256": sha256_bytes(draft_bytes),
        "etag": response.headers.get("etag"),
        "final_url": response.url,
        "last_modified": response.headers.get("last-modified"),
        "normalized_sha256": sha256_bytes(normalized_bytes),
        "raw_bytes": len(response.body),
        "raw_sha256": raw_sha256,
        "retrieved_at": retrieved_at,
        "source_id": source_id,
    }
    attempt_id = sha256_bytes(canonical_json_bytes(attempt_identity))
    probe_root = (
        project_root / "live_data" / "feed_factory" /
        "probes" / source_id / attempt_id
    )
    fixture_path = probe_root / "source.payload"
    relative_fixture = str(fixture_path.relative_to(project_root))
    spec = {
        "activation": draft["activation"],
        "expected_normalization": summary,
        "fixture": {
            "bytes": len(response.body),
            "path": relative_fixture,
            "retrieved_at": retrieved_at,
            "sha256": raw_sha256,
        },
        "reservation": draft["reservation"],
        "schema_version": SPEC_SCHEMA,
        "source": draft["source"],
    }
    spec_bytes = canonical_json_bytes(spec)
    spec_sha256 = sha256_bytes(spec_bytes)
    spec_path = (
        project_root / "live_data" / "feed_factory" / "recipes" /
        ("%s.%s.v1.json" % (source_id, spec_sha256))
    )
    receipt = {
        "attempt_id": attempt_id,
        "content_type": response.headers.get("content-type"),
        "draft_sha256": sha256_bytes(draft_bytes),
        "etag": response.headers.get("etag"),
        "final_url": response.url,
        "last_modified": response.headers.get("last-modified"),
        "normalized_sha256": sha256_bytes(normalized_bytes),
        "raw_bytes": len(response.body),
        "raw_sha256": raw_sha256,
        "record_count": summary["record_count"],
        "retrieved_at": retrieved_at,
        "schema_version": "recession-monitor-v2.feed-probe-receipt.v1",
        "scientific_effect": "none",
        "series_ids": summary["series_ids"],
        "source_id": source_id,
        "spec_sha256": spec_sha256,
        "status": "PROBE_PASS_NOT_ACTIVE",
        "website_effect": "none_until_activation",
    }
    output_root = project_root / "live_data" / "feed_factory"
    _ensure_safe_output_directory(probe_root, output_root)
    _write_immutable(
        fixture_path,
        response.body,
        output_root,
    )
    _write_immutable(
        probe_root / "normalized.json",
        normalized_bytes,
        output_root,
    )
    _write_immutable(
        probe_root / "probe.receipt.json",
        canonical_json_bytes(receipt),
        output_root,
    )
    _write_immutable(spec_path, spec_bytes, output_root)
    result = dict(receipt)
    result["probe_path"] = str(probe_root)
    result["spec_path"] = str(spec_path)
    return result


def compile_onboarding_spec(project_root, spec_path):
    """Compile and fixture-test a recipe without touching active live state."""
    project_root = Path(project_root).resolve()
    spec_path, spec_bytes = _read_spec_bytes(project_root, spec_path)
    spec = load_onboarding_spec(project_root, spec_path)
    active_path = project_root / "live_data" / "config" / "sources.v1.json"
    planned_path = (
        project_root / "live_data" / "config" /
        "planned_sources.v1.json"
    )
    active_bytes = safe_regular_file(
        active_path,
        project_root / "live_data" / "config",
    )
    planned_bytes = safe_regular_file(
        planned_path,
        project_root / "live_data" / "config",
    )
    active = strict_json_loads(active_bytes)
    planned = strict_json_loads(planned_bytes)
    candidate_config = _validate_source_candidate(
        project_root,
        active,
        spec["source"],
    )
    candidate_planned = _candidate_planned(
        planned,
        spec["reservation"],
    )

    _, fixture_bytes = _project_file(
        project_root,
        spec["fixture"]["path"],
    )
    if len(fixture_bytes) != spec["fixture"]["bytes"]:
        raise CanonicalDataError("fixture byte count differs")
    if sha256_bytes(fixture_bytes) != spec["fixture"]["sha256"]:
        raise CanonicalDataError("fixture SHA-256 differs")
    records = normalize(
        spec["source"],
        fixture_bytes,
        spec["fixture"]["retrieved_at"],
    )
    summary = _normalization_summary(records)
    if summary != spec["expected_normalization"]:
        raise CanonicalDataError(
            "normalized fixture differs from exact expectation"
        )
    normalized = {
        "parser_id": "rmv2-live/%s" % spec["source"]["adapter"],
        "records": records,
        "retrieved_at": spec["fixture"]["retrieved_at"],
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": spec["fixture"]["sha256"],
        "source_id": spec["source"]["source_id"],
    }
    normalized_bytes = canonical_json_bytes(normalized)
    candidate_config_bytes = canonical_json_bytes(candidate_config)
    candidate_planned_bytes = _package_json_bytes(candidate_planned)
    receipt = {
        "candidate_config_sha256": sha256_bytes(
            candidate_config_bytes
        ),
        "candidate_planned_sha256": sha256_bytes(
            candidate_planned_bytes
        ),
        "fixture_bytes": len(fixture_bytes),
        "fixture_sha256": sha256_bytes(fixture_bytes),
        "normalized_sha256": sha256_bytes(normalized_bytes),
        "predecessor_config_sha256": sha256_bytes(active_bytes),
        "predecessor_planned_sha256": sha256_bytes(planned_bytes),
        "record_count": summary["record_count"],
        "schema_version": RECEIPT_SCHEMA,
        "scientific_effect": "none",
        "series_ids": summary["series_ids"],
        "source_id": spec["source"]["source_id"],
        "spec_sha256": sha256_bytes(spec_bytes),
        "status": "COMPILED_FIXTURE_VERIFIED_NOT_ACTIVE",
        "website_effect": "measurement_catalog_and_status_only",
    }
    return {
        "candidate_config": candidate_config,
        "candidate_config_bytes": candidate_config_bytes,
        "candidate_planned": candidate_planned,
        "candidate_planned_bytes": candidate_planned_bytes,
        "normalized": normalized,
        "normalized_bytes": normalized_bytes,
        "fixture_bytes": fixture_bytes,
        "receipt": receipt,
        "receipt_bytes": canonical_json_bytes(receipt),
        "spec": spec,
        "spec_bytes": spec_bytes,
    }


def materialize_candidate_bundle(project_root, compiled):
    """Store one immutable, reviewable activation candidate."""
    project_root = Path(project_root).resolve()
    receipt = compiled["receipt"]
    fixture_bytes = compiled.get("fixture_bytes")
    if (
        not isinstance(fixture_bytes, bytes) or
        len(fixture_bytes) != receipt["fixture_bytes"] or
        sha256_bytes(fixture_bytes) != receipt["fixture_sha256"]
    ):
        raise CanonicalDataError(
            "compiled raw fixture binding is invalid"
        )
    raw_member_name = (
        "fixture.raw.%s.bin" % receipt["fixture_sha256"]
    )
    members = {
        "candidate.sources.v1.json": compiled["candidate_config_bytes"],
        "candidate.planned_sources.v1.json": (
            compiled["candidate_planned_bytes"]
        ),
        "fixture.normalized.json": compiled["normalized_bytes"],
        raw_member_name: fixture_bytes,
        "onboarding.spec.json": compiled["spec_bytes"],
        "onboarding.receipt.json": compiled["receipt_bytes"],
    }
    manifest = {
        "members": {
            name: {
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
            for name, data in sorted(members.items())
        },
        "predecessor_config_sha256": receipt[
            "predecessor_config_sha256"
        ],
        "predecessor_planned_sha256": receipt[
            "predecessor_planned_sha256"
        ],
        "schema_version": BUNDLE_SCHEMA,
        "scientific_effect": "none",
        "source_id": receipt["source_id"],
        "status": "CANDIDATE_NOT_ACTIVE",
    }
    manifest_bytes = canonical_json_bytes(manifest)
    bundle_id = sha256_bytes(manifest_bytes)
    bundle_root = (
        project_root / "live_data" / "feed_factory" /
        "candidates" / receipt["source_id"] / bundle_id
    )
    try:
        bundle_root.lstat()
        bundle_existed = True
    except FileNotFoundError:
        bundle_existed = False
    except OSError as exc:
        raise CanonicalDataError(
            "candidate bundle path is unavailable"
        ) from exc
    _ensure_safe_output_directory(
        bundle_root,
        project_root / "live_data" / "feed_factory",
    )
    expected_files = dict(members)
    expected_files["manifest.json"] = manifest_bytes
    if bundle_existed:
        actual_names = {path.name for path in bundle_root.iterdir()}
        if actual_names != set(expected_files):
            raise CanonicalDataError(
                "frozen candidate bundle file set differs"
            )
        for name, data in expected_files.items():
            _verify_frozen_file(
                bundle_root / name,
                data,
                bundle_root,
            )
    else:
        for name, data in members.items():
            _write_immutable(
                bundle_root / name,
                data,
                project_root / "live_data" / "feed_factory",
            )
        _write_immutable(
            bundle_root / "manifest.json",
            manifest_bytes,
            project_root / "live_data" / "feed_factory",
        )
        for name, data in expected_files.items():
            _verify_frozen_file(
                bundle_root / name,
                data,
                bundle_root,
            )
    return {
        "bundle_id": bundle_id,
        "manifest_path": bundle_root / "manifest.json",
    }


def _read_frozen_file(path, allowed_root):
    path = Path(path).absolute()
    try:
        info = path.lstat()
    except OSError as exc:
        raise CanonicalDataError(
            "frozen candidate file is unavailable"
        ) from exc
    if (
        stat.S_ISLNK(info.st_mode) or
        not stat.S_ISREG(info.st_mode) or
        info.st_nlink != 1 or
        stat.S_IMODE(info.st_mode) != 0o444
    ):
        raise CanonicalDataError(
            "frozen candidate file identity or mode differs"
        )
    return safe_regular_file(path, allowed_root)


def _verify_frozen_file(path, expected, allowed_root):
    actual = _read_frozen_file(path, allowed_root)
    if actual != expected:
        raise CanonicalDataError(
            "frozen candidate file bytes differ"
        )
    return actual


def _read_bundle_member(bundle_root, manifest, name):
    binding = manifest["members"].get(name)
    if (
        not isinstance(binding, dict) or
        frozenset(binding) != frozenset(("bytes", "sha256"))
    ):
        raise CanonicalDataError("bundle member binding is invalid")
    data = _read_frozen_file(bundle_root / name, bundle_root)
    if len(data) != binding["bytes"]:
        raise CanonicalDataError("bundle member byte count differs")
    if sha256_bytes(data) != binding["sha256"]:
        raise CanonicalDataError("bundle member SHA-256 differs")
    return data


def _validate_receipt(receipt):
    _require_exact_keys(receipt, RECEIPT_FIELDS, "onboarding receipt")
    if (
        receipt["schema_version"] != RECEIPT_SCHEMA or
        receipt["scientific_effect"] != "none" or
        receipt["status"] != "COMPILED_FIXTURE_VERIFIED_NOT_ACTIVE" or
        receipt["website_effect"] !=
        "measurement_catalog_and_status_only"
    ):
        raise CanonicalDataError("onboarding receipt policy is invalid")
    for name in (
        "candidate_config_sha256",
        "candidate_planned_sha256",
        "fixture_sha256",
        "normalized_sha256",
        "predecessor_config_sha256",
        "predecessor_planned_sha256",
        "spec_sha256",
    ):
        if (
            not isinstance(receipt[name], str) or
            not SHA256_RE.match(receipt[name])
        ):
            raise CanonicalDataError(
                "onboarding receipt %s is invalid" % name
            )
    if (
        not isinstance(receipt["fixture_bytes"], int) or
        receipt["fixture_bytes"] < 1 or
        not isinstance(receipt["record_count"], int) or
        receipt["record_count"] < 1 or
        not isinstance(receipt["source_id"], str) or
        not receipt["source_id"]
    ):
        raise CanonicalDataError("onboarding receipt identity is invalid")
    _unique_sorted_strings(
        receipt["series_ids"],
        "onboarding receipt series_ids",
    )


def _validate_normalized_member(normalized, normalized_bytes, receipt, source):
    _require_exact_keys(
        normalized,
        NORMALIZED_FIELDS,
        "normalized fixture",
    )
    if (
        normalized["schema_version"] !=
        "recession-monitor-v2.normalized-source.v1" or
        normalized["source_id"] != receipt["source_id"] or
        normalized["source_id"] != source.get("source_id") or
        normalized["parser_id"] !=
        "rmv2-live/%s" % source.get("adapter") or
        normalized["source_bytes_sha256"] != receipt["fixture_sha256"] or
        not isinstance(normalized["retrieved_at"], str) or
        not TIMESTAMP_RE.match(normalized["retrieved_at"]) or
        not isinstance(normalized["records"], list)
    ):
        raise CanonicalDataError(
            "normalized fixture semantic binding differs"
        )
    if sha256_bytes(normalized_bytes) != receipt["normalized_sha256"]:
        raise CanonicalDataError(
            "normalized fixture receipt hash differs"
        )
    summary = _normalization_summary(normalized["records"])
    if (
        summary["record_count"] != receipt["record_count"] or
        summary["series_ids"] != receipt["series_ids"]
    ):
        raise CanonicalDataError(
            "normalized fixture receipt summary differs"
        )


def _validate_candidate_planned_transition(current, candidate, source):
    if (
        not isinstance(current, dict) or
        not isinstance(candidate, dict) or
        frozenset(current) != frozenset(candidate) or
        not isinstance(current.get("sources"), list) or
        not isinstance(candidate.get("sources"), list) or
        not isinstance(current.get("scope"), dict) or
        not isinstance(candidate.get("scope"), dict)
    ):
        raise CanonicalDataError("planned source transition is invalid")
    for row in current["sources"] + candidate["sources"]:
        if tuple(row) != PLANNED_SOURCE_FIELD_ORDER:
            raise CanonicalDataError(
                "planned source package field order differs"
            )
    current_fixed = dict(current)
    candidate_fixed = dict(candidate)
    current_fixed.pop("sources")
    candidate_fixed.pop("sources")
    current_scope = dict(current_fixed["scope"])
    candidate_scope = dict(candidate_fixed["scope"])
    current_scope.pop("reservation_count", None)
    candidate_scope.pop("reservation_count", None)
    current_fixed["scope"] = current_scope
    candidate_fixed["scope"] = candidate_scope
    if current_fixed != candidate_fixed:
        raise CanonicalDataError(
            "planned source non-reservation policy differs"
        )
    if (
        current["scope"].get("reservation_count") !=
        len(current["sources"]) or
        candidate["scope"].get("reservation_count") !=
        len(candidate["sources"])
    ):
        raise CanonicalDataError(
            "planned source reservation count differs"
        )
    current_rows = current["sources"]
    candidate_rows = candidate["sources"]
    if candidate_rows == current_rows:
        return
    if len(candidate_rows) != len(current_rows) - 1:
        raise CanonicalDataError(
            "planned source transition is not one exact removal"
        )
    candidate_ids = [row.get("source_id") for row in candidate_rows]
    removed = [
        row for row in current_rows
        if row.get("source_id") not in candidate_ids
    ]
    if (
        len(removed) != 1 or
        [row for row in current_rows if row not in removed] != candidate_rows
    ):
        raise CanonicalDataError(
            "planned source removal identity differs"
        )
    removed_families = removed[0].get("coverage_source_family_ids")
    source_families = source.get("coverage_source_ids")
    if (
        not isinstance(removed_families, list) or
        not set(removed_families).intersection(source_families)
    ):
        raise CanonicalDataError(
            "planned source removal is unrelated to the candidate"
        )


def apply_candidate_bundle(project_root, manifest_path):
    """Apply reviewed config bytes; network refresh remains a separate gate."""
    project_root = Path(project_root).resolve()
    candidates_root = (
        project_root / "live_data" / "feed_factory" / "candidates"
    ).resolve()
    raw_manifest_path = Path(manifest_path).absolute()
    manifest_path = (
        raw_manifest_path.parent.resolve() / raw_manifest_path.name
    )
    manifest_bytes = _read_frozen_file(manifest_path, candidates_root)
    manifest = strict_json_loads(manifest_bytes)
    _require_exact_keys(
        manifest,
        frozenset((
            "members",
            "predecessor_config_sha256",
            "predecessor_planned_sha256",
            "schema_version",
            "scientific_effect",
            "source_id",
            "status",
        )),
        "candidate bundle",
    )
    if (
        manifest["schema_version"] != BUNDLE_SCHEMA or
        manifest["scientific_effect"] != "none" or
        manifest["status"] != "CANDIDATE_NOT_ACTIVE"
    ):
        raise CanonicalDataError("candidate bundle policy is invalid")
    bundle_root = manifest_path.parent
    if bundle_root.name != sha256_bytes(manifest_bytes):
        raise CanonicalDataError("candidate bundle path identity differs")
    fixed_member_names = frozenset((
        "candidate.planned_sources.v1.json",
        "candidate.sources.v1.json",
        "fixture.normalized.json",
        "onboarding.receipt.json",
        "onboarding.spec.json",
    ))
    raw_member_names = sorted(
        name for name in manifest["members"]
        if RAW_MEMBER_RE.match(name)
    )
    if (
        len(raw_member_names) != 1 or
        frozenset(manifest["members"]) !=
        fixed_member_names | frozenset(raw_member_names)
    ):
        raise CanonicalDataError("candidate bundle member set differs")
    raw_member_name = raw_member_names[0]
    raw_name_match = RAW_MEMBER_RE.match(raw_member_name)

    config_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        "candidate.sources.v1.json",
    )
    planned_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        "candidate.planned_sources.v1.json",
    )
    normalized_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        "fixture.normalized.json",
    )
    raw_fixture_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        raw_member_name,
    )
    receipt_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        "onboarding.receipt.json",
    )
    spec_bytes = _read_bundle_member(
        bundle_root,
        manifest,
        "onboarding.spec.json",
    )
    candidate_config_object = strict_json_loads(config_bytes)
    candidate_planned_object = strict_json_loads(planned_bytes)
    normalized = strict_json_loads(normalized_bytes)
    receipt = strict_json_loads(receipt_bytes)
    spec = _validate_onboarding_spec(strict_json_loads(spec_bytes))
    if canonical_json_bytes(candidate_config_object) != config_bytes:
        raise CanonicalDataError("candidate config is not canonical JSON")
    if _package_json_bytes(candidate_planned_object) != planned_bytes:
        raise CanonicalDataError(
            "candidate planned config package order differs"
        )
    if canonical_json_bytes(normalized) != normalized_bytes:
        raise CanonicalDataError("normalized fixture is not canonical JSON")
    if canonical_json_bytes(receipt) != receipt_bytes:
        raise CanonicalDataError("onboarding receipt is not canonical JSON")
    if canonical_json_bytes(spec) != spec_bytes:
        raise CanonicalDataError("onboarding spec is not canonical JSON")
    _validate_receipt(receipt)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "candidate.json"
        path.write_bytes(config_bytes)
        load_config(path)

    config_path = project_root / "live_data" / "config" / "sources.v1.json"
    planned_path = (
        project_root / "live_data" / "config" /
        "planned_sources.v1.json"
    )
    current_config = safe_regular_file(
        config_path,
        project_root / "live_data" / "config",
    )
    current_planned = safe_regular_file(
        planned_path,
        project_root / "live_data" / "config",
    )
    predecessor_config = manifest["predecessor_config_sha256"]
    predecessor_planned = manifest["predecessor_planned_sha256"]
    candidate_config = sha256_bytes(config_bytes)
    candidate_planned = sha256_bytes(planned_bytes)
    current_config_sha = sha256_bytes(current_config)
    current_planned_sha = sha256_bytes(current_planned)
    if (
        manifest["source_id"] != receipt["source_id"] or
        receipt["source_id"] != spec["source"].get("source_id") or
        receipt["candidate_config_sha256"] != candidate_config or
        receipt["candidate_planned_sha256"] != candidate_planned or
        receipt["predecessor_config_sha256"] != predecessor_config or
        receipt["predecessor_planned_sha256"] != predecessor_planned or
        receipt["spec_sha256"] != sha256_bytes(spec_bytes) or
        receipt["fixture_bytes"] != spec["fixture"]["bytes"] or
        receipt["fixture_sha256"] != spec["fixture"]["sha256"] or
        raw_name_match.group(1) != receipt["fixture_sha256"] or
        len(raw_fixture_bytes) != receipt["fixture_bytes"] or
        sha256_bytes(raw_fixture_bytes) != receipt["fixture_sha256"]
    ):
        raise CanonicalDataError(
            "candidate manifest and onboarding receipt differ"
        )
    if (
        current_config_sha == candidate_config and
        current_planned_sha == candidate_planned
    ):
        raise CanonicalDataError("candidate bundle is already applied")
    if (
        current_config_sha not in (predecessor_config, candidate_config) or
        current_planned_sha != predecessor_planned
    ):
        raise CanonicalDataError(
            "candidate predecessor bytes do not match active configuration"
        )
    candidate_sources = [
        row for row in candidate_config_object.get("sources", [])
        if row.get("source_id") == receipt["source_id"]
    ]
    if len(candidate_sources) != 1:
        raise CanonicalDataError(
            "candidate source identity did not resolve exactly once"
        )
    source = candidate_sources[0]
    if source != spec["source"]:
        raise CanonicalDataError(
            "candidate source and onboarding spec differ"
        )
    if current_config_sha == predecessor_config:
        predecessor_object = strict_json_loads(current_config)
    else:
        predecessor_object = dict(candidate_config_object)
        predecessor_object["sources"] = [
            row for row in candidate_config_object["sources"]
            if row.get("source_id") != receipt["source_id"]
        ]
        if (
            sha256_bytes(canonical_json_bytes(predecessor_object)) !=
            predecessor_config
        ):
            raise CanonicalDataError(
                "candidate predecessor reconstruction differs"
            )
    regenerated = _validate_source_candidate(
        project_root,
        predecessor_object,
        source,
    )
    if canonical_json_bytes(regenerated) != config_bytes:
        raise CanonicalDataError(
            "candidate config is not the exact validated successor"
        )
    _validate_normalized_member(
        normalized,
        normalized_bytes,
        receipt,
        source,
    )
    rederived_records = normalize(
        source,
        raw_fixture_bytes,
        spec["fixture"]["retrieved_at"],
    )
    rederived_normalized = {
        "parser_id": "rmv2-live/%s" % source["adapter"],
        "records": rederived_records,
        "retrieved_at": spec["fixture"]["retrieved_at"],
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": receipt["fixture_sha256"],
        "source_id": receipt["source_id"],
    }
    if canonical_json_bytes(rederived_normalized) != normalized_bytes:
        raise CanonicalDataError(
            "raw fixture normalization differs from frozen normalized bytes"
        )
    if (
        _normalization_summary(rederived_records) !=
        spec["expected_normalization"]
    ):
        raise CanonicalDataError(
            "raw fixture normalization summary differs"
        )
    current_planned_object = strict_json_loads(current_planned)
    _validate_candidate_planned_transition(
        current_planned_object,
        candidate_planned_object,
        source,
    )
    expected_planned = _candidate_planned(
        current_planned_object,
        spec["reservation"],
    )
    if _package_json_bytes(expected_planned) != planned_bytes:
        raise CanonicalDataError(
            "candidate planned config and onboarding spec differ"
        )
    if (
        _normalization_summary(normalized["records"]) !=
        spec["expected_normalization"] or
        normalized["retrieved_at"] != spec["fixture"]["retrieved_at"]
    ):
        raise CanonicalDataError(
            "normalized fixture and onboarding spec differ"
        )
    # Active-first is recoverable: an interrupted apply temporarily retains the
    # reservation rather than making the source disappear from both sets.
    if current_config_sha == predecessor_config:
        atomic_write(config_path, config_bytes)
    atomic_write(planned_path, planned_bytes)
    return {
        "candidate_config_sha256": candidate_config,
        "candidate_planned_sha256": candidate_planned,
        "schema_version": "recession-monitor-v2.feed-onboarding-apply.v1",
        "source_id": manifest["source_id"],
        "status": "APPLIED_CONFIG_ONLY_REFRESH_REQUIRED",
    }
