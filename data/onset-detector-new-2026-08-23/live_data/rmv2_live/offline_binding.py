"""B-LAND-3 §1/§2 — bind an offline (on-disk ALFRED vintage) landing into the
store as a first-class source: source object + normalized object + OFFLINE
acquisition receipt + source head + status, so it can be published into a
generation exactly like a live_http source.

This supersedes B-LAND-2's transport-only stop (offline_admission.py, which
landed only the object + a provenance SIDECAR and could not bind). The owner's
2026-08-05 ruling (Option a) is encoded here: the offline receipt is the ONE
provenance home (§24) — it folds in the per-file source shas, the transcoder
identity, the emitted response-schema sha, and the as-of stamp, carries NO
fabricated http request/response block, and is verified by the additive offline
branch of ``store.verify_source_binding`` / ``store.verify_offline_source_binding``.

Contract (unchanged from B-LAND-2): no network (the http client seam is never
referenced), no AI, deterministic. Source CSV bytes are read, never written.
"""
from __future__ import absolute_import

import hashlib

from . import feed_factory
from . import vintage_csv_transcoder as vct
from .adapters import normalize
from .canonical import CanonicalDataError
from .store import (
    OFFLINE_ACQUISITION_KIND,
    OFFLINE_ACQUISITION_RECEIPT_SCHEMA,
    OFFLINE_CURRENT_ACQUISITION_KIND,
    OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA,
    source_binding_from_head,
)


def build_offline_receipt(
    source,
    source_bytes_sha256,
    normalized_sha256,
    file_provenance,
    response_schema_sha256,
    source_bytes_length,
    as_of,
    predecessor_receipt_sha256,
    transcoder_parser_version=vct.TRANSCODER_PARSER_VERSION,
):
    """The single offline provenance home (§24). No http request/response.

    ``transcoder_parser_version`` names the exact on-disk shape reshaped into the
    output_type=2 body (the ALFRED long-CSV shape by default; the FRED-MD panel
    shape when B-LAND-3C-R2 binds a panel base) so the receipt records WHICH
    transcoder produced the bytes it hashes."""
    return {
        "acquisition_kind": OFFLINE_ACQUISITION_KIND,
        "as_of": as_of,
        "clocks": {
            "provider_available_at": as_of,
            "publisher_released_at": None,
            "retrieved_at": as_of,
            "validated_at": as_of,
        },
        "information_set_mode": source["information_set_mode"],
        "normalized_sha256": normalized_sha256,
        "outcome": "transcoded_and_validated",
        "predecessor_receipt_sha256": predecessor_receipt_sha256,
        "publisher": source["publisher"],
        "rights_status": source["rights_status"],
        "schema_version": OFFLINE_ACQUISITION_RECEIPT_SCHEMA,
        "source_bytes_sha256": source_bytes_sha256,
        "source_files": [
            {
                "base": entry["base"],
                "row_count": entry["row_count"],
                "source_path": entry["source_path"],
                "source_sha256": entry["source_sha256"],
                "vintage": entry["vintage"],
            }
            for entry in file_provenance
        ],
        "source_id": source["source_id"],
        "transcoder": {
            "parser_version": transcoder_parser_version,
            "response_schema_sha256": response_schema_sha256,
            "source_bytes_length": source_bytes_length,
        },
    }


def build_offline_current_receipt(
    source,
    source_bytes_sha256,
    normalized_sha256,
    cache_manifest,
    parser_id,
    retrieved_at,
    predecessor_receipt_sha256,
):
    """The single offline-current provenance home. No http request/response, no
    per-file vintage list, no transcoder identity — the cache bytes ARE the
    source object. Cites the sha-manifested prefetch cache (url + fetch UTC +
    sha256 + byte length) as acquisition provenance and records WHICH live parser
    normalized those bytes."""
    return {
        "acquisition_kind": OFFLINE_CURRENT_ACQUISITION_KIND,
        "cache_manifest": {
            "fetch_utc": cache_manifest["fetch_utc"],
            "source_bytes_length": cache_manifest["source_bytes_length"],
            "source_sha256": cache_manifest["source_sha256"],
            "url": cache_manifest["url"],
        },
        "clocks": {
            "provider_available_at": cache_manifest["fetch_utc"],
            "publisher_released_at": None,
            "retrieved_at": retrieved_at,
            "validated_at": retrieved_at,
        },
        "information_set_mode": source["information_set_mode"],
        "normalized_sha256": normalized_sha256,
        "outcome": "bound_offline_current",
        "parser_id": parser_id,
        "predecessor_receipt_sha256": predecessor_receipt_sha256,
        "publisher": source["publisher"],
        "rights_status": source["rights_status"],
        "schema_version": OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA,
        "source_bytes_sha256": source_bytes_sha256,
        "source_id": source["source_id"],
    }


def bind_offline_current(
    pipeline, source, cache_bytes, cache_manifest, retrieved_at,
    predecessor_receipt_sha256=None,
):
    """Bind one prefetch-cached, adapter-normalizable body as a store source head
    WITHOUT the FRED vintage transcoder / deep-parser path.

    ZERO network: never references ``pipeline.http_client``. The ``cache_bytes``
    are stored byte-unchanged as the source object (no transcode); ``normalize``
    routes on ``source["adapter"]`` to the same live parser the online lane would
    use, so a current_revised (or other non-vintage) lane lands identically to a
    live fetch minus the network. ``cache_manifest`` (url + fetch_utc +
    source_sha256 + source_bytes_length) is the acquisition provenance carried in
    the offline-current receipt; its declared sha and length MUST match the
    stored object. Proves closure under the strict offline-current verify before
    writing the head-bound status. Does NOT publish a generation (the caller
    composes and publishes)."""
    store = pipeline.store
    store.initialize()
    # append-only family gate — the offline-current kind MUST NOT bypass it.
    feed_factory._validate_source_candidate(
        pipeline.project_root, pipeline.config, source,
    )
    if not isinstance(cache_bytes, (bytes, bytearray)):
        raise CanonicalDataError(
            "offline-current cache bytes must be raw bytes for %s"
            % source["source_id"]
        )
    cache_bytes = bytes(cache_bytes)
    computed_sha = hashlib.sha256(cache_bytes).hexdigest()
    # the cache manifest MUST attest the exact bytes we are about to bind.
    if (
        cache_manifest.get("source_sha256") != computed_sha or
        cache_manifest.get("source_bytes_length") != len(cache_bytes)
    ):
        raise CanonicalDataError(
            "offline-current cache manifest does not match the cache bytes "
            "for %s" % source["source_id"]
        )
    source_digest, _ = store.store_source_object(cache_bytes)
    # normalize through the live adapter's parser (no network) and add the exact
    # per-record binding provenance the store closure checks.
    records = normalize(source, cache_bytes, retrieved_at)
    for record in records:
        record["retrieved_at"] = retrieved_at
        record["source_bytes_sha256"] = source_digest
        record["validated_at"] = retrieved_at
        record["vintage_id"] = source_digest
    parser_id = "rmv2-live/%s" % source["adapter"]
    normalized = {
        "parser_id": parser_id,
        "records": records,
        "retrieved_at": retrieved_at,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
    normalized_digest, _ = store.store_normalized(normalized)
    receipt = build_offline_current_receipt(
        source=source,
        source_bytes_sha256=source_digest,
        normalized_sha256=normalized_digest,
        cache_manifest=cache_manifest,
        parser_id=parser_id,
        retrieved_at=retrieved_at,
        predecessor_receipt_sha256=predecessor_receipt_sha256,
    )
    receipt_digest, _ = store.store_receipt(source["source_id"], receipt)
    latest_observation_period = max(
        (
            record["observation_period"]
            for record in records
            if record["observation_period"] is not None
        ),
        default=None,
    )
    head = {
        "adapter": source["adapter"],
        "etag": None,
        "latest_observation_period": latest_observation_period,
        "last_modified": None,
        "method_version": source["method_version"],
        "normalized_sha256": normalized_digest,
        "record_count": len(records),
        "receipt_sha256": receipt_digest,
        "retrieved_at": retrieved_at,
        "schema_version": "recession-monitor-v2.source-head.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
    store.write_source_head(source["source_id"], head)
    binding = source_binding_from_head(source["source_id"], head)
    # prove closure under the strict offline-current verify before status.
    store.verify_offline_current_source_binding(binding)
    store.write_source_status(source["source_id"], {
        "attempted_at": retrieved_at,
        "error": None,
        "last_success_at": retrieved_at,
        "outcome": "success",
        "receipt_sha256": receipt_digest,
        "schema_version": "recession-monitor-v2.source-status.v1",
        "source_id": source["source_id"],
    })
    landed_series = {}
    for record in records:
        landed_series[record["series_id"]] = landed_series.get(
            record["series_id"], 0) + 1
    return {
        "acquisition_kind": OFFLINE_CURRENT_ACQUISITION_KIND,
        "landed_series": landed_series,
        "latest_observation_period": latest_observation_period,
        "normalized_sha256": normalized_digest,
        "outcome": "bound_offline_current",
        "receipt_sha256": receipt_digest,
        "record_count": len(records),
        "source_bytes_length": len(cache_bytes),
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }


def bind_offline_vintage(
    pipeline, source, csv_paths, as_of, predecessor_receipt_sha256=None,
    transcoder=vct,
):
    """Bind one deep-vintage base's on-disk CSVs as a store source head.

    ZERO network: never references ``pipeline.http_client``. Reuses the proven
    append-only family gate, the proven CSV->output_type=2 transcoder, and the
    proven deep parser. Writes the source object, the normalized object, the
    offline receipt, the source head, and a success status; proves the binding
    closes under the strict offline verify before writing the head-bound status.
    Does NOT publish a generation (the caller composes and publishes).
    """
    store = pipeline.store
    store.initialize()
    # append-only family gate — the offline kind MUST NOT bypass it. Raises on
    # collision (an already-active source_id, or a same-lane family prefix).
    feed_factory._validate_source_candidate(
        pipeline.project_root, pipeline.config, source,
    )
    # transport: on-disk CSV vintages -> the exact FRED output_type=2 body. The
    # transcoder is pluggable (ALFRED long-CSV by default; the FRED-MD panel
    # transcoder for B-LAND-3C-R2) but MUST emit the identical output_type=2
    # shape the deep parser accepts.
    body, file_provenance = transcoder.transcode_base(csv_paths, source=source)
    body_bytes = transcoder.body_bytes(body)
    response_schema_sha256 = transcoder.response_schema_sha256(body)
    source_digest, _ = store.store_source_object(body_bytes)
    # normalize through the proven deep parser (no network) and add the exact
    # per-record binding provenance the store closure checks.
    records = normalize(source, body_bytes, as_of)
    for record in records:
        record["retrieved_at"] = as_of
        record["source_bytes_sha256"] = source_digest
        record["validated_at"] = as_of
        record["vintage_id"] = source_digest
    normalized = {
        "parser_id": "rmv2-live/%s" % source["adapter"],
        "records": records,
        "retrieved_at": as_of,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
    normalized_digest, _ = store.store_normalized(normalized)
    receipt = build_offline_receipt(
        source=source,
        source_bytes_sha256=source_digest,
        normalized_sha256=normalized_digest,
        file_provenance=file_provenance,
        response_schema_sha256=response_schema_sha256,
        source_bytes_length=len(body_bytes),
        as_of=as_of,
        predecessor_receipt_sha256=predecessor_receipt_sha256,
        transcoder_parser_version=transcoder.TRANSCODER_PARSER_VERSION,
    )
    receipt_digest, _ = store.store_receipt(source["source_id"], receipt)
    latest_observation_period = max(
        (
            record["observation_period"]
            for record in records
            if record["observation_period"] is not None
        ),
        default=None,
    )
    head = {
        "adapter": source["adapter"],
        "etag": None,
        "latest_observation_period": latest_observation_period,
        "last_modified": None,
        "method_version": source["method_version"],
        "normalized_sha256": normalized_digest,
        "record_count": len(records),
        "receipt_sha256": receipt_digest,
        "retrieved_at": as_of,
        "schema_version": "recession-monitor-v2.source-head.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
    store.write_source_head(source["source_id"], head)
    binding = source_binding_from_head(source["source_id"], head)
    # prove closure under the strict offline verify (full raw->normalized->
    # receipt->binding chain plus the offline-kind guard) before status.
    store.verify_offline_source_binding(binding)
    store.write_source_status(source["source_id"], {
        "attempted_at": as_of,
        "error": None,
        "last_success_at": as_of,
        "outcome": "success",
        "receipt_sha256": receipt_digest,
        "schema_version": "recession-monitor-v2.source-status.v1",
        "source_id": source["source_id"],
    })
    landed_series = {}
    for record in records:
        landed_series[record["series_id"]] = landed_series.get(
            record["series_id"], 0) + 1
    return {
        "acquisition_kind": OFFLINE_ACQUISITION_KIND,
        "files_bound": len(file_provenance),
        "landed_series": landed_series,
        "latest_observation_period": latest_observation_period,
        "normalized_sha256": normalized_digest,
        "outcome": "bound_offline",
        "receipt_sha256": receipt_digest,
        "record_count": len(records),
        "source_bytes_length": len(body_bytes),
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
