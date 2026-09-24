"""Deterministic probe-receipt -> feed-discovery draft generation (B-FAST-2 §3).

`generate_draft` replaces hand-authored drafts with a byte-derived transform:
given a probe receipt (what the bytes proved) and the reservation row it
consumes, it emits a `recession-monitor-v2.feed-discovery-spec.v1` draft.

Nothing is invented. Every source field is copied or mechanically derived from
the two inputs. Three derivations are rule-governed rather than eyeballed:

  * ``information_set_mode`` — ``archive_snapshot_asof`` ONLY when the probe
    proves a vintage lane from bytes; otherwise ``current_revised`` when a
    current lane is established; when neither is established the generator emits
    the typed blocker ``CLOCK_UNRESOLVED`` and NO draft (§3, §13).
  * ``poll_seconds`` — the measured modal cadence when known, else the
    conservative fixed interval already used in the repo, with
    ``schedule_confidence: unknown`` (§8.3). A schedule is never invented.
  * ``rights_status`` — a fully mechanized ordered ladder (registry ->
    declared-license -> statutory -> unresolved). ``UNRESOLVED`` never blocks
    admission; it sets ``display_permitted: false`` and leaves ``enabled: true``
    (§4.9). Rights are never inferred from a sibling source.

The generator only *applies* rights policy (the publisher rights registry, the
license table, the federal-host list); it never extends it — that is an owner
act (§22.6).
"""
from __future__ import absolute_import

from urllib.parse import urlparse

DRAFT_SCHEMA = "recession-monitor-v2.feed-discovery-spec.v1"

# The conservative fixed poll interval already used by the repo's hand-authored
# vintage drafts (see live_data/feed_factory/drafts/fred_icsa_api_vintages.v1
# poll_seconds=21600). Used when a source's modal cadence is unmeasured; a
# schedule is never invented (§8.3).
CONSERVATIVE_POLL_SECONDS = 21600

# 17 U.S.C. 105 public-domain result for a US-federal-works host (rung 3).
STATUTORY_RIGHTS = "public_domain_17_usc_105"

# Rights values that carry one of these markers may be used and computed but not
# charted or republished (§2.3): display is withheld even when rights resolve.
_PROPRIETARY_MARKERS = (
    "proprietary",
    "restricted",
    "license_required",
    "not_redistributable",
)

_CONTENT_TYPE_MAP = {
    "text/csv": "text/csv",
    "application/json": "application/json",
    "application/xml": "application/xml",
    "text/xml": "text/xml",
    "text/html": "text/html",
    "application/pdf": "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


def _host(url):
    return (urlparse(str(url or "")).hostname or "").lower()


def _has_current_lane(probe_receipt):
    """A current lane is established iff the probe returned dated observations."""
    count = probe_receipt.get("record_count")
    first = probe_receipt.get("first_observation_period")
    last = probe_receipt.get("last_observation_period")
    return (
        isinstance(count, int) and count > 0 and
        isinstance(first, str) and first and
        isinstance(last, str) and last
    )


def _resolve_information_set_mode(probe_receipt):
    """Return a mode string, or None when the clock is unresolved (no draft)."""
    if probe_receipt.get("vintage_lane_proven") is True:
        return "archive_snapshot_asof"
    if _has_current_lane(probe_receipt):
        return "current_revised"
    return None


def _resolve_poll(probe_receipt):
    cadence = probe_receipt.get("modal_cadence_seconds")
    if isinstance(cadence, int) and cadence > 0:
        return cadence, "measured"
    return CONSERVATIVE_POLL_SECONDS, "unknown"


def _resolve_rights(reservation_row, probe_receipt, rights_registry,
                    license_table, federal_hosts):
    """Ordered ladder, first match wins. Returns (rung, rights_status).

    Never infers from a sibling source: rung 1 keys on THIS reservation's own
    publisher having a curated registry entry, not on copying another row.
    """
    publisher = reservation_row.get("publisher")
    if publisher in (rights_registry or {}):
        return "RIGHTS_REGISTRY", rights_registry[publisher]
    declared = probe_receipt.get("declared_license")
    if isinstance(declared, str) and declared in (license_table or {}):
        return "DECLARED_LICENSE", license_table[declared]
    host = _host(reservation_row.get("endpoint"))
    if host and host in (federal_hosts or frozenset()):
        return "STATUTORY", STATUTORY_RIGHTS
    return "UNRESOLVED", "UNRESOLVED"


def _display_permitted(rung, rights_status):
    if rung == "UNRESOLVED":
        return False
    lowered = rights_status.lower()
    return not any(marker in lowered for marker in _PROPRIETARY_MARKERS)


def _max_bytes(payload_bytes):
    """Smallest power of two >= 2x the observed payload, floored at 1 MiB."""
    target = max(int(payload_bytes or 0) * 2, 1 << 20)
    cap = 1 << 20
    while cap < target:
        cap <<= 1
    return cap


def _expected_content_types(content_type):
    base = str(content_type or "").split(";", 1)[0].strip().lower()
    mapped = _CONTENT_TYPE_MAP.get(base)
    return [mapped] if mapped else ["application/octet-stream"]


def _blocked(reservation_id, blocker):
    return {
        "emitted": False,
        "draft": None,
        "blocker": blocker,
        "rights_rung": None,
        "reservation_id": reservation_id,
    }


def generate_draft(probe_receipt, reservation_row, *, rights_registry,
                   license_table, federal_hosts):
    """Emit a discovery-spec draft, or a typed blocker when the clock is unset.

    Result: ``{"emitted": bool, "draft": dict|None, "rights_rung": str|None,
    "blocker": str|None, "reservation_id": str}``. Identical inputs produce a
    byte-identical draft.
    """
    reservation_id = reservation_row.get("source_id")

    mode = _resolve_information_set_mode(probe_receipt)
    if mode is None:
        # Neither a vintage lane nor a current lane is established from bytes:
        # assign no mode, emit no draft (§3, §13).
        return _blocked(reservation_id, "CLOCK_UNRESOLVED")

    poll_seconds, schedule_confidence = _resolve_poll(probe_receipt)
    rung, rights_status = _resolve_rights(
        reservation_row,
        probe_receipt,
        rights_registry,
        license_table,
        federal_hosts,
    )
    display_permitted = _display_permitted(rung, rights_status)

    source_id = probe_receipt.get("source_id")
    auth_env = reservation_row.get("auth_env")
    coverage = sorted(reservation_row.get("coverage_source_family_ids") or [])
    allowed_hosts = sorted(
        str(host).lower() for host in (probe_receipt.get("allowed_hosts") or [])
    )
    series = probe_receipt.get("series") or {}

    release_clock = reservation_row.get("release_clock") or "unspecified"
    publisher_release_clock = (
        "%s; generated from probe measurement; publisher first-release time "
        "remains null unless separately proven" % release_clock
    )

    source = {
        "adapter": probe_receipt.get("adapter"),
        "allowed_hosts": allowed_hosts,
        "coverage_source_ids": coverage,
        "display_permitted": display_permitted,
        "enabled": True,
        "endpoint": probe_receipt.get("endpoint"),
        "expected_content_types": _expected_content_types(
            probe_receipt.get("content_type")
        ),
        "frequency": probe_receipt.get("observation_frequency"),
        "information_set_mode": mode,
        "label": probe_receipt.get("label"),
        "max_bytes": _max_bytes(probe_receipt.get("payload_bytes")),
        "method_version": "%s.generated_from_probe.v1" % source_id,
        "poll_seconds": poll_seconds,
        "publisher": reservation_row.get("publisher"),
        "publisher_release_clock": publisher_release_clock,
        "rights_status": rights_status,
        "schedule_confidence": schedule_confidence,
        "secret_env": auth_env,
        "secret_required": auth_env is not None,
        "series": {
            "label": series.get("label"),
            "series_id": series.get("series_id"),
            "unit": series.get("unit"),
        },
        "source_id": source_id,
        "value_status": probe_receipt.get("value_status") or "actual",
    }

    draft = {
        "activation": {
            "scientific_effect": "none",
            "website_effect": "measurement_catalog_and_status_only",
        },
        "reservation": {
            "action": "remove_exact",
            "source_id": reservation_id,
        },
        "schema_version": DRAFT_SCHEMA,
        "source": source,
    }

    return {
        "emitted": True,
        "draft": draft,
        "rights_rung": rung,
        "blocker": None,
        "reservation_id": reservation_id,
    }
