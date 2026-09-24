from __future__ import absolute_import

import copy
import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import (
    CanonicalDataError,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
)
from live_data.rmv2_live.config import load_config
from live_data.rmv2_live.feed_factory import (
    apply_candidate_bundle,
    compile_onboarding_spec,
    load_onboarding_spec,
    materialize_candidate_bundle,
    probe_onboarding_source,
)
from live_data.rmv2_live.adapters import HttpResponse


CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
PLANNED_PATH = (
    PROJECT_ROOT / "live_data" / "config" / "planned_sources.v1.json"
)
REGISTRY_PATH = (
    PROJECT_ROOT / "data_vault" / "catalog" /
    "external_source_registry.csv"
)
RETRIEVED_AT = "2026-07-30T12:00:00Z"
PLANNED_SOURCE_FIELDS = (
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


def package_json_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def source_config():
    return {
        "adapter": "tabular_csv",
        "allowed_hosts": ["publisher.example"],
        "coverage_source_ids": ["census_bds"],
        "enabled": True,
        "endpoint": "https://publisher.example/feed.csv",
        "expected_content_types": ["text/csv"],
        "frequency": "annual",
        "information_set_mode": "current_revised",
        "label": "Fixture-backed government test feed",
        "max_bytes": 100000,
        "method_version": "fixture_feed.current_revised.v1",
        "poll_seconds": 604800,
        "publisher": "Publisher",
        "publisher_release_clock": (
            "annual exact publisher calendar; reference, release, "
            "retrieval, and validation clocks remain separate"
        ),
        "rights_status": "public_government_data_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "date_column": "year",
            "date_format": "%Y",
            "expected_header": ["year", "value"],
            "items": [{
                "column": "value",
                "forecast_horizon": None,
                "label": "Value",
                "series_id": "FACTORY.TEST.VALUE",
                "unit": "index points",
                "value_status": "actual",
            }],
            "missing_tokens": [""],
        },
        "source_id": "factory_test_current",
        "value_status": "actual",
    }


def fixture_bytes():
    return b"year,value\n2024,1.25\n2025,2.50\n"


def write_active_generation(
    root,
    active_config,
    source_ids=None,
    series_bindings=None,
):
    root = Path(root)
    if source_ids is None:
        source_ids = sorted(
            source["source_id"]
            for source in active_config["sources"]
            if source["enabled"]
        )
    if series_bindings is None:
        series_bindings = {
            "CFPB.CCT.CREDIT_TIGHTNESS_INDEX.AUT.NSA.VALUE": (
                "cfpb_credit_trends_current"
            ),
            "EIUIR": "bls_mxp_current",
            "FED.DSR.CONSUMER_DSR_RATIO": "fed_dsr_current",
            "FED.DSR.DSR_RATIO": "fed_dsr_current",
            "FED.DSR.MORTGAGE_DSR_RATIO": "fed_dsr_current",
        }
    receipts = {
        source_id: sha256_bytes(source_id.encode("utf-8"))
        for source_id in source_ids
    }
    snapshot = {
        "generated_at": RETRIEVED_AT,
        "schema_version": "recession-monitor-v2.live-snapshot.v1",
        "series": {
            series_id: {
                "series_id": series_id,
                "source_id": source_id,
                "unit": "index",
            }
            for series_id, source_id in sorted(series_bindings.items())
        },
        "sources": [
            {
                "receipt_sha256": receipts[source_id],
                "source_id": source_id,
            }
            for source_id in source_ids
        ],
    }
    coverage = {
        "schema_version": "recession-monitor-v2.source-coverage.v1",
    }
    status = {
        "schema_version": "recession-monitor-v2.live-status.v1",
    }
    members = {
        "coverage.json": canonical_json_bytes(coverage),
        "snapshot.json": canonical_json_bytes(snapshot),
        "status.json": canonical_json_bytes(status),
    }
    manifest = {
        "created_at": RETRIEVED_AT,
        "members": {
            name: {
                "bytes": len(data),
                "schema_version": strict_json_loads(data)["schema_version"],
                "sha256": sha256_bytes(data),
            }
            for name, data in sorted(members.items())
        },
        "schema_version": (
            "recession-monitor-v2.live-generation-manifest.v2"
        ),
        "source_head_receipt_sha256": receipts,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    generation_id = sha256_bytes(manifest_bytes)
    generation_root = (
        root / "live_data" / "store" / "generations" / generation_id
    )
    generation_root.mkdir(parents=True)
    for name, data in members.items():
        path = generation_root / name
        path.write_bytes(data)
        path.chmod(0o444)
    manifest_path = generation_root / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_path.chmod(0o444)
    pointer = {
        "coverage_sha256": manifest["members"]["coverage.json"]["sha256"],
        "generation_sha256": generation_id,
        "manifest_sha256": generation_id,
        "schema_version": "recession-monitor-v2.live-pointer.v2",
        "snapshot_sha256": manifest["members"]["snapshot.json"]["sha256"],
        "status_sha256": manifest["members"]["status.json"]["sha256"],
        "updated_at": RETRIEVED_AT,
    }
    public_root = root / "live_data" / "public"
    public_root.mkdir(parents=True, exist_ok=True)
    pointer_path = public_root / "latest.pointer.json"
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    return {
        "generation_root": generation_root,
        "pointer": pointer,
        "pointer_path": pointer_path,
    }


def write_project_inputs(root):
    root = Path(root)
    config_target = root / "live_data" / "config" / "sources.v1.json"
    planned_target = (
        root / "live_data" / "config" / "planned_sources.v1.json"
    )
    registry_target = (
        root / "data_vault" / "catalog" /
        "external_source_registry.csv"
    )
    config_target.parent.mkdir(parents=True, exist_ok=True)
    registry_target.parent.mkdir(parents=True, exist_ok=True)
    config_target.write_bytes(CONFIG_PATH.read_bytes())
    planned = read_json(PLANNED_PATH)
    planned["sources"] = [
        {field: row[field] for field in PLANNED_SOURCE_FIELDS}
        for row in planned["sources"]
    ]
    planned_target.write_bytes(package_json_bytes(planned))
    registry_target.write_bytes(REGISTRY_PATH.read_bytes())
    write_active_generation(root, load_config(config_target))
    return config_target, planned_target


def write_spec(root, coverage_source_id="census_bds"):
    root = Path(root)
    fixture_path = root / "live_data" / "feed_factory" / "fixtures" / "feed.csv"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_bytes(fixture_bytes())
    source = source_config()
    source["coverage_source_ids"] = [coverage_source_id]
    spec = {
        "activation": {
            "scientific_effect": "none",
            "website_effect": "measurement_catalog_and_status_only",
        },
        "expected_normalization": {
            "first_observation_period": "2024-01-01",
            "last_observation_period": "2025-01-01",
            "record_count": 2,
            "series_ids": ["FACTORY.TEST.VALUE"],
            "units": ["index points"],
            "value_statuses": ["actual"],
        },
        "fixture": {
            "bytes": len(fixture_bytes()),
            "path": "live_data/feed_factory/fixtures/feed.csv",
            "retrieved_at": RETRIEVED_AT,
            "sha256": sha256_bytes(fixture_bytes()),
        },
        "reservation": {
            "action": "none",
            "source_id": None,
        },
        "schema_version": "recession-monitor-v2.feed-onboarding-spec.v1",
        "source": source,
    }
    spec_path = root / "live_data" / "feed_factory" / "recipes" / "feed.v1.json"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_bytes(canonical_json_bytes(spec))
    return spec_path, spec


def write_draft(root):
    root = Path(root)
    draft = {
        "activation": {
            "scientific_effect": "none",
            "website_effect": "measurement_catalog_and_status_only",
        },
        "reservation": {
            "action": "none",
            "source_id": None,
        },
        "schema_version": "recession-monitor-v2.feed-discovery-spec.v1",
        "source": source_config(),
    }
    path = (
        root / "live_data" / "feed_factory" /
        "drafts" / "feed.v1.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(draft))
    return path


class FixtureHttpClient(object):
    def fetch(self, source, now=None, conditional_headers=None):
        return HttpResponse(
            source["endpoint"],
            200,
            {
                "content-type": "text/csv",
                "etag": '"fixture-v1"',
            },
            fixture_bytes(),
            request_headers={},
            request_method="GET",
            request_parameters={},
        )


def rewrite_bundle(root, bundle, replacements):
    manifest_path = Path(bundle["manifest_path"])
    old_root = manifest_path.parent
    manifest = read_json(manifest_path)
    members = {}
    for name in manifest["members"]:
        members[name] = replacements.get(
            name,
            (old_root / name).read_bytes(),
        )
    manifest["members"] = {
        name: {
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        for name, data in sorted(members.items())
    }
    manifest_bytes = canonical_json_bytes(manifest)
    new_root = (
        Path(root) / "live_data" / "feed_factory" / "candidates" /
        manifest["source_id"] / sha256_bytes(manifest_bytes)
    )
    new_root.mkdir(parents=True)
    for name, data in members.items():
        path = new_root / name
        path.write_bytes(data)
        path.chmod(0o444)
    new_manifest = new_root / "manifest.json"
    new_manifest.write_bytes(manifest_bytes)
    new_manifest.chmod(0o444)
    return new_manifest


class FeedFactoryTests(unittest.TestCase):
    def test_probe_fetches_once_into_isolated_evidence_and_generates_recipe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path, planned_path = write_project_inputs(root)
            draft_path = write_draft(root)
            before_config = config_path.read_bytes()
            before_planned = planned_path.read_bytes()

            result = probe_onboarding_source(
                root,
                draft_path,
                http_client=FixtureHttpClient(),
                clock=lambda: RETRIEVED_AT,
            )
            self.assertEqual(result["status"], "PROBE_PASS_NOT_ACTIVE")
            self.assertEqual(
                result["raw_sha256"],
                sha256_bytes(fixture_bytes()),
            )
            self.assertEqual(config_path.read_bytes(), before_config)
            self.assertEqual(planned_path.read_bytes(), before_planned)
            self.assertFalse(
                (root / "live_data" / "runtime" / "source_heads").exists()
            )

            generated_spec = read_json(result["spec_path"])
            self.assertEqual(
                generated_spec["schema_version"],
                "recession-monitor-v2.feed-onboarding-spec.v1",
            )
            self.assertEqual(
                generated_spec["expected_normalization"]["record_count"],
                2,
            )
            compiled = compile_onboarding_spec(
                root,
                result["spec_path"],
            )
            self.assertEqual(
                compiled["receipt"]["status"],
                "COMPILED_FIXTURE_VERIFIED_NOT_ACTIVE",
            )

    def test_strict_recipe_and_fixture_compile_to_deterministic_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)

            self.assertEqual(
                compiled["receipt"]["schema_version"],
                "recession-monitor-v2.feed-onboarding-receipt.v1",
            )
            self.assertEqual(
                compiled["receipt"]["status"],
                "COMPILED_FIXTURE_VERIFIED_NOT_ACTIVE",
            )
            self.assertEqual(compiled["receipt"]["record_count"], 2)
            self.assertEqual(
                compiled["receipt"]["series_ids"],
                ["FACTORY.TEST.VALUE"],
            )
            self.assertEqual(
                compiled["receipt"]["scientific_effect"],
                "none",
            )
            self.assertEqual(
                compiled["candidate_config"]["sources"][-1],
                spec["source"],
            )
            self.assertEqual(
                compiled["candidate_config_bytes"],
                canonical_json_bytes(compiled["candidate_config"]),
            )
            self.assertEqual(
                compiled["receipt"]["candidate_config_sha256"],
                sha256_bytes(compiled["candidate_config_bytes"]),
            )
            load_config_bytes = (
                root / "live_data" / "config" / "candidate.json"
            )
            load_config_bytes.write_bytes(
                compiled["candidate_config_bytes"]
            )
            loaded = load_config(load_config_bytes)
            self.assertEqual(
                len(loaded["sources"]),
                len(load_config(CONFIG_PATH)["sources"]) + 1,
            )

    def test_candidate_planned_rows_preserve_package_field_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)

            candidate = strict_json_loads(
                compiled["candidate_planned_bytes"]
            )
            self.assertTrue(candidate["sources"])
            for row in candidate["sources"]:
                self.assertEqual(tuple(row), PLANNED_SOURCE_FIELDS)

    def test_duplicate_keys_extra_keys_and_fixture_hash_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root)

            duplicate = (
                b'{"schema_version":"a","schema_version":"b"}'
            )
            spec_path.write_bytes(duplicate)
            with self.assertRaises(CanonicalDataError):
                load_onboarding_spec(root, spec_path)

            spec["unexpected"] = True
            spec_path.write_bytes(canonical_json_bytes(spec))
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

            del spec["unexpected"]
            spec["fixture"]["sha256"] = "0" * 64
            spec_path.write_bytes(canonical_json_bytes(spec))
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

    def test_rights_blocked_target_quarantine_and_series_collision_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root, "cboe_vix")
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

            spec["source"]["coverage_source_ids"] = [
                "nyfed_yield_recession_probability"
            ]
            spec_path.write_bytes(canonical_json_bytes(spec))
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

            spec["source"]["coverage_source_ids"] = ["census_bds"]
            spec["source"]["series"]["items"][0]["series_id"] = "EIUIR"
            spec["expected_normalization"]["series_ids"] = ["EIUIR"]
            spec_path.write_bytes(canonical_json_bytes(spec))
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

    def test_fed_ddp_derived_series_collision_with_active_dsr_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root)
            active_dsr = next(
                copy.deepcopy(source)
                for source in load_config(CONFIG_PATH)["sources"]
                if source["source_id"] == "fed_dsr_current"
            )
            active_dsr["source_id"] = "factory_duplicate_dsr_current"
            spec["source"] = active_dsr
            spec_path.write_bytes(canonical_json_bytes(spec))

            with self.assertRaisesRegex(
                CanonicalDataError,
                "FED\\.DSR\\.CONSUMER_DSR_RATIO",
            ):
                compile_onboarding_spec(root, spec_path)

    def test_unsupported_derived_identity_shape_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root)
            spec["source"]["adapter"] = "cfpb_credit_trends_csv"
            spec["source"]["series"] = {}
            spec_path.write_bytes(canonical_json_bytes(spec))

            with self.assertRaisesRegex(
                CanonicalDataError,
                "output series identity",
            ):
                compile_onboarding_spec(root, spec_path)

    def test_dynamic_cfpb_measurement_collision_from_active_snapshot_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, spec = write_spec(root)
            collision = (
                "CFPB.CCT.CREDIT_TIGHTNESS_INDEX.AUT.NSA.VALUE"
            )
            spec["source"]["series"]["items"][0]["series_id"] = collision
            spec["expected_normalization"]["series_ids"] = [collision]
            spec_path.write_bytes(canonical_json_bytes(spec))

            with self.assertRaisesRegex(
                CanonicalDataError,
                "CFPB\\.CCT\\.CREDIT_TIGHTNESS_INDEX\\.AUT\\.NSA\\.VALUE",
            ):
                compile_onboarding_spec(root, spec_path)

    def test_active_measurement_generation_absence_and_drift_fail_closed(self):
        cases = (
            "absent_pointer",
            "stale_source_set",
            "malformed_series",
            "mixed_pointer",
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    config_path, unused_planned = write_project_inputs(root)
                    spec_path, unused_spec = write_spec(root)
                    active = load_config(config_path)
                    pointer_path = (
                        root / "live_data" / "public" /
                        "latest.pointer.json"
                    )
                    if case == "absent_pointer":
                        pointer_path.unlink()
                    elif case == "stale_source_set":
                        source_ids = sorted(
                            source["source_id"]
                            for source in active["sources"]
                            if source["enabled"]
                        )[:-1]
                        write_active_generation(
                            root,
                            active,
                            source_ids=source_ids,
                        )
                    elif case == "malformed_series":
                        write_active_generation(
                            root,
                            active,
                            series_bindings={
                                "EIUIR": "not_an_active_source",
                            },
                        )
                    else:
                        pointer = read_json(pointer_path)
                        pointer["snapshot_sha256"] = "0" * 64
                        pointer_path.write_bytes(
                            canonical_json_bytes(pointer)
                        )

                    with self.assertRaises(CanonicalDataError):
                        compile_onboarding_spec(root, spec_path)

    def test_reservation_transition_and_candidate_application_are_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path, planned_path = write_project_inputs(root)
            spec_path, spec = write_spec(root)
            planned = read_json(planned_path)
            reservation = copy.deepcopy(planned["sources"][0])
            reservation["source_id"] = "factory_test_reservation"
            reservation["coverage_source_family_ids"] = ["census_bds"]
            planned["sources"].append(reservation)
            planned["scope"]["reservation_count"] = len(planned["sources"])
            planned_path.write_bytes(package_json_bytes(planned))

            spec["reservation"] = {
                "action": "remove_exact",
                "source_id": "factory_test_reservation",
            }
            spec_path.write_bytes(canonical_json_bytes(spec))
            compiled = compile_onboarding_spec(root, spec_path)
            self.assertNotIn(
                "factory_test_reservation",
                [
                    row["source_id"]
                    for row in compiled["candidate_planned"]["sources"]
                ],
            )
            self.assertEqual(
                compiled["candidate_planned"]["scope"]["reservation_count"],
                len(planned["sources"]) - 1,
            )

            bundle = materialize_candidate_bundle(root, compiled)
            result = apply_candidate_bundle(root, bundle["manifest_path"])
            self.assertEqual(result["status"], "APPLIED_CONFIG_ONLY_REFRESH_REQUIRED")
            self.assertEqual(
                sha256_bytes(config_path.read_bytes()),
                compiled["receipt"]["candidate_config_sha256"],
            )
            self.assertEqual(
                sha256_bytes(planned_path.read_bytes()),
                compiled["receipt"]["candidate_planned_sha256"],
            )
            self.assertEqual(
                len(load_config(config_path)["sources"]),
                len(load_config(CONFIG_PATH)["sources"]) + 1,
            )

            with self.assertRaises(CanonicalDataError):
                apply_candidate_bundle(root, bundle["manifest_path"])

    def test_apply_rejects_forged_target_family_even_when_hashes_are_rebound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)
            bundle = materialize_candidate_bundle(root, compiled)

            candidate = copy.deepcopy(compiled["candidate_config"])
            candidate["sources"][-1]["coverage_source_ids"] = [
                "nyfed_yield_recession_probability"
            ]
            candidate_bytes = canonical_json_bytes(candidate)
            spec = copy.deepcopy(compiled["spec"])
            spec["source"]["coverage_source_ids"] = [
                "nyfed_yield_recession_probability"
            ]
            spec_bytes = canonical_json_bytes(spec)
            receipt = copy.deepcopy(compiled["receipt"])
            receipt["candidate_config_sha256"] = sha256_bytes(
                candidate_bytes
            )
            receipt["spec_sha256"] = sha256_bytes(spec_bytes)
            forged_manifest = rewrite_bundle(
                root,
                bundle,
                {
                    "candidate.sources.v1.json": candidate_bytes,
                    "onboarding.receipt.json": canonical_json_bytes(receipt),
                    "onboarding.spec.json": spec_bytes,
                },
            )

            with self.assertRaises(CanonicalDataError):
                apply_candidate_bundle(root, forged_manifest)

    def test_legacy_v1_and_v2_bundles_are_historical_and_refused_for_apply(self):
        for legacy_version in ("v1", "v2"):
            with self.subTest(legacy_version=legacy_version):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    write_project_inputs(root)
                    spec_path, unused_spec = write_spec(root)
                    compiled = compile_onboarding_spec(root, spec_path)
                    bundle = materialize_candidate_bundle(root, compiled)
                    v3_manifest_path = Path(bundle["manifest_path"])
                    v3_root = v3_manifest_path.parent
                    manifest = read_json(v3_manifest_path)
                    manifest["schema_version"] = (
                        "recession-monitor-v2.feed-onboarding-bundle.%s" %
                        legacy_version
                    )
                    raw_names = [
                        name for name in manifest["members"]
                        if name.startswith("fixture.raw.")
                    ]
                    for name in raw_names:
                        manifest["members"].pop(name)
                    if legacy_version == "v1":
                        manifest["members"].pop("onboarding.spec.json")
                    manifest_bytes = canonical_json_bytes(manifest)
                    legacy_root = (
                        root / "live_data" / "feed_factory" / "candidates" /
                        manifest["source_id"] / sha256_bytes(manifest_bytes)
                    )
                    legacy_root.mkdir(parents=True)
                    for name in manifest["members"]:
                        path = legacy_root / name
                        path.write_bytes((v3_root / name).read_bytes())
                        path.chmod(0o444)
                    legacy_manifest_path = legacy_root / "manifest.json"
                    legacy_manifest_path.write_bytes(manifest_bytes)
                    legacy_manifest_path.chmod(0o444)

                    with self.assertRaises(CanonicalDataError):
                        apply_candidate_bundle(root, legacy_manifest_path)

    def test_repeated_materialization_preserves_frozen_inode_and_mtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)
            first = materialize_candidate_bundle(root, compiled)
            manifest_path = Path(first["manifest_path"])
            manifest = read_json(manifest_path)
            self.assertEqual(
                manifest["schema_version"],
                "recession-monitor-v2.feed-onboarding-bundle.v3",
            )
            raw_name = (
                "fixture.raw.%s.bin" %
                compiled["receipt"]["fixture_sha256"]
            )
            self.assertIn(raw_name, manifest["members"])
            paths = [manifest_path] + [
                manifest_path.parent / name
                for name in manifest["members"]
            ]
            before = {
                path.name: (path.stat().st_ino, path.stat().st_mtime_ns)
                for path in paths
            }

            second = materialize_candidate_bundle(root, compiled)
            self.assertEqual(second, first)
            self.assertEqual(
                {
                    path.name: (path.stat().st_ino, path.stat().st_mtime_ns)
                    for path in paths
                },
                before,
            )

    def test_repeated_materialization_rejects_frozen_file_drift(self):
        mutations = (
            "bytes",
            "mode",
            "symlink",
            "hardlink",
            "special",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    write_project_inputs(root)
                    spec_path, unused_spec = write_spec(root)
                    compiled = compile_onboarding_spec(root, spec_path)
                    bundle = materialize_candidate_bundle(root, compiled)
                    target = (
                        Path(bundle["manifest_path"]).parent /
                        "candidate.sources.v1.json"
                    )
                    if mutation == "bytes":
                        target.chmod(0o644)
                        target.write_bytes(b"{}")
                        target.chmod(0o444)
                    elif mutation == "mode":
                        target.chmod(0o644)
                    elif mutation == "symlink":
                        outside = root / "outside.json"
                        outside.write_bytes(target.read_bytes())
                        target.unlink()
                        target.symlink_to(outside)
                    elif mutation == "hardlink":
                        os.link(str(target), str(root / "second-link.json"))
                    else:
                        target.unlink()
                        os.mkfifo(str(target), 0o444)

                    with self.assertRaises(CanonicalDataError):
                        materialize_candidate_bundle(root, compiled)

    def test_raw_fixture_is_bundled_and_apply_rederives_normalized_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)
            bundle = materialize_candidate_bundle(root, compiled)
            manifest_path = Path(bundle["manifest_path"])
            raw_name = (
                "fixture.raw.%s.bin" %
                compiled["receipt"]["fixture_sha256"]
            )
            self.assertEqual(
                (manifest_path.parent / raw_name).read_bytes(),
                fixture_bytes(),
            )

            normalized = copy.deepcopy(compiled["normalized"])
            normalized["records"][0]["value"] = "999"
            normalized_bytes = canonical_json_bytes(normalized)
            receipt = copy.deepcopy(compiled["receipt"])
            receipt["normalized_sha256"] = sha256_bytes(normalized_bytes)
            forged_manifest = rewrite_bundle(
                root,
                bundle,
                {
                    "fixture.normalized.json": normalized_bytes,
                    "onboarding.receipt.json": canonical_json_bytes(receipt),
                },
            )
            with self.assertRaisesRegex(
                CanonicalDataError,
                "raw fixture normalization",
            ):
                apply_candidate_bundle(root, forged_manifest)

    def test_apply_rejects_missing_tampered_and_rebound_raw_fixture(self):
        for mutation in ("missing", "tampered", "rebound"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    write_project_inputs(root)
                    spec_path, unused_spec = write_spec(root)
                    compiled = compile_onboarding_spec(root, spec_path)
                    bundle = materialize_candidate_bundle(root, compiled)
                    manifest_path = Path(bundle["manifest_path"])
                    raw_name = (
                        "fixture.raw.%s.bin" %
                        compiled["receipt"]["fixture_sha256"]
                    )
                    raw_path = manifest_path.parent / raw_name
                    if mutation == "missing":
                        raw_path.unlink()
                        candidate_manifest = manifest_path
                    elif mutation == "tampered":
                        raw_path.chmod(0o644)
                        raw_path.write_bytes(fixture_bytes() + b"\n")
                        raw_path.chmod(0o444)
                        candidate_manifest = manifest_path
                    else:
                        candidate_manifest = rewrite_bundle(
                            root,
                            bundle,
                            {
                                raw_name: (
                                    b"year,value\n2024,1.25\n2025,3.00\n"
                                ),
                            },
                        )

                    with self.assertRaises(CanonicalDataError):
                        apply_candidate_bundle(root, candidate_manifest)

    def test_apply_cross_binds_receipt_and_normalized_member_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            compiled = compile_onboarding_spec(root, spec_path)
            bundle = materialize_candidate_bundle(root, compiled)

            normalized = copy.deepcopy(compiled["normalized"])
            normalized["source_id"] = "forged_source"
            normalized_bytes = canonical_json_bytes(normalized)
            receipt = copy.deepcopy(compiled["receipt"])
            receipt["normalized_sha256"] = sha256_bytes(normalized_bytes)
            forged_manifest = rewrite_bundle(
                root,
                bundle,
                {
                    "fixture.normalized.json": normalized_bytes,
                    "onboarding.receipt.json": canonical_json_bytes(receipt),
                },
            )

            with self.assertRaises(CanonicalDataError):
                apply_candidate_bundle(root, forged_manifest)

    def test_registry_symlink_and_hardlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            spec_path, unused_spec = write_spec(root)
            original = REGISTRY_PATH.read_bytes()

            registry = (
                root / "data_vault" / "catalog" /
                "external_source_registry.csv"
            )
            real_registry = registry.with_name("registry.real.csv")
            registry.rename(real_registry)
            registry.symlink_to(real_registry.name)
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

            registry.unlink()
            real_registry.write_bytes(original)
            os.link(str(real_registry), str(registry))
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

            registry.unlink()
            registry.mkdir()
            with self.assertRaises(CanonicalDataError):
                compile_onboarding_spec(root, spec_path)

    def test_probe_rejects_symlinked_output_ancestor(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            draft_path = write_draft(root)
            outside = root / "outside"
            outside.mkdir()
            probe_parent = root / "live_data" / "feed_factory" / "probes"
            probe_parent.parent.mkdir(parents=True, exist_ok=True)
            probe_parent.symlink_to(outside, target_is_directory=True)

            with self.assertRaises(CanonicalDataError):
                probe_onboarding_source(
                    root,
                    draft_path,
                    http_client=FixtureHttpClient(),
                    clock=lambda: RETRIEVED_AT,
                )
            self.assertEqual(list(outside.iterdir()), [])

    def test_identical_payload_at_later_time_retains_both_probe_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_project_inputs(root)
            draft_path = write_draft(root)

            first = probe_onboarding_source(
                root,
                draft_path,
                http_client=FixtureHttpClient(),
                clock=lambda: "2026-07-30T12:00:00Z",
            )
            second = probe_onboarding_source(
                root,
                draft_path,
                http_client=FixtureHttpClient(),
                clock=lambda: "2026-07-30T12:05:00Z",
            )

            self.assertNotEqual(first["probe_path"], second["probe_path"])
            self.assertNotEqual(first["spec_path"], second["spec_path"])
            self.assertEqual(
                read_json(
                    Path(first["probe_path"]) / "probe.receipt.json"
                )["retrieved_at"],
                "2026-07-30T12:00:00Z",
            )
            self.assertEqual(
                read_json(
                    Path(second["probe_path"]) / "probe.receipt.json"
                )["retrieved_at"],
                "2026-07-30T12:05:00Z",
            )
            with self.assertRaises(CanonicalDataError):
                probe_onboarding_source(
                    root,
                    draft_path,
                    http_client=FixtureHttpClient(),
                    clock=lambda: "2026-07-30T12:05:00Z",
                )


if __name__ == "__main__":
    unittest.main()


class AdmissionGateTests(unittest.TestCase):
    """Automatic activation must never publish a payload that is not data."""

    SUMMARY = {
        "first_observation_period": "2020-01",
        "last_observation_period": "2026-06",
    }

    def gate(self, **overrides):
        from live_data.rmv2_live.feed_factory import evaluate_admission_gate
        kwargs = {
            "receipt": {
                "normalized_sha256": "a" * 64,
                "record_count": 100,
                "series_ids": ["A", "B"],
                "source_id": "x_new",
            },
            "summary": dict(self.SUMMARY),
            "fixture_bytes": b"date,value\n2020-01,1\n",
            "adapter": "tabular_csv",
            "rights": "public_domain_with_attribution",
            "active_series_ids": {"Z"},
            "active_source_ids": {"other"},
        }
        kwargs.update(overrides)
        return evaluate_admission_gate(**kwargs)

    def test_clean_tabular_candidate_is_admitted(self):
        self.assertEqual(self.gate()["verdict"], "ADMITTED")

    def test_html_masquerading_as_csv_is_blocked(self):
        result = self.gate(
            fixture_bytes=b"<!DOCTYPE html><html><body>404 Not Found",
        )
        self.assertEqual(result["verdict"], "BLOCKED_NOT_DATA")
        self.assertIn("payload_is_data_not_markup", result["failed_checks"])

    def test_markup_is_allowed_for_a_declared_markup_adapter(self):
        result = self.gate(
            fixture_bytes=b"<?xml version='1.0'?><root/>",
            adapter="treasury_yield_xml",
        )
        self.assertEqual(result["verdict"], "ADMITTED")

    def test_empty_parse_is_blocked(self):
        result = self.gate(receipt={
            "normalized_sha256": "a" * 64,
            "record_count": 0,
            "series_ids": ["A"],
            "source_id": "x_new",
        })
        self.assertIn(
            "record_count_at_or_above_floor",
            result["failed_checks"],
        )

    def test_series_and_source_collisions_are_blocked(self):
        self.assertIn(
            "no_series_identity_collision",
            self.gate(active_series_ids={"A"})["failed_checks"],
        )
        self.assertIn(
            "no_source_identity_collision",
            self.gate(active_source_ids={"x_new"})["failed_checks"],
        )

    def test_proprietary_or_missing_rights_is_blocked(self):
        self.assertIn(
            "rights_declared_and_not_proprietary",
            self.gate(rights="output_with_proprietary_inputs")[
                "failed_checks"
            ],
        )
        self.assertIn(
            "rights_declared_and_not_proprietary",
            self.gate(rights=None)["failed_checks"],
        )

    def test_out_of_order_observation_periods_are_blocked(self):
        result = self.gate(summary={
            "first_observation_period": "2026-06",
            "last_observation_period": "2020-01",
        })
        self.assertIn("observation_periods_ordered", result["failed_checks"])

    def test_gate_grants_no_scientific_effect(self):
        self.assertEqual(self.gate()["scientific_effect"], "none")
