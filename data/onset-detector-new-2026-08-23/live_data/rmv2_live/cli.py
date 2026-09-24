"""Command-line and launchd entry point for the local live-data subsystem."""

from __future__ import absolute_import, print_function

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

from .canonical import (
    CanonicalDataError,
    atomic_write_json,
    canonical_json_bytes,
    pretty_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
)
from .config import load_config, load_env_file
from .feed_factory import (
    apply_candidate_bundle,
    compile_onboarding_spec,
    materialize_candidate_bundle,
    probe_onboarding_source,
)
from .matrix import (
    build_source_matrix,
    source_matrix_definition_sha256,
    write_source_matrix,
)
from .pipeline import RefreshPipeline
from .server import create_server
from .store import (
    GENERATION_MEMBERS,
    SHA256_RE,
    SOURCE_ID_RE,
    LiveStore,
    attest_source_binding,
    generation_storage_fingerprint,
    read_verified_generation,
    safe_regular_file,
    source_binding_from_head,
    validate_source_binding,
    verify_source_binding,
)


AI_HOST_TOKENS = ("anthropic", "chatgpt", "claude", "gemini", "openai")


def default_project_root():
    return Path(__file__).resolve().parents[2]


def default_config(project_root):
    return Path(project_root) / "live_data" / "config" / "sources.v1.json"


def _context(args):
    project_root = Path(args.project_root or default_project_root()).resolve()
    config_path = Path(args.config or default_config(project_root)).resolve()
    load_env_file(config_path.parent / "local.env")
    config = load_config(config_path)
    return project_root, config


def _print(value):
    sys.stdout.buffer.write(pretty_json_bytes(value))


def command_refresh(args):
    project_root, config = _context(args)
    pipeline = RefreshPipeline(project_root, config)
    result = pipeline.refresh(args.source, due_only=args.due_only)
    _print(result)
    return 0


def command_status(args):
    project_root, config = _context(args)
    store = LiveStore(project_root, config)
    path = store.public / "operational_status.json"
    if not path.exists():
        path = store.public / "live_status.json"
    if not path.exists():
        _print({
            "schema_version": "recession-monitor-v2.live-status.v1",
            "service_state": "not_initialized",
        })
        return 1
    _print(read_json(path))
    return 0


def command_matrix(args):
    project_root, config = _context(args)
    pipeline = RefreshPipeline(project_root, config)
    pipeline.store.initialize()
    generated_at = pipeline.clock()
    coverage = pipeline.build_coverage(generated_at)
    matrix = build_source_matrix(
        project_root,
        config,
        pipeline.store,
        coverage,
        generated_at,
    )
    receipt = write_source_matrix(project_root, matrix)
    operational_path = pipeline.store.public / "operational_status.json"
    if operational_path.exists():
        operational = read_json(operational_path)
        operational["source_matrix"] = {
            "csv_bytes": receipt["csv_bytes"],
            "csv_sha256": receipt["csv_sha256"],
            "definition_sha256": receipt["definition_sha256"],
            "json_bytes": receipt["json_bytes"],
            "json_sha256": receipt["json_sha256"],
            "row_count": receipt["row_count"],
        }
        atomic_write_json(operational_path, operational)
    _print(receipt)
    return 0


def command_feed_factory_probe(args):
    project_root = Path(
        args.project_root or default_project_root()
    ).resolve()
    # Keyed adapters (e.g. fred_json_api) authenticate at probe time; load the
    # gitignored local.env so the required secret NAME is present in os.environ.
    load_env_file(project_root / "live_data" / "config" / "local.env")
    result = probe_onboarding_source(
        project_root,
        args.draft,
    )
    _print(result)
    return 0


def command_feed_factory_compile(args):
    project_root = Path(
        args.project_root or default_project_root()
    ).resolve()
    compiled = compile_onboarding_spec(
        project_root,
        args.spec,
    )
    bundle = materialize_candidate_bundle(
        project_root,
        compiled,
    )
    _print({
        "bundle_id": bundle["bundle_id"],
        "manifest_path": str(bundle["manifest_path"]),
        "receipt": compiled["receipt"],
        "schema_version": "recession-monitor-v2.feed-factory-compile.v1",
        "status": "CANDIDATE_NOT_ACTIVE",
    })
    return 0


def command_feed_factory_prepare(args):
    project_root = Path(
        args.project_root or default_project_root()
    ).resolve()
    # Keyed adapters (e.g. fred_json_api) authenticate at probe time; load the
    # gitignored local.env so the required secret NAME is present in os.environ.
    load_env_file(project_root / "live_data" / "config" / "local.env")
    probe = probe_onboarding_source(
        project_root,
        args.draft,
    )
    compiled = compile_onboarding_spec(
        project_root,
        probe["spec_path"],
    )
    bundle = materialize_candidate_bundle(
        project_root,
        compiled,
    )
    _print({
        "bundle_id": bundle["bundle_id"],
        "manifest_path": str(bundle["manifest_path"]),
        "probe": probe,
        "receipt": compiled["receipt"],
        "schema_version": "recession-monitor-v2.feed-factory-prepare.v1",
        "status": "CANDIDATE_NOT_ACTIVE",
    })
    return 0


def command_feed_factory_apply(args):
    project_root = Path(
        args.project_root or default_project_root()
    ).resolve()
    result = apply_candidate_bundle(
        project_root,
        args.bundle,
    )
    _print(result)
    return 0


def _read_inventory_json(path, allowed_root):
    return strict_json_loads(safe_regular_file(path, allowed_root))


def _verify_source_binding_worker(item):
    store_root, source = item
    # Content-addressed attestation: the launcher inventory needs only the
    # per-source {etag, last_modified, parser_id} facts, each a pure function of
    # the immutable normalized/receipt objects. Attesting reuses the cached
    # closure so the inventory is O(changed sources), not O(total normalized
    # bytes). The full closure remains the default for ``rmv2_live verify``.
    attestation = attest_source_binding(Path(store_root), source)
    return source["source_id"], {
        "etag": attestation["etag"],
        "last_modified": attestation["last_modified"],
        "parser_id": attestation["parser_id"],
    }


def _bounded_parallel_map(worker, items):
    items = list(items)
    if len(items) < 4:
        return [worker(item) for item in items]
    worker_count = min(4, len(items))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(worker, items, chunksize=1))


def _read_verified_generation_parallel(public_root, generations_root):
    """Authenticate one generation with bounded parallel source checks.

    This preserves ``read_verified_generation`` validation semantics while
    moving only independent source-evidence checks into a deterministic,
    bounded worker pool. The pointer and storage fingerprints still bracket
    the entire verification so concurrent mutation fails closed.
    """
    public_root = Path(public_root).resolve()
    generations_root = Path(generations_root).resolve()
    pointer_path = public_root / "latest.pointer.json"
    pointer_bytes_before = safe_regular_file(pointer_path, public_root)
    pointer = strict_json_loads(pointer_bytes_before)
    expected_pointer_keys = {
        "coverage_sha256",
        "generation_sha256",
        "manifest_sha256",
        "schema_version",
        "snapshot_sha256",
        "status_sha256",
        "updated_at",
    }
    if set(pointer) != expected_pointer_keys:
        raise CanonicalDataError("live pointer has an invalid key set")
    if pointer["schema_version"] != "recession-monitor-v2.live-pointer.v2":
        raise CanonicalDataError("unsupported live pointer schema")
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
                "live pointer contains an invalid digest"
            )
    if pointer["generation_sha256"] != pointer["manifest_sha256"]:
        raise CanonicalDataError(
            "generation and manifest identity differ"
        )

    generation_root = (
        generations_root / pointer["generation_sha256"]
    )
    probe_snapshot_bytes = safe_regular_file(
        generation_root / "snapshot.json",
        generations_root,
    )
    try:
        probe_snapshot = strict_json_loads(probe_snapshot_bytes)
    except (UnicodeDecodeError, ValueError) as exc:
        raise CanonicalDataError(
            "generation snapshot probe is invalid"
        ) from exc
    probe_source_bindings = probe_snapshot.get("sources")
    if not isinstance(probe_source_bindings, list):
        raise CanonicalDataError(
            "generation snapshot probe sources are invalid"
        )
    storage_fingerprint_before = generation_storage_fingerprint(
        public_root,
        generations_root,
        pointer,
        probe_source_bindings,
    )
    try:
        actual_names = {
            path.name for path in generation_root.iterdir()
        }
    except FileNotFoundError:
        raise
    if actual_names != set(GENERATION_MEMBERS) | {"manifest.json"}:
        raise CanonicalDataError(
            "generation contains an unexpected member set"
        )
    manifest_bytes = safe_regular_file(
        generation_root / "manifest.json",
        generations_root,
    )
    if sha256_bytes(manifest_bytes) != pointer["manifest_sha256"]:
        raise CanonicalDataError("generation manifest hash mismatch")
    manifest = strict_json_loads(manifest_bytes)
    if set(manifest) != {
        "created_at",
        "members",
        "schema_version",
        "source_head_receipt_sha256",
    }:
        raise CanonicalDataError(
            "generation manifest has an invalid key set"
        )
    if (
        manifest["schema_version"] !=
        "recession-monitor-v2.live-generation-manifest.v2"
    ):
        raise CanonicalDataError(
            "unsupported generation manifest schema"
        )
    if set(manifest["members"]) != set(GENERATION_MEMBERS):
        raise CanonicalDataError(
            "generation member set is incomplete"
        )
    manifest_source_receipts = manifest[
        "source_head_receipt_sha256"
    ]
    if not isinstance(manifest_source_receipts, dict):
        raise CanonicalDataError(
            "generation source receipt binding is invalid"
        )
    for source_id, receipt_sha256 in (
        manifest_source_receipts.items()
    ):
        if (
            not isinstance(source_id, str) or
            not SOURCE_ID_RE.match(source_id) or
            not isinstance(receipt_sha256, str) or
            not SHA256_RE.match(receipt_sha256)
        ):
            raise CanonicalDataError(
                "generation source receipt binding is invalid"
            )

    members = {}
    snapshot_value = None
    pointer_fields = {
        "coverage.json": "coverage_sha256",
        "snapshot.json": "snapshot_sha256",
        "status.json": "status_sha256",
    }
    for name in GENERATION_MEMBERS:
        specification = manifest["members"][name]
        if set(specification) != {
            "bytes",
            "sha256",
            "schema_version",
        }:
            raise CanonicalDataError(
                "generation member specification is invalid"
            )
        data = safe_regular_file(
            generation_root / name,
            generations_root,
        )
        if len(data) != specification["bytes"]:
            raise CanonicalDataError(
                "generation member byte count mismatch"
            )
        if sha256_bytes(data) != specification["sha256"]:
            raise CanonicalDataError(
                "generation member hash mismatch"
            )
        if (
            pointer[pointer_fields[name]] !=
            specification["sha256"]
        ):
            raise CanonicalDataError("pointer member hash mismatch")
        value = strict_json_loads(data)
        if value.get("schema_version") != specification["schema_version"]:
            raise CanonicalDataError(
                "generation member schema mismatch"
            )
        if name == "snapshot.json":
            snapshot_value = value
        members[name] = value

    snapshot_sources = snapshot_value.get("sources")
    if not isinstance(snapshot_sources, list):
        raise CanonicalDataError(
            "generation snapshot sources are invalid"
        )
    snapshot_source_receipts = {}
    ordered_sources = []
    for source in snapshot_sources:
        if not isinstance(source, dict):
            raise CanonicalDataError(
                "generation snapshot source is invalid"
            )
        source_id = source.get("source_id")
        receipt_sha256 = source.get("receipt_sha256")
        if (
            not isinstance(source_id, str) or
            not SOURCE_ID_RE.match(source_id) or
            source_id in snapshot_source_receipts or
            not isinstance(receipt_sha256, str) or
            not SHA256_RE.match(receipt_sha256)
        ):
            raise CanonicalDataError(
                "generation snapshot source is invalid"
            )
        snapshot_source_receipts[source_id] = receipt_sha256
        ordered_sources.append(source)
    if snapshot_source_receipts != manifest_source_receipts:
        raise CanonicalDataError(
            "generation source receipt binding differs from snapshot"
        )

    store_root = generations_root.parent
    source_head_metadata = dict(_bounded_parallel_map(
        _verify_source_binding_worker,
        (
            (str(store_root), source)
            for source in sorted(
                ordered_sources,
                key=lambda item: item["source_id"],
            )
        ),
    ))

    pointer_bytes_after = safe_regular_file(
        pointer_path,
        public_root,
    )
    if pointer_bytes_before != pointer_bytes_after:
        raise CanonicalDataError(
            "live pointer changed during generation read"
        )
    storage_fingerprint_after = generation_storage_fingerprint(
        public_root,
        generations_root,
        pointer,
        snapshot_sources,
    )
    if storage_fingerprint_before != storage_fingerprint_after:
        raise CanonicalDataError(
            "generation storage changed during verification"
        )
    return {
        "manifest": manifest,
        "members": members,
        "pointer": pointer,
        "pointer_bytes": pointer_bytes_before,
        "source_bindings": snapshot_sources,
        "source_head_metadata": source_head_metadata,
        "storage_fingerprint": storage_fingerprint_after,
    }


def _inventory_source_id(value):
    if not isinstance(value, dict):
        raise CanonicalDataError("Feed Factory artifact must be an object")
    source_value = value.get("source")
    if isinstance(source_value, dict):
        source_id = source_value.get("source_id")
    else:
        source_id = value.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        raise CanonicalDataError(
            "Feed Factory artifact lacks a source_id"
        )
    return source_id


def _inventory_collection(project_root, factory_root, pattern):
    paths = sorted(factory_root.glob(pattern))
    result_paths = []
    source_ids = []
    errors = []
    for path in paths:
        try:
            value = _read_inventory_json(path, factory_root)
            source_ids.append(_inventory_source_id(value))
            result_paths.append(str(path.relative_to(project_root)))
        except (CanonicalDataError, OSError, ValueError) as exc:
            errors.append("%s: %s" % (
                str(path.relative_to(project_root)),
                exc,
            ))
    return {
        "artifact_count": len(paths),
        "paths": result_paths,
        "source_count": len(set(source_ids)),
        "source_ids": sorted(set(source_ids)),
    }, errors


def _inventory_sources(project_root, errors):
    path = project_root / "live_data" / "config" / "sources.v1.json"
    try:
        active_bytes = safe_regular_file(path, project_root)
        value = strict_json_loads(active_bytes)
        rows = value.get("sources")
        if not isinstance(rows, list):
            raise CanonicalDataError("active sources must be a list")
        sources = {}
        for row in rows:
            if not isinstance(row, dict):
                raise CanonicalDataError("active source must be an object")
            source_id = row.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise CanonicalDataError("active source_id is invalid")
            if source_id in sources:
                raise CanonicalDataError(
                    "duplicate active source_id: %s" % source_id
                )
            sources[source_id] = row
        return sources, value, sha256_bytes(active_bytes)
    except (CanonicalDataError, OSError, ValueError) as exc:
        errors.append("active source config: %s" % exc)
        return {}, None, None


def _endpoint_identity(url):
    """Publisher route identity: scheme-insensitive host plus exact path.

    Two reservation rows and one active feed can name the same publisher
    route with different query strings. Query text selects fields or a
    window; it does not change which publisher object is being retrieved.
    """
    if not isinstance(url, str) or not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    host = (parts.netloc or "").lower()
    if not host:
        return None
    return (host, (parts.path or "").rstrip("/").lower())


def _inventory_reservations(
    project_root,
    enabled_source_ids,
    errors,
    enabled_endpoint_keys=None,
):
    path = (
        project_root / "live_data" / "config" /
        "planned_sources.v1.json"
    )
    groups = {
        "credential": [],
        "lower_priority": [],
        "normal": [],
    }
    endpoints = {}
    try:
        value = _read_inventory_json(path, project_root)
        rows = value.get("sources")
        if not isinstance(rows, list):
            raise CanonicalDataError("planned sources must be a list")
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise CanonicalDataError("planned source must be an object")
            source_id = row.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise CanonicalDataError("planned source_id is invalid")
            if source_id in seen:
                raise CanonicalDataError(
                    "duplicate planned source_id: %s" % source_id
                )
            seen.add(source_id)
            endpoints[source_id] = row.get("endpoint")
            role = row.get("role")
            if row.get("auth_env"):
                group = "credential"
            elif (
                isinstance(role, str) and
                role.startswith("lower_priority")
            ):
                group = "lower_priority"
            else:
                group = "normal"
            groups[group].append(source_id)
    except (CanonicalDataError, OSError, ValueError) as exc:
        errors.append("planned source config: %s" % exc)
    for source_ids in groups.values():
        source_ids.sort()
    configured_groups = {
        key: list(source_ids)
        for key, source_ids in sorted(groups.items())
    }
    enabled_endpoint_keys = frozenset(
        key for key in (enabled_endpoint_keys or ()) if key
    )
    fulfilled = {
        source_id
        for source_ids in configured_groups.values()
        for source_id in source_ids
        if source_id in enabled_source_ids or (
            _endpoint_identity(endpoints.get(source_id)) is not None and
            _endpoint_identity(endpoints.get(source_id)) in
            enabled_endpoint_keys
        )
    }
    fulfilled_source_ids = sorted(fulfilled)
    groups = {
        key: [
            source_id for source_id in source_ids
            if source_id not in fulfilled
        ]
        for key, source_ids in sorted(configured_groups.items())
    }
    counts = {
        key: len(value)
        for key, value in sorted(groups.items())
    }
    counts["total"] = sum(counts.values())
    configured_counts = {
        key: len(value)
        for key, value in sorted(configured_groups.items())
    }
    configured_counts["total"] = sum(configured_counts.values())
    return {
        "configured_counts": configured_counts,
        "configured_source_ids": configured_groups,
        "counts": counts,
        "fulfilled": {
            "count": len(fulfilled_source_ids),
            "source_ids": fulfilled_source_ids,
        },
        "source_ids": groups,
    }


def _inventory_blocked(
    project_root,
    verified_coverage,
    errors,
):
    path = (
        project_root / "live_data" / "public" /
        "source_coverage.json"
    )
    groups = {
        "rights_blocked": [],
        "target_quarantined": [],
    }
    coverage_states = {
        "blocked_rights": "rights_blocked",
        "quarantined_target_bearing": "target_quarantined",
    }
    try:
        if not isinstance(verified_coverage, dict):
            raise CanonicalDataError(
                "authenticated generation coverage is unavailable"
            )
        value = verified_coverage
        public_value = _read_inventory_json(path, project_root)
        if (
            canonical_json_bytes(public_value) !=
            canonical_json_bytes(value)
        ):
            errors.append(
                "public source coverage differs from authenticated "
                "generation"
            )
        rows = value.get("rows")
        if not isinstance(rows, list):
            raise CanonicalDataError("coverage rows must be a list")
        for row in rows:
            if not isinstance(row, dict):
                raise CanonicalDataError("coverage row must be an object")
            group = coverage_states.get(row.get("live_state"))
            if group is None:
                continue
            source_id = row.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise CanonicalDataError(
                    "blocked coverage source_id is invalid"
                )
            groups[group].append(source_id)
        declared_counts = value.get("counts")
        if isinstance(declared_counts, dict):
            for live_state, group in sorted(coverage_states.items()):
                declared = declared_counts.get(live_state)
                if (
                    isinstance(declared, int) and
                    declared != len(set(groups[group]))
                ):
                    raise CanonicalDataError(
                        "coverage %s count does not match rows" %
                        live_state
                    )
    except (CanonicalDataError, OSError, ValueError) as exc:
        errors.append("source coverage: %s" % exc)
    return {
        key: {
            "count": len(set(source_ids)),
            "source_ids": sorted(set(source_ids)),
        }
        for key, source_ids in sorted(groups.items())
    }


def _inventory_generation(project_root, active_config, errors):
    result = {
        "generation_id": None,
        "recovery_required": True,
        "source_count": 0,
        "source_ids": [],
    }
    public_root = project_root / "live_data" / "public"
    verified_coverage = None
    try:
        if active_config is None:
            raise CanonicalDataError(
                "active config is unavailable for generation verification"
            )
        store = LiveStore(project_root, active_config)
        generation = _read_verified_generation_parallel(
            store.public,
            store.root / "generations",
        )
        _verify_runtime_generation_receipt_closure(store, generation)
        pointer = generation["pointer"]
        receipt_map = generation["manifest"][
            "source_head_receipt_sha256"
        ]
        source_ids = sorted(receipt_map)
        result.update({
            "generation_id": pointer["generation_sha256"],
            "source_count": len(source_ids),
            "source_ids": source_ids,
        })
        verified_coverage = generation["members"]["coverage.json"]
    except (CanonicalDataError, OSError, ValueError) as exc:
        errors.append("active generation: %s" % exc)

    status_path = public_root / "operational_status.json"
    if not status_path.exists():
        status_path = public_root / "live_status.json"
    service_state = None
    health = {}
    try:
        status = _read_inventory_json(status_path, public_root)
        service_state = status.get("service_state")
        health = status.get("current_source_health")
        if not isinstance(health, dict):
            raise CanonicalDataError(
                "current source health must be an object"
            )
        for source_id, value in health.items():
            if (
                not isinstance(source_id, str) or
                not isinstance(value, str)
            ):
                raise CanonicalDataError(
                    "current source health entry is invalid"
                )
        recovery_required = status.get(
            "generation_recovery_required",
            False,
        )
        if not isinstance(recovery_required, bool):
            raise CanonicalDataError(
                "generation recovery flag must be boolean"
            )
        result["recovery_required"] = recovery_required
        status_generation = status.get("active_generation_sha256")
        if (
            status_generation is not None and
            status_generation != result["generation_id"]
        ):
            raise CanonicalDataError(
                "operational status generation differs from pointer"
            )
    except (CanonicalDataError, OSError, ValueError) as exc:
        errors.append("operational status: %s" % exc)
        result["recovery_required"] = True
    return result, health, service_state, verified_coverage


def _inventory_candidates(
    project_root,
    factory_root,
    paths,
    active_sources,
    active_config_sha256,
    live_source_ids,
    healthy_source_ids,
    errors,
):
    lifecycle = []
    for manifest_path in paths:
        try:
            manifest = _read_inventory_json(
                manifest_path,
                factory_root,
            )
            source_id = _inventory_source_id(manifest)
            candidate_config_path = (
                manifest_path.parent / "candidate.sources.v1.json"
            )
            candidate_config = _read_inventory_json(
                candidate_config_path,
                factory_root,
            )
            candidate_rows = candidate_config.get("sources")
            if not isinstance(candidate_rows, list):
                raise CanonicalDataError(
                    "candidate sources must be a list"
                )
            matches = [
                row for row in candidate_rows
                if (
                    isinstance(row, dict) and
                    row.get("source_id") == source_id
                )
            ]
            if len(matches) != 1:
                raise CanonicalDataError(
                    "candidate source must occur exactly once"
                )
            active_source = active_sources.get(source_id)
            source_already_active = active_source is not None
            predecessor_matches_active = (
                manifest.get("predecessor_config_sha256") ==
                active_config_sha256
            )
            config_applied = (
                source_already_active and
                canonical_json_bytes(active_source) ==
                canonical_json_bytes(matches[0])
            )
            live = (
                config_applied and
                source_id in live_source_ids and
                source_id in healthy_source_ids
            )
            if live:
                state = "LIVE"
            elif config_applied:
                state = "CONFIGURED_AWAITING_REFRESH"
            elif (
                manifest.get("status") == "CANDIDATE_NOT_ACTIVE" and
                predecessor_matches_active
            ):
                state = "READY_FOR_REVIEW"
            else:
                state = "SUPERSEDED_OR_HISTORICAL"
            lifecycle.append({
                "bundle_id": manifest_path.parent.name,
                "config_applied": config_applied,
                "live": live,
                "manifest_path": str(
                    manifest_path.relative_to(project_root)
                ),
                "predecessor_matches_active": predecessor_matches_active,
                "source_already_active": source_already_active,
                "source_id": source_id,
                "state": state,
            })
        except (CanonicalDataError, OSError, ValueError) as exc:
            errors.append("%s: %s" % (
                str(manifest_path.relative_to(project_root)),
                exc,
            ))
    return sorted(
        lifecycle,
        key=lambda item: (
            item["source_id"],
            item["bundle_id"],
        ),
    )


def _factory_status_reason(overall_state):
    reasons = {
        "DEGRADED": (
            "A configured feed, status file, or authoritative generation "
            "requires repair before the scope can be called healthy."
        ),
        "READY_FOR_REVIEW": (
            "At least one isolated candidate is prepared but has not been "
            "applied to the active configuration."
        ),
        "WORKING": (
            "Actionable Feed Factory work remains before the declared "
            "acquisition scope is complete."
        ),
        "SCOPED_WORK_COMPLETE": (
            "Every declared source is healthy and no actionable or blocked "
            "exception remains in the Feed Factory inventory."
        ),
        "BLOCKED_EXCEPTIONS_ONLY": (
            "All ordinary actionable work is closed, but explicit credential, "
            "lower-priority, rights, or target exceptions remain."
        ),
    }
    return reasons[overall_state]


def _build_feed_factory_inventory(project_root):
    project_root = Path(project_root).resolve()
    factory_root = project_root / "live_data" / "feed_factory"
    errors = []
    patterns = {
        "candidates": "candidates/*/*/manifest.json",
        "drafts": "drafts/*.json",
        "probes": "probes/*/*/probe.receipt.json",
        "recipes": "recipes/*.json",
    }
    artifacts = {}
    artifact_paths = {}
    for name, pattern in sorted(patterns.items()):
        collection, collection_errors = _inventory_collection(
            project_root,
            factory_root,
            pattern,
        )
        artifacts[name] = collection
        artifact_paths[name] = sorted(factory_root.glob(pattern))
        errors.extend(collection_errors)

    active_sources, active_config, active_config_sha256 = _inventory_sources(
        project_root,
        errors,
    )
    enabled_source_ids = {
        source_id
        for source_id, value in active_sources.items()
        if value.get("enabled") is True
    }
    archival_source_ids = {
        source_id
        for source_id, value in active_sources.items()
        if value.get("archival") is True
    }
    # Archival (frozen-admission) rows are config-known runtime heads that are
    # never fetched; they belong in every operational/generation source set.
    admissible_source_ids = enabled_source_ids | archival_source_ids
    reservations = _inventory_reservations(
        project_root,
        enabled_source_ids,
        errors,
        enabled_endpoint_keys={
            _endpoint_identity(
                value.get("endpoint") or value.get("url")
            )
            for source_id, value in active_sources.items()
            if value.get("enabled") is True
        },
    )
    (
        generation,
        health,
        service_state,
        verified_coverage,
    ) = _inventory_generation(
        project_root,
        active_config,
        errors,
    )
    blocked = _inventory_blocked(
        project_root,
        verified_coverage,
        errors,
    )
    live_source_ids = set(generation["source_ids"])
    healthy_status_ids = {
        source_id
        for source_id, state in health.items()
        if state == "healthy"
    }
    healthy_source_ids = (
        enabled_source_ids &
        live_source_ids &
        healthy_status_ids
    )
    failed_source_ids = {
        source_id
        for source_id in enabled_source_ids
        if (
            source_id in health and
            health[source_id] != "healthy"
        )
    }
    not_yet_refreshed_ids = (
        enabled_source_ids -
        healthy_source_ids -
        failed_source_ids
    )
    health_source_ids = set(health)
    if health_source_ids != admissible_source_ids:
        errors.append(
            "operational health source IDs are not the exact enabled set; "
            "missing=%s extra=%s" % (
                ",".join(sorted(
                    admissible_source_ids - health_source_ids
                )) or "none",
                ",".join(sorted(
                    health_source_ids - admissible_source_ids
                )) or "none",
            )
        )
    unexpected_generation_ids = live_source_ids - admissible_source_ids
    if unexpected_generation_ids:
        errors.append(
            "active generation contains sources absent or disabled in "
            "current config: %s" %
            ",".join(sorted(unexpected_generation_ids))
        )

    lifecycle = _inventory_candidates(
        project_root,
        factory_root,
        artifact_paths["candidates"],
        active_sources,
        active_config_sha256,
        live_source_ids,
        healthy_source_ids,
        errors,
    )
    pending_candidates = [
        item for item in lifecycle
        if item["state"] in (
            "CONFIGURED_AWAITING_REFRESH",
            "READY_FOR_REVIEW",
        )
    ]
    ready_for_review = any(
        item["state"] == "READY_FOR_REVIEW"
        for item in lifecycle
    )
    normal_actionable_ids = set(
        reservations["source_ids"]["normal"]
    )
    credential_exception_ids = set(
        reservations["source_ids"]["credential"]
    )
    lower_priority_exception_ids = set(
        reservations["source_ids"]["lower_priority"]
    )
    rights_exception_ids = set(
        blocked["rights_blocked"]["source_ids"]
    )
    target_exception_ids = set(
        blocked["target_quarantined"]["source_ids"]
    )
    factory_source_ids = set()
    for artifact in artifacts.values():
        factory_source_ids.update(artifact["source_ids"])
    unresolved_factory_ids = factory_source_ids - healthy_source_ids

    degraded = (
        bool(errors) or
        bool(failed_source_ids) or
        generation["recovery_required"] or
        service_state != "ready"
    )
    if degraded:
        overall_state = "DEGRADED"
    elif ready_for_review:
        overall_state = "READY_FOR_REVIEW"
    elif (
        not_yet_refreshed_ids or
        unresolved_factory_ids or
        normal_actionable_ids
    ):
        overall_state = "WORKING"
    elif (
        credential_exception_ids or
        lower_priority_exception_ids or
        rights_exception_ids or
        target_exception_ids
    ):
        overall_state = "BLOCKED_EXCEPTIONS_ONLY"
    else:
        overall_state = "SCOPED_WORK_COMPLETE"

    counts = {
        name: value["artifact_count"]
        for name, value in sorted(artifacts.items())
    }
    report = {
        "active_generation": generation,
        "blocked_or_deferred": blocked,
        "candidate_lifecycle": lifecycle,
        "completion_blockers": {
            "credential_exceptions": sorted(
                credential_exception_ids
            ),
            "failed_sources": sorted(failed_source_ids),
            "lower_priority_exceptions": sorted(
                lower_priority_exception_ids
            ),
            "normal_actionable_reservations": sorted(
                normal_actionable_ids
            ),
            "not_yet_refreshed_sources": sorted(
                not_yet_refreshed_ids
            ),
            "ready_for_review_candidates": sorted(set(
                item["source_id"]
                for item in lifecycle
                if item["state"] == "READY_FOR_REVIEW"
            )),
            "rights_exceptions": sorted(rights_exception_ids),
            "target_quarantine_exceptions": sorted(
                target_exception_ids
            ),
            "unresolved_factory_sources": sorted(
                unresolved_factory_ids
            ),
        },
        "counts": counts,
        "errors": errors,
        "factory_artifacts": artifacts,
        "factory_root": str(factory_root),
        "overall_state": overall_state,
        "overall_state_reason": _factory_status_reason(overall_state),
        "pending_candidates": pending_candidates,
        "reservations": reservations,
        "schema_version": (
            "recession-monitor-v2.feed-factory-inventory.v1"
        ),
        "scientific_effect": "none",
        "scope_notice": (
            "This reports the current accessible scope; not every possible "
            "dataset is collected. Credential-bound, rights-blocked, "
            "target-quarantined, publisher-unavailable, and intentionally "
            "deferred sources are tracked separately from active feed "
            "progress."
        ),
        "sources": {
            "enabled": {
                "count": len(enabled_source_ids),
                "source_ids": sorted(enabled_source_ids),
            },
            "failed": {
                "count": len(failed_source_ids),
                "source_ids": sorted(failed_source_ids),
            },
            "healthy": {
                "count": len(healthy_source_ids),
                "source_ids": sorted(healthy_source_ids),
            },
            "not_yet_refreshed": {
                "count": len(not_yet_refreshed_ids),
                "source_ids": sorted(not_yet_refreshed_ids),
            },
        },
        "status": "FAIL" if overall_state == "DEGRADED" else "PASS",
    }
    return report


def _print_feed_factory_inventory(report):
    sources = report["sources"]
    reservations = report["reservations"]["counts"]
    configured_reservations = report["reservations"][
        "configured_counts"
    ]
    fulfilled_reservations = report["reservations"]["fulfilled"]
    blocked = report["blocked_or_deferred"]
    generation = report["active_generation"]
    print("Recession Monitor V2 Feed Factory Status")
    print("Overall: %s" % report["overall_state"])
    print(report["overall_state_reason"])
    print("")
    print(
        "Feeds: %d enabled | %d healthy | %d failed | "
        "%d awaiting first refresh" % (
            sources["enabled"]["count"],
            sources["healthy"]["count"],
            sources["failed"]["count"],
            sources["not_yet_refreshed"]["count"],
        )
    )
    print(
        "Active generation: %s (%d sources)" % (
            generation["generation_id"] or "unavailable",
            generation["source_count"],
        )
    )
    print(
        "Factory evidence: %d drafts | %d probes | %d recipes | "
        "%d candidates" % (
            report["counts"]["drafts"],
            report["counts"]["probes"],
            report["counts"]["recipes"],
            report["counts"]["candidates"],
        )
    )
    print(
        "Review/refresh queue: %d candidate artifacts" %
        len(report["pending_candidates"])
    )
    print(
        "Actionable normal reservations remaining: %d" %
        len(
            report["completion_blockers"][
                "normal_actionable_reservations"
            ]
        )
    )
    print(
        "Outstanding reservations: %d total (%d normal, %d credential, "
        "%d lower-priority)" % (
            reservations["total"],
            reservations["normal"],
            reservations["credential"],
            reservations["lower_priority"],
        )
    )
    print(
        "Configured reservation rows: %d | already fulfilled: %d" % (
            configured_reservations["total"],
            fulfilled_reservations["count"],
        )
    )
    print(
        "Blocked/deferred: %d rights-blocked | %d target-quarantined" % (
            blocked["rights_blocked"]["count"],
            blocked["target_quarantined"]["count"],
        )
    )
    if report["errors"]:
        print("")
        print("Fail-closed findings:")
        for error in report["errors"]:
            print("- %s" % error)
    print("")
    print(report["scope_notice"])


def command_feed_factory_inventory(args):
    project_root = Path(
        args.project_root or default_project_root()
    ).resolve()
    report = _build_feed_factory_inventory(project_root)
    if args.json:
        _print(report)
    else:
        _print_feed_factory_inventory(report)
    return 1 if report["overall_state"] == "DEGRADED" else 0


def _verify_runtime_generation_receipt_closure(store, generation):
    runtime_heads = store.all_source_heads()
    runtime_bindings = {}
    source_head_metadata = generation.get("source_head_metadata")
    for source_id, head in sorted(runtime_heads.items()):
        if source_head_metadata is None:
            store.verify_source_head(source_id, head)
        binding = source_binding_from_head(source_id, head)
        if source_head_metadata is not None:
            if not isinstance(source_head_metadata, dict):
                raise CanonicalDataError(
                    "verified source-head metadata is invalid"
                )
            metadata = source_head_metadata.get(source_id)
            if (
                not isinstance(metadata, dict) or
                set(metadata) != {
                    "etag",
                    "last_modified",
                    "parser_id",
                } or
                metadata["parser_id"] !=
                "rmv2-live/%s" % head["adapter"] or
                metadata["etag"] != head["etag"] or
                metadata["last_modified"] != head["last_modified"]
            ):
                raise CanonicalDataError(
                    "runtime source head does not match immutable evidence"
                )
        runtime_bindings[source_id] = binding
    runtime_receipts = {
        source_id: binding["receipt_sha256"]
        for source_id, binding in runtime_bindings.items()
    }
    manifest_map = generation["manifest"]["source_head_receipt_sha256"]
    snapshot_bindings = {
        source["source_id"]: validate_source_binding(source)
        for source in generation["members"]["snapshot.json"]["sources"]
    }
    snapshot_receipts = {
        source_id: binding["receipt_sha256"]
        for source_id, binding in snapshot_bindings.items()
    }
    if (
        runtime_bindings != snapshot_bindings or
        runtime_receipts != manifest_map or
        runtime_receipts != snapshot_receipts
    ):
        raise CanonicalDataError(
            "runtime source evidence differs from active generation"
        )
    return runtime_bindings


def _verify_store(store):
    checks = []
    for source_id, head in sorted(store.all_source_heads().items()):
        store.verify_source_head(source_id, head)
        checks.append(source_id)
    generation = None
    pointer_path = store.public / "latest.pointer.json"
    if pointer_path.exists():
        # The loop above is the one full raw -> normalized -> receipt closure
        # pass.  Authenticate the generation through the content-addressed
        # attestations created at publish time so the same immutable normalized
        # objects are not parsed four more times by the generation/config
        # closure checks.
        generation = _read_verified_generation_parallel(
            store.public,
            store.root / "generations",
        )
        _verify_runtime_generation_receipt_closure(store, generation)
        pointer = generation["pointer"]
        convenience = {
            "live_snapshot.json": "snapshot.json",
            "live_snapshot.lkg.json": "snapshot.json",
            "live_status.json": "status.json",
            "source_coverage.json": "coverage.json",
        }
        for public_name, generation_name in convenience.items():
            public_data = safe_regular_file(
                store.public / public_name,
                store.public,
            )
            expected = canonical_json_bytes(
                generation["members"][generation_name]
            )
            if public_data != expected:
                raise CanonicalDataError(
                    "public convenience file does not match generation: %s" %
                    public_name
                )
        lkg_pointer = safe_regular_file(
            store.public / "latest.lkg.pointer.json",
            store.public,
        )
        if lkg_pointer != generation["pointer_bytes"]:
            raise CanonicalDataError("LKG pointer does not match current generation")
        if pointer["generation_sha256"] != pointer["manifest_sha256"]:
            raise CanonicalDataError("generation root is not the manifest identity")

    for directory in (store.root / "receipts", store.root / "attempts"):
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.json")):
            expected = path.stem
            data = path.read_bytes()
            if sha256_bytes(data) != expected:
                raise CanonicalDataError(
                    "content-addressed record hash mismatch: %s" % path.name
                )
    operational_path = store.public / "operational_status.json"
    if operational_path.exists():
        operational = read_json(operational_path)
        matrix_binding = operational.get("source_matrix")
        if matrix_binding:
            matrix_root = store.project_root / "live_data" / "catalog"
            for kind in ("csv", "json"):
                matrix_path = matrix_root / ("source_matrix.v1." + kind)
                data = safe_regular_file(matrix_path, matrix_root)
                if len(data) != matrix_binding[kind + "_bytes"]:
                    raise CanonicalDataError(
                        "source matrix byte count mismatch: %s" % kind
                    )
                if sha256_bytes(data) != matrix_binding[kind + "_sha256"]:
                    raise CanonicalDataError(
                        "source matrix hash mismatch: %s" % kind
                    )
    return checks, generation


def _verify_config_generation_closure(
    project_root,
    config,
    store,
    generation=None,
):
    """Reject a scheduler/catalog generation built from stale source config."""
    matrix_root = Path(project_root) / "live_data" / "catalog"
    matrix_path = matrix_root / "source_matrix.v1.json"
    if not matrix_path.exists():
        return {
            "status": "not_applicable_no_materialized_matrix",
        }
    matrix = read_json(matrix_path)
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        raise CanonicalDataError("source matrix rows are invalid")
    expected_definition = source_matrix_definition_sha256(rows)
    if matrix.get("definition_sha256") != expected_definition:
        raise CanonicalDataError("source matrix definition hash is invalid")
    configured_ids = {
        source["source_id"]
        for source in config["sources"]
        if source["enabled"]
    }
    # Archival (frozen-admission) rows are config-known runtime heads that are
    # published into the generation but are NOT active collectors: they never
    # refresh. They belong in the head/snapshot sets, not the active set.
    admissible_ids = configured_ids | {
        source["source_id"]
        for source in config["sources"]
        if source.get("archival")
    }
    active_ids = {
        row.get("source_id")
        for row in rows
        if row.get("record_kind") == "active_collector"
    }
    if active_ids != configured_ids:
        raise CanonicalDataError(
            "source matrix active collectors do not match current config"
        )
    head_ids = set(store.all_source_heads())
    if head_ids != admissible_ids:
        raise CanonicalDataError(
            "source heads do not match current enabled collector set"
        )

    if generation is None:
        generation = _read_verified_generation_parallel(
            store.public,
            store.root / "generations",
        )
    _verify_runtime_generation_receipt_closure(store, generation)
    snapshot_ids = {
        row.get("source_id")
        for row in generation["members"]["snapshot.json"].get("sources", [])
        if isinstance(row, dict)
    }
    if snapshot_ids != admissible_ids:
        raise CanonicalDataError(
            "immutable snapshot sources do not match current enabled collectors"
        )
    generation_status = generation["members"]["status.json"]
    matrix_binding = generation_status.get("source_matrix")
    if (
        not isinstance(matrix_binding, dict) or
        matrix_binding.get("row_count") != len(rows)
    ):
        raise CanonicalDataError(
            "immutable generation source matrix is stale for current config"
        )
    if matrix_binding.get("definition_sha256") != expected_definition:
        raise CanonicalDataError(
            "immutable generation source definition is stale for current config"
        )
    if generation_status.get("snapshot_source_count") != len(admissible_ids):
        raise CanonicalDataError(
            "immutable generation source count is stale for current config"
        )
    return {
        "configured_source_count": len(configured_ids),
        "admissible_source_count": len(admissible_ids),
        "matrix_row_count": len(rows),
        "status": "PASS",
    }


def command_verify(args):
    project_root, config = _context(args)
    for source in config["sources"]:
        strings = [source["endpoint"]] + list(source["allowed_hosts"])
        for value in strings:
            lower = value.lower()
            if any(token in lower for token in AI_HOST_TOKENS):
                raise CanonicalDataError("AI endpoint token found in source configuration")
    store = LiveStore(project_root, config)
    store.initialize()
    checked_sources, generation = _verify_store(store)
    closure = _verify_config_generation_closure(
        project_root,
        config,
        store,
        generation=generation,
    )
    _print({
        "api_host": config["api"]["host"],
        "api_port": config["api"]["port"],
        "checked_source_heads": checked_sources,
        "config_generation_closure": closure,
        "configured_sources": len(config["sources"]),
        "no_ai_endpoints": True,
        "schema_version": "recession-monitor-v2.live-verification.v1",
        "status": "PASS",
    })
    return 0


def _ensure_initial_public(project_root, config):
    store = LiveStore(project_root, config)
    store.initialize()
    pipeline = RefreshPipeline(project_root, config)
    if not (store.public / "live_status.json").exists():
        now = pipeline.clock()
        coverage = pipeline.build_coverage(now)
        current_source_health, current_source_health_counts = (
            pipeline._current_source_health()
        )
        status = {
            "api": {
                "host": config["api"]["host"],
                "port": config["api"]["port"],
            },
            "coverage_counts": coverage["counts"],
            "current_source_health": current_source_health,
            "current_source_health_counts": current_source_health_counts,
            "data_policy": {
                "ai_dependency": "none",
                "browser_scientific_calculation": "prohibited",
                "scientific_model_binding": "not_authorized",
            },
            "generated_at": now,
            "generation_recovery_required": False,
            "latest_attempt_counts": {},
            "last_refresh_outcomes": [],
            "last_refresh_state_counts": {},
            "no_ai": True,
            "schema_version": "recession-monitor-v2.live-status.v1",
            "scientific_outputs_updated": False,
            "service_state": "awaiting_first_refresh",
            "snapshot_series_count": 0,
            "snapshot_source_count": 0,
        }
        status[
            "schema_version"
        ] = "recession-monitor-v2.live-operational-status.v1"
        status["active_generation_sha256"] = None
        status["generation_advanced"] = False
        atomic_write_json(store.public / "operational_status.json", status)
        atomic_write_json(store.public / "source_coverage.json", coverage)
    return store


def command_serve(args):
    project_root, config = _context(args)
    store = _ensure_initial_public(project_root, config)
    server = create_server(
        config["api"]["host"],
        config["api"]["port"],
        store.public,
        store.root / "generations",
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def _warm_server(server):
    """Best-effort cache warm; a warm failure must never stop the service."""
    if server is None:
        return
    try:
        server.warm()
    except Exception as exc:
        print(
            "live warm skipped: %s: %s" % (type(exc).__name__, exc),
            file=sys.stderr,
        )


def _read_pointer_bytes(public_root):
    """Cheap O(1) read of the active generation pointer, or None if absent."""
    try:
        return (public_root / "latest.pointer.json").read_bytes()
    except FileNotFoundError:
        return None


def _scheduler(project_root, config, stop_event, server=None):
    pipeline = RefreshPipeline(project_root, config)
    tick = config["service"]["refresh_tick_seconds"]
    public_root = pipeline.store.public
    # The server was warmed to the active pointer at boot (command_service).
    # Track it so we only re-warm when the published generation actually moves.
    warmed_pointer = _read_pointer_bytes(public_root)
    while not stop_event.is_set():
        try:
            pipeline.refresh(due_only=True)
        except RuntimeError as exc:
            if "another live-data refresh is already running" in str(exc):
                print(
                    "live refresh skipped: publication barrier held by "
                    "another holder; retrying next tick",
                    file=sys.stderr,
                )
            else:
                print("live refresh error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        except Exception as exc:
            print("live refresh error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        # Incremental warm: re-authenticate the generation off the request path
        # ONLY when the published pointer actually moved (whether this scheduler
        # or the autopilot published it). An idle tick leaves the pointer byte-
        # identical, so this is an O(1) pointer read and NO O(store) re-hash —
        # the per-tick full closure re-verification that wedged the service is
        # gone. Full closure re-verification lives in `verify --full`, on demand.
        current_pointer = _read_pointer_bytes(public_root)
        if current_pointer is not None and current_pointer != warmed_pointer:
            _warm_server(server)
            warmed_pointer = current_pointer
        stop_event.wait(tick)


def command_service(args):
    project_root, config = _context(args)
    store = _ensure_initial_public(project_root, config)
    stop_event = threading.Event()
    # Build the socket without listening yet, pre-authenticate the active
    # generation, and only then start accepting connections. A client that
    # arrives during the one-time warm gets a fast connection refusal (and
    # retries) instead of a request that blocks for the whole verification.
    server = create_server(
        config["api"]["host"],
        config["api"]["port"],
        store.public,
        store.root / "generations",
        bind_and_activate=False,
    )
    _warm_server(server)
    server.server_bind()
    server.server_activate()
    worker = threading.Thread(
        target=_scheduler,
        args=(project_root, config, stop_event, server),
        name="rmv2-live-refresh",
    )
    worker.daemon = True
    worker.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        stop_event.set()
        server.server_close()
        worker.join(timeout=5)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Recession Monitor V2 live data")
    parser.add_argument("--config", help="path to sources.v1.json")
    parser.add_argument("--project-root", help="Recession Monitor V2 root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser("refresh", help="run one acquisition pass")
    refresh.add_argument("--due-only", action="store_true")
    refresh.add_argument("--source", action="append", default=[])
    refresh.set_defaults(func=command_refresh)

    serve = subparsers.add_parser("serve", help="serve existing local snapshot")
    serve.set_defaults(func=command_serve)

    service = subparsers.add_parser("service", help="refresh and serve continuously")
    service.set_defaults(func=command_service)

    matrix = subparsers.add_parser(
        "matrix",
        help="materialize the Claude/Codex source coverage matrix",
    )
    matrix.set_defaults(func=command_matrix)

    status = subparsers.add_parser("status", help="print current service status")
    status.set_defaults(func=command_status)

    verify = subparsers.add_parser("verify", help="verify config and local store")
    verify.set_defaults(func=command_verify)

    feed_factory = subparsers.add_parser(
        "feed-factory",
        help="probe, compile, and stage official-source onboarding recipes",
    )
    factory_commands = feed_factory.add_subparsers(
        dest="feed_factory_command",
        required=True,
    )
    factory_probe = factory_commands.add_parser(
        "probe",
        help="fetch one draft into isolated evidence and generate a recipe",
    )
    factory_probe.add_argument("--draft", required=True)
    factory_probe.set_defaults(func=command_feed_factory_probe)

    factory_compile = factory_commands.add_parser(
        "compile",
        help="fixture-test one recipe and materialize a candidate bundle",
    )
    factory_compile.add_argument("--spec", required=True)
    factory_compile.set_defaults(func=command_feed_factory_compile)

    factory_prepare = factory_commands.add_parser(
        "prepare",
        help="probe and compile one draft without activating it",
    )
    factory_prepare.add_argument("--draft", required=True)
    factory_prepare.set_defaults(func=command_feed_factory_prepare)

    factory_apply = factory_commands.add_parser(
        "apply",
        help="apply reviewed config bytes; refresh and service reload remain required",
    )
    factory_apply.add_argument("--bundle", required=True)
    factory_apply.set_defaults(func=command_feed_factory_apply)

    factory_inventory = factory_commands.add_parser(
        "inventory",
        help=(
            "show Feed Factory evidence, candidate, live-source, "
            "reservation, and completion status"
        ),
    )
    factory_inventory.add_argument(
        "--json",
        action="store_true",
        help="emit the authoritative lifecycle report as JSON",
    )
    factory_inventory.set_defaults(func=command_feed_factory_inventory)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (CanonicalDataError, OSError, RuntimeError, ValueError) as exc:
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
