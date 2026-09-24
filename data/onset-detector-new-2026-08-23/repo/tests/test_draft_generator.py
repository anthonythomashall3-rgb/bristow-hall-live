"""B-FAST-2 §3.2 — the deterministic draft generator.

`generate_draft(probe_receipt, reservation_row, ...)` turns a probe receipt plus
a reservation row into a `recession-monitor-v2.feed-discovery-spec.v1` draft with
every field byte-derived from its inputs — nothing invented. Three derivation
rules are mechanized and pinned here: information_set_mode, poll_seconds, and the
rights ladder. Rights UNRESOLVED never blocks admission; it gates display only
(§4.9).
"""
from __future__ import absolute_import

import copy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import canonical_json_bytes
from live_data.rmv2_live.draft_generator import (
    CONSERVATIVE_POLL_SECONDS,
    generate_draft,
)
from live_data.rmv2_live.feed_factory import _load_discovery_spec


# ---- input builders -------------------------------------------------------

def _probe(**over):
    receipt = {
        "source_id": "usda_snap_current",
        "adapter": "tabular_csv",
        "publisher": "USDA",
        "endpoint": "https://www.fns.usda.gov/pd/snap.csv",
        "allowed_hosts": ["www.fns.usda.gov"],
        "content_type": "text/csv",
        "observation_frequency": "monthly",
        "modal_cadence_seconds": 86400,
        "record_count": 412,
        "first_observation_period": "1969-01",
        "last_observation_period": "2026-06",
        "payload_bytes": 51234,
        "response_schema_sha256": "a" * 64,
        "vintage_lane_proven": False,
        "series": {
            "series_id": "SNAP_PARTICIPATION",
            "label": "SNAP participation",
            "unit": "persons",
        },
        "value_status": "actual",
        "declared_license": None,
        "label": "SNAP participation (USDA FNS)",
    }
    receipt.update(over)
    return receipt


def _reservation(**over):
    row = {
        "source_id": "usda_snap",
        "registry_status": "RESERVED_NOT_ENABLED",
        "enabled": False,
        "publisher": "USDA",
        "endpoint": "https://www.fns.usda.gov/pd/snap.csv",
        "endpoint_status": "resolved",
        "auth_env": None,
        "cadence": "monthly",
        "release_timezone": "America/New_York",
        "release_clock": "monthly",
        "observation_period": "1969+",
        "revision_policy": "current_revised",
        "rights": "public_government_source_with_attribution",
        "parser_version": None,
        "role": "diagnostic",
        "clock_notes": "",
        "split_or_bias_guard": "",
        "coverage_source_family_ids": ["usda_snap"],
    }
    row.update(over)
    return row


REGISTRY = {"USDA": "public_domain_with_attribution"}
LICENSE_TABLE = {"CC0-1.0": "cc0_public_domain_dedication"}
FEDERAL_HOSTS = frozenset(("www.fns.usda.gov", "data.bls.gov"))


def _gen(probe, reservation, **kw):
    kw.setdefault("rights_registry", REGISTRY)
    kw.setdefault("license_table", LICENSE_TABLE)
    kw.setdefault("federal_hosts", FEDERAL_HOSTS)
    return generate_draft(probe, reservation, **kw)


# ---- information_set_mode --------------------------------------------------

def test_proven_vintage_lane_yields_archive_snapshot_asof():
    result = _gen(_probe(vintage_lane_proven=True), _reservation())
    assert result["emitted"] is True
    assert (
        result["draft"]["source"]["information_set_mode"]
        == "archive_snapshot_asof"
    )


def test_no_vintage_evidence_yields_current_revised_not_archive():
    result = _gen(_probe(vintage_lane_proven=False), _reservation())
    assert result["emitted"] is True
    mode = result["draft"]["source"]["information_set_mode"]
    assert mode == "current_revised"
    assert mode != "archive_snapshot_asof"


def test_neither_lane_established_blocks_clock_unresolved_no_draft():
    # No vintage proof AND no current-lane evidence (no records, no periods).
    result = _gen(
        _probe(
            vintage_lane_proven=False,
            record_count=0,
            first_observation_period=None,
            last_observation_period=None,
        ),
        _reservation(),
    )
    assert result["emitted"] is False
    assert result["draft"] is None
    assert result["blocker"] == "CLOCK_UNRESOLVED"


# ---- rights ladder ---------------------------------------------------------

def test_rights_ladder_registry_beats_declared_beats_statutory():
    # All three rungs are satisfiable at once; registry must win.
    probe = _probe(declared_license="CC0-1.0")  # rung 2 available
    reservation = _reservation()  # publisher USDA in REGISTRY (rung 1),
    # endpoint host in FEDERAL_HOSTS (rung 3)
    result = _gen(probe, reservation)
    assert result["rights_rung"] == "RIGHTS_REGISTRY"
    assert (
        result["draft"]["source"]["rights_status"]
        == "public_domain_with_attribution"
    )

    # Remove rung 1 -> declared license wins over statutory.
    result2 = _gen(probe, reservation, rights_registry={})
    assert result2["rights_rung"] == "DECLARED_LICENSE"
    assert (
        result2["draft"]["source"]["rights_status"]
        == "cc0_public_domain_dedication"
    )

    # Remove rungs 1 and 2 -> statutory (federal host) wins.
    result3 = _gen(
        _probe(declared_license=None),
        reservation,
        rights_registry={},
    )
    assert result3["rights_rung"] == "STATUTORY"
    assert "17_usc_105" in result3["draft"]["source"]["rights_status"]


def test_publisher_absent_from_every_rung_is_unresolved_but_admitted():
    # Publisher not in registry, no declared license, host not federal.
    probe = _probe(
        endpoint="https://example.org/x.csv",
        allowed_hosts=["example.org"],
        declared_license=None,
    )
    reservation = _reservation(
        publisher="Private Vendor",
        endpoint="https://example.org/x.csv",
    )
    result = _gen(probe, reservation, rights_registry={}, federal_hosts=frozenset())
    assert result["emitted"] is True
    assert result["rights_rung"] == "UNRESOLVED"
    source = result["draft"]["source"]
    assert source["rights_status"] == "UNRESOLVED"
    assert source["display_permitted"] is False
    # §4.9: rights are not a coverage gap — the source is still admitted/computing.
    assert source["enabled"] is True


def test_a_siblings_rights_are_never_copied_to_an_unresolved_publisher():
    # A different publisher (BLS) has rights in the registry; the reservation's
    # own publisher does not. Its rights must NOT be inherited from the sibling.
    registry = {"BLS": "public_domain_with_attribution"}
    probe = _probe(
        publisher="Obscure Agency",
        endpoint="https://obscure.example/x.csv",
        allowed_hosts=["obscure.example"],
        declared_license=None,
    )
    reservation = _reservation(
        publisher="Obscure Agency",
        endpoint="https://obscure.example/x.csv",
    )
    result = _gen(
        probe, reservation, rights_registry=registry, federal_hosts=frozenset()
    )
    assert result["draft"]["source"]["rights_status"] == "UNRESOLVED"
    assert result["rights_rung"] == "UNRESOLVED"


# ---- poll_seconds ----------------------------------------------------------

def test_unknown_cadence_uses_conservative_interval_and_marks_confidence():
    result = _gen(_probe(modal_cadence_seconds=None), _reservation())
    source = result["draft"]["source"]
    assert source["poll_seconds"] == CONSERVATIVE_POLL_SECONDS
    assert source["schedule_confidence"] == "unknown"


def test_known_cadence_uses_measured_interval_and_marks_confidence():
    result = _gen(_probe(modal_cadence_seconds=86400), _reservation())
    source = result["draft"]["source"]
    assert source["poll_seconds"] == 86400
    assert source["schedule_confidence"] == "measured"


# ---- schema + determinism --------------------------------------------------

def test_generated_draft_validates_against_the_live_draft_schema(tmp_path):
    result = _gen(_probe(), _reservation())
    draft = result["draft"]
    # Persist under a temp project's drafts root and load it through the live
    # discovery-spec validator the feed factory uses.
    drafts_dir = tmp_path / "live_data" / "feed_factory" / "drafts"
    drafts_dir.mkdir(parents=True)
    draft_path = drafts_dir / "generated.v1.json"
    draft_path.write_bytes(canonical_json_bytes(draft))
    loaded = _load_discovery_spec(tmp_path, draft_path)
    assert loaded["schema_version"] == "recession-monitor-v2.feed-discovery-spec.v1"


def test_byte_determinism_identical_inputs_yield_identical_draft():
    probe = _probe()
    reservation = _reservation()
    a = _gen(copy.deepcopy(probe), copy.deepcopy(reservation))
    b = _gen(copy.deepcopy(probe), copy.deepcopy(reservation))
    assert canonical_json_bytes(a["draft"]) == canonical_json_bytes(b["draft"])
