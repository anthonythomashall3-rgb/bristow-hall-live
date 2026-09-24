#!/usr/bin/env python3
"""D0B proof harness for the unfrozen vault verifier.

verify_data_vault.py had three store-growing pins hand-typed as literals: the
external-source-registry count (== 134), the dataset-partition set (an exact
tuple), and the external-registry field list (exact equality). D0B converted
each to a value computed from the store plus a relational assertion, backed by
the append-only floors in source_registry_growth_floors.v1.json.

This test proves the conversions did not weaken the gate:

  * eight regression cases each still make the verifier FAIL closed, and
  * four legitimate-growth cases each now PASS.

It drives verify_data_vault.py's own functions against small synthetic roots
(copies of the real catalogs, then a single targeted mutation) so no real
payload byte is touched.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = PROJECT_ROOT / "data_vault" / "scripts" / "verify_data_vault.py"

_spec = importlib.util.spec_from_file_location("verify_data_vault_under_test", VERIFY_PATH)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

# Files verify_research_catalogs reads (catalogs + timing + the two live_data
# authorities the D0B cross-check and floors now consult).
CATALOG_INPUTS = (
    "data_vault/catalog/metric_catalog.csv",
    "data_vault/catalog/dataset_catalog.csv",
    "data_vault/catalog/external_source_registry.csv",
    "data_vault/catalog/episode_2022_release_evidence.csv",
    "data_vault/catalog/severity_reference_ledger.csv",
    "data_vault/catalog/research_claim_ledger.csv",
    "data_vault/catalog/chronology_method_registry.csv",
    "data_vault/catalog/severity_dimension_registry.csv",
    "data_vault/catalog/timing_model.json",
    "live_data/config/source_registry_growth_floors.v1.json",
    "live_data/catalog/source_matrix.v1.json",
)

EXTERNAL_CSV = "data_vault/catalog/external_source_registry.csv"
DATASET_CSV = "data_vault/catalog/dataset_catalog.csv"
MATRIX_JSON = "live_data/catalog/source_matrix.v1.json"


def _real_receipt():
    receipt = json.loads(
        (PROJECT_ROOT / "data_vault/manifests/local_inventory_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        "series_id_count": receipt["series_id_count"],
        "discovered_files": receipt["discovered_files"],
        "discovered_bytes": receipt["discovered_bytes"],
    }


def _make_catalog_root(tmp: Path) -> Path:
    for rel in CATALOG_INPUTS:
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(PROJECT_ROOT / rel, dst)
    return tmp


def _read_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def _write_rows(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class CatalogRegressionTests(unittest.TestCase):
    """Cases (a)-(e), (h) and growth (i), (ii), (iv) via verify_research_catalogs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = _make_catalog_root(Path(self._tmp.name))
        self.receipt = _real_receipt()

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, receipt=None):
        V.verify_research_catalogs(self.root, receipt or self.receipt)

    def test_baseline_passes(self):
        # Sanity: an unmutated copy passes, so any failure below is the mutation.
        self._run()

    # (a) a registry row removed -> registry count falls below the floor.
    def test_a_registry_row_removed_fails(self):
        path = self.root / EXTERNAL_CSV
        fields, rows = _read_rows(path)
        _write_rows(path, fields, rows[:-1])
        with self.assertRaises(V.VerificationError) as cm:
            self._run()
        self.assertIn("count fell below recorded floor", str(cm.exception))

    # (b) a source_id renamed -> append-only id set broken (count unchanged).
    def test_b_source_id_renamed_fails(self):
        path = self.root / EXTERNAL_CSV
        fields, rows = _read_rows(path)
        rows[0]["source_id"] = "renamed_not_in_floor"
        _write_rows(path, fields, rows)
        with self.assertRaises(V.VerificationError) as cm:
            self._run()
        self.assertIn("dropped a previously-recorded source_id", str(cm.exception))

    # (c) a count decreased -> the dataset-partition count floor (the other
    #     converted count) also fails closed on a shrink.
    def test_c_count_decreased_fails(self):
        path = self.root / DATASET_CSV
        fields, rows = _read_rows(path)
        _write_rows(path, fields, rows[:-1])
        with self.assertRaises(V.VerificationError) as cm:
            self._run()
        self.assertIn("dataset", str(cm.exception).lower())

    # (d) a row malformed -> excess CSV fields rejected on read.
    def test_d_row_malformed_fails(self):
        path = self.root / EXTERNAL_CSV
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write("a,b,c,d,e,f,g,h,i,j,k,l,m,n,EXCESS,EXTRA\n")
        with self.assertRaises(V.VerificationError):
            self._run()

    # (e) registry and matrix family tallies disagree.
    def test_e_registry_matrix_divergence_fails(self):
        path = self.root / MATRIX_JSON
        matrix = json.loads(path.read_text(encoding="utf-8"))
        for row in matrix["rows"]:
            if row.get("record_kind") == "registered_source_family":
                row["source_id"] = "matrix_only_divergent_id"
                break
        path.write_text(json.dumps(matrix), encoding="utf-8")
        with self.assertRaises(V.VerificationError) as cm:
            self._run()
        self.assertIn("diverge", str(cm.exception))

    # (h) a schema field removed -> superset check still fails on removal.
    def test_h_schema_field_removed_fails(self):
        path = self.root / EXTERNAL_CSV
        fields, rows = _read_rows(path)
        drop = "notes"
        new_fields = [f for f in fields if f != drop]
        for row in rows:
            row.pop(drop, None)
        _write_rows(path, new_fields, rows)
        with self.assertRaises(V.VerificationError) as cm:
            self._run()
        self.assertIn("missing a required field", str(cm.exception))

    # (i) a coverage family added to the external registry (registry + matrix
    #     grown together, as a registration batch would) -> PASS.
    def test_i_growth_registry_family_added_passes(self):
        ext = self.root / EXTERNAL_CSV
        fields, rows = _read_rows(ext)
        template = dict(rows[0])
        template["source_id"] = "brandnew_coverage_family"
        template["primary_url"] = "https://example.gov/new"
        template["access_class"] = "A"
        rows.append(template)
        _write_rows(ext, fields, rows)

        mpath = self.root / MATRIX_JSON
        matrix = json.loads(mpath.read_text(encoding="utf-8"))
        sample = next(
            r for r in matrix["rows"] if r.get("record_kind") == "registered_source_family"
        )
        new_row = dict(sample)
        new_row["source_id"] = "brandnew_coverage_family"
        matrix["rows"].append(new_row)
        matrix["counts"]["registered_source_family"] += 1
        mpath.write_text(json.dumps(matrix), encoding="utf-8")

        self._run()  # must not raise

    # (ii) a new dataset directory added (files landed + receipt regenerated in
    #      the same write) -> PASS.
    def test_ii_growth_dataset_partition_added_passes(self):
        path = self.root / DATASET_CSV
        fields, rows = _read_rows(path)
        added_files, added_bytes = 3, 99
        new = dict(rows[0])
        new["dataset_id"] = "data_archive/brandnew_partition"
        new["file_count"] = str(added_files)
        new["byte_count"] = str(added_bytes)
        rows.append(new)
        _write_rows(path, fields, rows)
        receipt = dict(self.receipt)
        receipt["discovered_files"] += added_files
        receipt["discovered_bytes"] += added_bytes
        self._run(receipt)  # must not raise

    # (iv) a schema field added -> superset check tolerates the new column.
    def test_iv_growth_schema_field_added_passes(self):
        path = self.root / EXTERNAL_CSV
        fields, rows = _read_rows(path)
        new_fields = list(fields) + ["coverage_family_notes"]
        for row in rows:
            row["coverage_family_notes"] = "added"
        _write_rows(path, new_fields, rows)
        self._run()  # must not raise


class InventoryRelationTests(unittest.TestCase):
    """Cases (f), (g) and growth (iii) via verify_inventory_relation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _sha(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _baseline(self):
        """A minimal payload tree that passes verify_inventory_relation."""
        root = self.root
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "data_archive").mkdir(parents=True, exist_ok=True)
        (root / "method_source").mkdir(parents=True, exist_ok=True)
        (root / "data_vault/manifests").mkdir(parents=True, exist_ok=True)

        a = b"listed payload\n"
        r = b"# readme\n"
        (root / "data/a.txt").write_bytes(a)
        (root / "data_archive/README.md").write_bytes(r)
        sha_a, sha_r = self._sha(a), self._sha(r)

        expected = {"data/a.txt": sha_a}  # README is the one allowed-unlisted file
        rows = [
            {
                "path": "data/a.txt",
                "sha256": sha_a,
                "byte_count": str(len(a)),
                "expected_sha256": sha_a,
                "manifest_match": "true",
                "lane": "data",
            },
            {
                "path": "data_archive/README.md",
                "sha256": sha_r,
                "byte_count": str(len(r)),
                "expected_sha256": "",
                "manifest_match": "unlisted",
                "lane": "docs",
            },
        ]
        receipt = {
            "discovered_files": 2,
            "discovered_bytes": len(a) + len(r),
            "manifest_matches": 1,
            "manifest_mismatches": 0,
            "lane_counts": {
                "data": {"files": 1, "bytes": len(a)},
                "docs": {"files": 1, "bytes": len(r)},
            },
            "duplicate_hash_group_count": 0,
        }
        (root / "data_vault/manifests/duplicate_hash_groups.json").write_text(
            "[]", encoding="utf-8"
        )
        return receipt, rows, expected

    def test_baseline_passes(self):
        receipt, rows, expected = self._baseline()
        V.verify_inventory_relation(self.root, receipt, rows, expected, full=False)

    # (f) a vault file present on disk but absent from the inventory.
    def test_f_disk_file_not_in_inventory_fails(self):
        receipt, rows, expected = self._baseline()
        (self.root / "data/orphan_on_disk.txt").write_bytes(b"x\n")
        with self.assertRaises(V.VerificationError) as cm:
            V.verify_inventory_relation(self.root, receipt, rows, expected, full=False)
        self.assertIn("differs from disk", str(cm.exception))

    # (g) a vault file in the inventory but missing from disk.
    def test_g_inventory_file_missing_from_disk_fails(self):
        receipt, rows, expected = self._baseline()
        rows.append(
            {
                "path": "data/phantom.txt",
                "sha256": "0" * 64,
                "byte_count": "1",
                "expected_sha256": "0" * 64,
                "manifest_match": "true",
                "lane": "data",
            }
        )
        with self.assertRaises(V.VerificationError) as cm:
            V.verify_inventory_relation(self.root, receipt, rows, expected, full=False)
        self.assertIn("differs from disk", str(cm.exception))

    # (iii) new files added to an existing lane with the inventory regenerated
    #       in the same write -> PASS.
    def test_iii_growth_file_added_with_inventory_regen_passes(self):
        receipt, rows, expected = self._baseline()
        d = b"another listed payload\n"
        (self.root / "data/d.txt").write_bytes(d)
        sha_d = self._sha(d)
        expected["data/d.txt"] = sha_d
        rows.append(
            {
                "path": "data/d.txt",
                "sha256": sha_d,
                "byte_count": str(len(d)),
                "expected_sha256": sha_d,
                "manifest_match": "true",
                "lane": "data",
            }
        )
        receipt["discovered_files"] = 3
        receipt["discovered_bytes"] += len(d)
        receipt["manifest_matches"] = 2
        receipt["lane_counts"]["data"] = {"files": 2, "bytes": 15 + len(d)}
        rows.sort(key=lambda r: r["path"])  # inventory is path-sorted, like the real vault
        V.verify_inventory_relation(self.root, receipt, rows, expected, full=False)


if __name__ == "__main__":
    unittest.main()
