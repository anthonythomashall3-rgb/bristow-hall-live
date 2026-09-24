"""B-FAST-2 §2 (FAM1-reduced): the three CDX coverage families.

Scope registration only. A coverage family is a provenance SCOPE bucket — never
an identity binding, never a channel (FAM1 §0, §0a). These assertions pin:

  * the three genuinely-new CDX family ids are registered (registry grows >134),
  * the registry schema carries no channel / weight / member column and no
    registered family id string-matches a model CHANNELS name (§0a.1, §0a.2),
  * BLS/DOL rights are the verbatim publisher clauses, access_class A, never
    license-blocked (FAM1 §1c.3, §2),
  * the CDX lane is marked a DISTINCT third lane, never archive_snapshot_asof
    (FAM1 §1c.2 / §3.6).

The stale 1a/1b families and the unmeasured 7 SDMX candidates are intentionally
NOT registered by this batch — see the B-FAST-2 receipt for the disagreement.
"""
from __future__ import absolute_import

import csv
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REGISTRY_PATH = (
    PROJECT_ROOT / "data_vault" / "catalog" / "external_source_registry.csv"
)

CDX_FAMILIES = {
    "bls_empsit_cdx": {
        "publisher": "BLS",
        "access_class": "A",
        "rights_status": "public_domain_with_attribution",
    },
    "bls_jolts_cdx": {
        "publisher": "BLS",
        "access_class": "A",
        "rights_status": "public_domain_with_attribution",
    },
    "dol_ui_cdx": {
        "publisher": "DOL_ETA",
        "access_class": "A",
        "rights_status": "public_government_source_with_attribution",
    },
}

# The model's channel names (method_source/index_v1.py::CHANNELS). A registered
# family id must never equal or embed one of these — that would smuggle an
# inherited channel assumption through the provenance layer (FAM1 §0a).
CHANNEL_NAMES = frozenset((
    "labor",
    "realactivity",
    "creditequity",
    "finconditions",
    "housingincome",
))

CHANNEL_FIELD_TOKENS = ("channel", "weight", "member", "instrument_member")


def _rows():
    with REGISTRY_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _channels_from_source():
    src = (PROJECT_ROOT / "method_source" / "index_v1.py").read_text()
    block = re.search(r"CHANNELS\s*=\s*\{(.*?)\n\}", src, re.S).group(1)
    keys = re.findall(r'"([a-z_]+)":', block)
    return frozenset(keys)


def test_channel_names_fixture_matches_source():
    # Guard against drift: if CHANNELS in index_v1.py changes, this test must be
    # revisited rather than silently passing on a stale fixture.
    assert _channels_from_source() == CHANNEL_NAMES


def test_registry_grew_past_134_and_holds_the_three_cdx_families():
    rows = _rows()
    assert len(rows) > 134, len(rows)
    ids = {r["source_id"] for r in rows}
    for family_id in CDX_FAMILIES:
        assert family_id in ids, family_id


def test_registry_schema_carries_no_channel_or_member_column():
    header = _rows()[0].keys()
    for column in header:
        low = column.lower()
        for token in CHANNEL_FIELD_TOKENS:
            assert token not in low, (column, token)


def test_no_registered_family_id_is_a_channel_name():
    for row in _rows():
        family_id = row["source_id"]
        assert family_id not in CHANNEL_NAMES, family_id
        # embedding guard: a would-be `labor_cdx` etc. that string-matches a
        # channel name as a token also reds here.
        tokens = set(re.split(r"[_.]", family_id))
        assert tokens.isdisjoint(CHANNEL_NAMES), family_id


def test_cdx_rights_are_verbatim_publisher_clauses_never_license_blocked():
    by_id = {r["source_id"]: r for r in _rows()}
    for family_id, expected in CDX_FAMILIES.items():
        row = by_id[family_id]
        assert row["publisher"] == expected["publisher"], family_id
        assert row["access_class"] == expected["access_class"], family_id
        assert row["rights_status"] == expected["rights_status"], family_id
        assert "license_required" not in row["rights_status"], family_id
        # A registered CDX family is NOT admission: it must not be blocked or
        # target-quarantined (feed_factory._validate_family_bindings), so its
        # access_class stays out of {C, D} and its role out of the block set.
        assert row["access_class"] not in ("C", "D"), family_id
        assert row["role"] not in ("licensed_only", "target_quarantine"), (
            family_id
        )


def test_cdx_is_a_distinct_third_lane_not_archive_snapshot_asof():
    by_id = {r["source_id"]: r for r in _rows()}
    for family_id in CDX_FAMILIES:
        behavior = by_id[family_id]["revision_and_vintage_behavior"]
        # FAM1 §1c.2 / §3.6: the CDX lane is a distinct third lane, never merged
        # with or relabeled as archive_snapshot_asof, and it carries no
        # real-time display claim; a distinct digest marks a revision, not a
        # re-crawl (§1c.4).
        assert "not_archive_snapshot_asof" in behavior, family_id
        assert "distinct_digest" in behavior, family_id
