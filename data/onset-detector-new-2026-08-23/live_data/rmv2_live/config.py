"""Strict configuration loading for publisher-direct collectors."""

from __future__ import absolute_import

import os
import re
import stat
from pathlib import Path
from urllib.parse import urlparse

from .canonical import CanonicalDataError, read_json


KNOWN_ADAPTERS = frozenset((
    "atsix_termstructure_xlsx",
    "bea_api",
    "dallas_wei_xlsx",
    "bea_regional_cainc_zip",
    "bls_json",
    "census_api",
    "census_btos_xlsx",
    "census_qss_timeseries_zip",
    "cfpb_credit_trends_csv",
    "cfpb_mortgage_performance_state_csv",
    "cleveland_nowcast_json",
    "dbnomics_json",
    "dol_eta539_csv",
    "dol_ui_weekly_claims_report_html",
    "eia_v2_json",
    "fdic_aggregate_json",
    "fed_ddp_csv",
    "fiscaldata_json",
    "fhfa_hpi_at_geo_csv",
    "fhfa_hpi_csv",
    "fred_graph_csv",
    "fred_json_api",
    "fred_json_api_vintages",
    "fred_json_api_vintages_deep",
    "forecast_sep_pdf",
    "forecast_xlsx",
    "geo_grid_json",
    "geo_panel_json",
    "greenbook_row_xlsx",
    "nber_macrohistory_dat",
    "nyfed_reference_rate_json",
    "ofr_fsi_csv",
    "openfema_disaster_declarations_json",
    "philadelphia_ads_xlsx",
    "raw_capture",
    "regional_survey_xlsx",
    "socrata_json",
    "tabular_csv",
    "treasury_dts_json",
    "treasury_dts_operating_cash",
    "treasury_mts_totals_json",
    "treasury_yield_xml",
    "tsa_passenger_html",
))
TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
ENV_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
# B-LAND-3D: a non-primary provider's deep vintage lane tags its emitted
# <BASE>.<TAG>.DEEPASOF<YYYYMMDD> family so the append-only family-prefix gate is
# per-(base, provider). The tag is uppercase-alnum and may NOT begin with "ASOF"
# or "DEEP" -- either would re-open the very .ASOF / .DEEPASOF prefix collision
# the tag exists to avoid (§7.2 also prohibits ".ASOFDEEP").
VINTAGE_PROVIDER_TAG_RE = re.compile(r"^[A-Z][A-Z0-9]{1,15}$")


def load_env_file(path):
    """Load a small KEY=VALUE file without shell evaluation."""
    path = Path(path)
    if not path.exists():
        return
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = None
    try:
        descriptor = os.open(str(path), os.O_RDONLY | nofollow)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise CanonicalDataError("local env must be one regular file")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise CanonicalDataError("local env permissions must exclude group and other")
        chunks = []
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8", errors="strict")
    except OSError as exc:
        raise CanonicalDataError("local env cannot be safely opened") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise CanonicalDataError("invalid env line %d" % line_number)
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not ENV_RE.match(key):
            raise CanonicalDataError("invalid env key on line %d" % line_number)
        if key not in os.environ:
            os.environ[key] = value


def _require_keys(mapping, required, context, optional=()):
    keys = set(mapping)
    missing = sorted(set(required) - keys)
    extra = sorted(keys - set(required) - set(optional))
    if missing or extra:
        raise CanonicalDataError(
            "%s key mismatch; missing=%r extra=%r" % (context, missing, extra)
        )


def load_config(path):
    config = read_json(path)
    _require_keys(
        config,
        ("api", "catalog_registry", "schema_version", "service", "sources", "store"),
        "configuration",
    )
    if config["schema_version"] != "recession-monitor-v2.live-data-config.v1":
        raise CanonicalDataError("unsupported live-data configuration schema")
    if not isinstance(config["catalog_registry"], str) or not config["catalog_registry"]:
        raise CanonicalDataError("catalog_registry is invalid")
    catalog_path = Path(config["catalog_registry"])
    if catalog_path.is_absolute() or ".." in catalog_path.parts:
        raise CanonicalDataError("catalog_registry must be a project-relative path")

    api = config["api"]
    _require_keys(api, ("host", "port", "website_poll_seconds"), "api")
    if api["host"] != "127.0.0.1":
        raise CanonicalDataError("API must bind to 127.0.0.1")
    if not isinstance(api["port"], int) or not (1024 <= api["port"] <= 65535):
        raise CanonicalDataError("API port is invalid")
    if (
        not isinstance(api["website_poll_seconds"], int) or
        isinstance(api["website_poll_seconds"], bool) or
        api["website_poll_seconds"] < 5
    ):
        raise CanonicalDataError("website_poll_seconds is invalid")

    service = config["service"]
    _require_keys(service, ("refresh_tick_seconds",), "service")
    if (
        not isinstance(service["refresh_tick_seconds"], int) or
        isinstance(service["refresh_tick_seconds"], bool) or
        service["refresh_tick_seconds"] < 60
    ):
        raise CanonicalDataError("refresh_tick_seconds is invalid")

    store = config["store"]
    _require_keys(store, ("public", "root", "runtime"), "store")
    for name in ("public", "root", "runtime"):
        value = store[name]
        if not isinstance(value, str) or not value:
            raise CanonicalDataError("store.%s is invalid" % name)
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise CanonicalDataError("store.%s must be project-relative" % name)
    store_paths = [Path(store[name]) for name in ("public", "root", "runtime")]
    for index, left in enumerate(store_paths):
        for right in store_paths[index + 1:]:
            if (
                left == right or
                left in right.parents or
                right in left.parents
            ):
                raise CanonicalDataError("store roots must be pairwise disjoint")

    seen = set()
    if not isinstance(config["sources"], list) or not config["sources"]:
        raise CanonicalDataError("sources must be a nonempty list")
    for source in config["sources"]:
        if not isinstance(source, dict):
            raise CanonicalDataError("source entry is not an object")
        _require_keys(
            source,
            (
                "adapter",
                "allowed_hosts",
                "coverage_source_ids",
                "enabled",
                "endpoint",
                "expected_content_types",
                "frequency",
                "information_set_mode",
                "label",
                "max_bytes",
                "method_version",
                "poll_seconds",
                "publisher",
                "publisher_release_clock",
                "rights_status",
                "secret_env",
                "secret_required",
                "series",
                "source_id",
                "value_status",
            ),
            "source",
            optional=(
                "archival",
                "snapshot_projection",
                "vintage_provider_tag",
            ),
        )
        source_id = source["source_id"]
        if (
            not isinstance(source_id, str) or
            not TOKEN_RE.match(source_id) or
            source_id in (".", "..")
        ):
            raise CanonicalDataError("source_id is invalid")
        if source_id in seen:
            raise CanonicalDataError("duplicate source_id: %s" % source_id)
        seen.add(source_id)
        if source["adapter"] not in KNOWN_ADAPTERS:
            raise CanonicalDataError("unknown adapter for %s" % source_id)
        if not isinstance(source["enabled"], bool):
            raise CanonicalDataError("%s enabled is invalid" % source_id)
        if "archival" in source:
            # An archival (frozen-admission) row records a deep-vintage head that
            # the resident service must never fetch/refresh; a fetchable archival
            # row would clobber the audited offline bytes, so archival ⇒ disabled.
            if not isinstance(source["archival"], bool):
                raise CanonicalDataError("%s archival is invalid" % source_id)
            if source["archival"] and source["enabled"]:
                raise CanonicalDataError(
                    "%s archival source must be enabled:false" % source_id
                )
        if "snapshot_projection" in source:
            if source["snapshot_projection"] not in (
                "archival_panel.v1", "greenbook_vintage_panel.v1"
            ):
                raise CanonicalDataError(
                    "%s snapshot_projection is invalid" % source_id
                )
            if not source.get("archival") or source["enabled"]:
                raise CanonicalDataError(
                    "%s archival panel projection requires archival:true and "
                    "enabled:false" % source_id
                )
        if "vintage_provider_tag" in source:
            tag = source["vintage_provider_tag"]
            if source["adapter"] != "fred_json_api_vintages_deep":
                raise CanonicalDataError(
                    "%s vintage_provider_tag is only valid on the deep vintage "
                    "lane" % source_id
                )
            if (
                not isinstance(tag, str) or
                not VINTAGE_PROVIDER_TAG_RE.match(tag) or
                tag.startswith("ASOF") or
                tag.startswith("DEEP")
            ):
                raise CanonicalDataError(
                    "%s vintage_provider_tag is invalid" % source_id
                )
        if not isinstance(source["secret_required"], bool):
            raise CanonicalDataError("%s secret_required is invalid" % source_id)
        if source["secret_required"] and not source["secret_env"]:
            raise CanonicalDataError("%s requires a named secret" % source_id)
        parsed = urlparse(source["endpoint"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise CanonicalDataError("%s endpoint must use HTTPS" % source_id)
        allowed_hosts = source["allowed_hosts"]
        if (
            not isinstance(allowed_hosts, list) or
            not allowed_hosts or
            any(not isinstance(item, str) or not item for item in allowed_hosts)
        ):
            raise CanonicalDataError("%s allowed_hosts is invalid" % source_id)
        if len(set(allowed_hosts)) != len(allowed_hosts):
            raise CanonicalDataError("%s allowed_hosts contains duplicates" % source_id)
        if parsed.hostname not in allowed_hosts:
            raise CanonicalDataError("%s endpoint host is not allowlisted" % source_id)
        if (
            not isinstance(source["expected_content_types"], list) or
            not source["expected_content_types"] or
            any(not isinstance(item, str) or not item for item in source["expected_content_types"])
        ):
            raise CanonicalDataError("%s expected_content_types is invalid" % source_id)
        if (
            not isinstance(source["coverage_source_ids"], list) or
            not source["coverage_source_ids"] or
            any(not isinstance(item, str) or not item for item in source["coverage_source_ids"])
        ):
            raise CanonicalDataError("%s coverage_source_ids is invalid" % source_id)
        if len(set(source["coverage_source_ids"])) != len(source["coverage_source_ids"]):
            raise CanonicalDataError("%s coverage_source_ids contains duplicates" % source_id)
        if not isinstance(source["poll_seconds"], int) or source["poll_seconds"] < 60:
            raise CanonicalDataError("%s poll_seconds is invalid" % source_id)
        if not isinstance(source["max_bytes"], int) or source["max_bytes"] < 1024:
            raise CanonicalDataError("%s max_bytes is invalid" % source_id)
        if source["information_set_mode"] not in (
            "current_revised",
            "archive_snapshot_asof",
            "stitched_strict_first_release",
            "substituted_diagnostic",
        ):
            raise CanonicalDataError("%s information_set_mode is invalid" % source_id)
        if not isinstance(source["series"], dict):
            raise CanonicalDataError("%s series is invalid" % source_id)
        if (
            source.get("snapshot_projection") == "archival_panel.v1" and
            source["series"].get("forecast_shape") != "spf_individual"
        ):
            raise CanonicalDataError(
                "%s archival panel projection is only valid for the "
                "spf_individual shape" % source_id
            )
        if (
            source.get("snapshot_projection") == "greenbook_vintage_panel.v1" and
            source["adapter"] != "greenbook_row_xlsx"
        ):
            raise CanonicalDataError(
                "%s greenbook vintage panel projection is only valid for the "
                "greenbook_row_xlsx adapter" % source_id
            )
        if (
            source["secret_env"] is not None and
            (
                not isinstance(source["secret_env"], str) or
                not ENV_RE.match(source["secret_env"])
            )
        ):
            raise CanonicalDataError("%s secret_env is invalid" % source_id)
    return config
