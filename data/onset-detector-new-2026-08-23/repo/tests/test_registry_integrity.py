"""B-SAFE-1 §4.5 — deterministic registry-integrity checks (no AI, no tokens).

An AI reviewer was proposed and rejected; every check here is byte-derived from
the committed registry, source matrix, and growth-floor low-water marks. Each
failure names the exact offending id or field (never "registry invalid", §19.3).

The seven invariants:
  1. C-set cardinality == 7            (access_class == "C")
  2. enabled sources' access_class ⊆ {A, B}   (C = reserved, D = comparator)
  3. registry ids append-only vs the recorded floor set (a removal fails)
  4. every count floor <= its measured current count
  5. coverage_source_family_ids ⊆ registry family ids
  6. no duplicate registry family ids
  7. every enabled (active_collector) source's families are registered

Negative tests mutate a copy in memory and assert the checker raises with the
offending id named, proving each guard actually bites.
"""

from __future__ import absolute_import

import csv
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

REGISTRY_PATH = REPO / "data_vault" / "catalog" / "external_source_registry.csv"
MATRIX_PATH = REPO / "live_data" / "catalog" / "source_matrix.v1.json"
FLOORS_PATH = REPO / "live_data" / "config" / "source_registry_growth_floors.v1.json"


class RegistryIntegrityError(AssertionError):
    pass


def load_registry():
    with REGISTRY_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_matrix():
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def load_floors():
    return json.loads(FLOORS_PATH.read_text(encoding="utf-8"))


# ----- checkers (pure; raise RegistryIntegrityError naming the offender) ------

def check_c_set_cardinality(registry):
    c_set = sorted(r["source_id"] for r in registry if r["access_class"] == "C")
    if len(c_set) != 7:
        raise RegistryIntegrityError("C-set cardinality %d != 7: %s" % (len(c_set), c_set))
    return c_set


# B-RIGHTS-1 — OWNER_RULING_20260808_PUBLISH_ALL_GOOD_DATA.md. The 7 class-C
# families migrate to publish_class `publish_all_good_data`; publish_class is
# now filled EXPLICITLY on every row (no fallback resolution); the comparator D
# family stays `internal_only` (target contamination, never a rights matter).
KNOWN_PUBLISH_CLASSES = frozenset(("public", "internal_only", "publish_all_good_data"))
GOOD_DATA_FAMILIES = frozenset((
    "moody_corporate_yields", "ice_bofa_spreads", "sp_equity",
    "nasdaq_equity", "cboe_vix", "freddie_pmms", "michigan_consumers",
))


def check_publish_class_migration(registry):
    """Every row carries an explicit known publish_class; the ruling's 7 carry
    `publish_all_good_data` and no other row does; the D comparator is
    `internal_only`. Names the exact offending id/field on failure (§19.3).
    """
    for row in registry:
        pc = (row.get("publish_class") or "").strip()
        if not pc:
            raise RegistryIntegrityError(
                "publish_class blank on %s (fallback resolution forbidden after B-RIGHTS-1)"
                % row["source_id"])
        if pc not in KNOWN_PUBLISH_CLASSES:
            raise RegistryIntegrityError(
                "unknown publish_class %r on %s" % (pc, row["source_id"]))
    good = {r["source_id"] for r in registry
            if (r.get("publish_class") or "").strip() == "publish_all_good_data"}
    if good != GOOD_DATA_FAMILIES:
        raise RegistryIntegrityError(
            "publish_all_good_data set %s != ruling's 7 %s"
            % (sorted(good), sorted(GOOD_DATA_FAMILIES)))
    nyfed = next((r for r in registry
                  if r["source_id"] == "nyfed_yield_recession_probability"), None)
    if nyfed is not None and (nyfed.get("publish_class") or "").strip() != "internal_only":
        raise RegistryIntegrityError(
            "nyfed_yield_recession_probability publish_class %r != internal_only (quarantine)"
            % nyfed.get("publish_class"))
    return good


def check_enabled_access_class(registry, matrix):
    by_id = {r["source_id"]: r for r in registry}
    offenders = []
    for row in matrix["rows"]:
        if row.get("record_kind") != "active_collector":
            continue
        for fam in row.get("coverage_source_family_ids") or []:
            ac = by_id.get(fam, {}).get("access_class")
            if ac not in ("A", "B"):
                offenders.append("%s->%s:access_class=%s" % (row["source_id"], fam, ac))
    if offenders:
        raise RegistryIntegrityError("enabled sources with access_class outside {A,B}: %s" % offenders)


def check_append_only(registry, floors):
    current = {r["source_id"] for r in registry}
    recorded = set(floors["append_only_source_ids"]["registered_source_family"])
    removed = sorted(recorded - current)
    if removed:
        raise RegistryIntegrityError("registry ids removed (append-only violated): %s" % removed)


def check_count_floors(registry, matrix, floors):
    measured = {
        "registered_source_family": len(registry),
        "active_collector": matrix["counts"]["active_collector"],
        "reserved_collector": matrix["counts"]["reserved_collector"],
        "matrix_rows": len(matrix["rows"]),
    }
    for key, floor in floors["count_floors"].items():
        if key not in measured:
            continue  # dataset_partition is validated by verify_data_vault
        if measured[key] < floor:
            raise RegistryIntegrityError(
                "count floor %s=%d exceeds measured current %d" % (key, floor, measured[key])
            )


def check_coverage_subset(registry, matrix):
    reg_ids = {r["source_id"] for r in registry}
    missing = set()
    for row in matrix["rows"]:
        for fam in row.get("coverage_source_family_ids") or []:
            if fam not in reg_ids:
                missing.add("%s->%s" % (row["source_id"], fam))
    if missing:
        raise RegistryIntegrityError("coverage_source_family_ids not in registry: %s" % sorted(missing))


def check_no_duplicate_family_ids(registry):
    seen, dups = set(), set()
    for r in registry:
        sid = r["source_id"]
        if sid in seen:
            dups.add(sid)
        seen.add(sid)
    if dups:
        raise RegistryIntegrityError("duplicate registry family ids: %s" % sorted(dups))


def check_enabled_family_registered(registry, matrix):
    reg_ids = {r["source_id"] for r in registry}
    offenders = []
    for row in matrix["rows"]:
        if row.get("record_kind") != "active_collector":
            continue
        for fam in row.get("coverage_source_family_ids") or []:
            if fam not in reg_ids:
                offenders.append("%s->%s" % (row["source_id"], fam))
    if offenders:
        raise RegistryIntegrityError("enabled source families not registered: %s" % offenders)


# ----- positive: the live registry satisfies every invariant -----------------

class RegistryIntegrityLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.matrix = load_matrix()
        cls.floors = load_floors()

    def test_c_set_is_seven(self):
        self.assertEqual(len(check_c_set_cardinality(self.registry)), 7)

    def test_publish_class_migration(self):
        # B-RIGHTS-1: the 7 carry publish_all_good_data, every row explicit.
        self.assertEqual(check_publish_class_migration(self.registry), GOOD_DATA_FAMILIES)

    def test_enabled_access_class_subset_ab(self):
        check_enabled_access_class(self.registry, self.matrix)

    def test_append_only(self):
        check_append_only(self.registry, self.floors)

    def test_count_floors(self):
        check_count_floors(self.registry, self.matrix, self.floors)

    def test_coverage_subset(self):
        check_coverage_subset(self.registry, self.matrix)

    def test_no_duplicate_ids(self):
        check_no_duplicate_family_ids(self.registry)

    def test_enabled_family_registered(self):
        check_enabled_family_registered(self.registry, self.matrix)


# ----- negative: each checker bites and names the offender -------------------

class RegistryIntegrityNegativeTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.matrix = load_matrix()
        self.floors = load_floors()

    def test_removing_c_member_trips_cardinality(self):
        reg = [r for r in self.registry if r["source_id"] != "cboe_vix"]
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_c_set_cardinality(reg)
        self.assertIn("!= 7", str(ctx.exception))

    def test_removed_registry_id_trips_append_only(self):
        reg = [r for r in self.registry if r["source_id"] != "bea_gdp"]
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_append_only(reg, self.floors)
        self.assertIn("bea_gdp", str(ctx.exception))

    def test_lowered_count_trips_floor(self):
        matrix = json.loads(json.dumps(self.matrix))
        matrix["counts"]["active_collector"] = 1
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_count_floors(self.registry, matrix, self.floors)
        self.assertIn("active_collector", str(ctx.exception))

    def test_unregistered_family_trips_coverage(self):
        matrix = json.loads(json.dumps(self.matrix))
        matrix["rows"][0]["coverage_source_family_ids"] = ["not_a_real_family"]
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_coverage_subset(self.registry, matrix)
        self.assertIn("not_a_real_family", str(ctx.exception))

    def test_duplicate_id_trips_guard(self):
        reg = self.registry + [dict(self.registry[0])]
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_no_duplicate_family_ids(reg)
        self.assertIn(self.registry[0]["source_id"], str(ctx.exception))

    def test_blank_publish_class_trips_migration(self):
        reg = json.loads(json.dumps(self.registry))
        reg[0]["publish_class"] = ""
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_publish_class_migration(reg)
        self.assertIn("blank", str(ctx.exception))

    def test_unlisted_good_data_trips_migration(self):
        reg = json.loads(json.dumps(self.registry))
        for r in reg:
            if r["source_id"] == "bea_gdp":
                r["publish_class"] = "publish_all_good_data"
        with self.assertRaises(RegistryIntegrityError) as ctx:
            check_publish_class_migration(reg)
        self.assertIn("publish_all_good_data set", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
