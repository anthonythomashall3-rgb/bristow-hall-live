"""B-LAND-2 §1 — the offline-admission acquisition kind (transport + provenance).

The ONLY store-write path for source objects, pipeline._refresh_source, obtains
its bytes from a live HTTPS fetch (PublisherHttpClient.fetch). The audited
on-disk ALFRED vintage corpora cannot reach the store that way without either
re-fetching today's FRED bytes (wrong bytes/provenance, cannot reach the
pre-1997 ALFRED floor) or fabricating an http receipt. This module is the
honest alternative: a NON-network transport that transcodes the on-disk CSV
vintages into the exact FRED output_type=2 body the proven deep parser already
admits, stores THAT body as the content-addressed store object, and records a
TRUTHFUL, DISTINCT offline provenance record beside it.

Provenance carried (§1.1): per-file on-disk CSV path + sha256 · the transcoder
id/parser_version · the emitted response_schema sha256 · an as-of stamp · the
information-set mode archive_snapshot_asof. No fabricated HTTP receipt, no
synthetic URL, no fake fetch timestamp.

MEASURED WALL (§1, filed as a DECISION blocker): binding the landed object into
a published generation requires store.verify_source_binding's CLOSED
acquisition-receipt.v1 schema (an exact key set with mandatory http
request/response blocks, re-checked by `verify --full`). A truthful offline
receipt has no field there, so binding would demand either a null/synthetic
http receipt (a §1.1 FABRICATION-class defect) or a change to the verify
closure (§3 forbids weakening verify). Both are owner adjudications. This
module therefore stops at honest transport + provenance and does NOT bind a
source head / receipt — that remainder is queued, not silently skipped.

Contract: no network (the http client seam is never referenced), no AI,
deterministic. Source CSV bytes are read, never written.
"""
from __future__ import absolute_import

from . import feed_factory
from . import vintage_csv_transcoder as vct
from .adapters import normalize

OFFLINE_ACQUISITION_KIND = "offline_vintage_admission"
OFFLINE_PROVENANCE_SCHEMA = "recession-monitor-v2.offline-admission-provenance.v1"

_SHA256_HEX_LEN = 64
_PROVENANCE_FIELDS = frozenset((
    "acquisition_kind",
    "as_of",
    "information_set_mode",
    "record_count",
    "response_schema_sha256",
    "schema_version",
    "source_bytes_sha256",
    "source_files",
    "source_id",
    "transcoder_parser_version",
))
_SOURCE_FILE_FIELDS = frozenset((
    "base", "row_count", "source_path", "source_sha256", "vintage",
))


class OfflineProvenanceError(ValueError):
    """The offline provenance record was not truthful/complete; refuse."""


def _is_sha256(value):
    return (
        isinstance(value, str) and
        len(value) == _SHA256_HEX_LEN and
        all(c in "0123456789abcdef" for c in value)
    )


def validate_offline_provenance(record):
    """Refuse any provenance record missing a per-file source sha, the
    transcoder version, the emitted response-schema sha, or its source files —
    a silent gap would let an un-attributed landing masquerade as audited."""
    if not isinstance(record, dict) or frozenset(record) != _PROVENANCE_FIELDS:
        raise OfflineProvenanceError("offline provenance key set is not exact")
    if record["acquisition_kind"] != OFFLINE_ACQUISITION_KIND:
        raise OfflineProvenanceError("offline provenance acquisition_kind is wrong")
    if record["schema_version"] != OFFLINE_PROVENANCE_SCHEMA:
        raise OfflineProvenanceError("offline provenance schema_version is wrong")
    version = record["transcoder_parser_version"]
    if not isinstance(version, str) or not version:
        raise OfflineProvenanceError("offline provenance transcoder version is absent")
    if not _is_sha256(record["response_schema_sha256"]):
        raise OfflineProvenanceError("offline provenance response_schema sha is invalid")
    if not _is_sha256(record["source_bytes_sha256"]):
        raise OfflineProvenanceError("offline provenance source_bytes sha is invalid")
    if not isinstance(record["as_of"], str) or not record["as_of"]:
        raise OfflineProvenanceError("offline provenance as_of stamp is absent")
    if record["information_set_mode"] != "archive_snapshot_asof":
        raise OfflineProvenanceError("offline provenance mode is not archive_snapshot_asof")
    if not isinstance(record["record_count"], int) or record["record_count"] < 0:
        raise OfflineProvenanceError("offline provenance record_count is invalid")
    files = record["source_files"]
    if not isinstance(files, list) or not files:
        raise OfflineProvenanceError("offline provenance has no source files")
    for entry in files:
        if not isinstance(entry, dict) or frozenset(entry) != _SOURCE_FILE_FIELDS:
            raise OfflineProvenanceError("offline provenance file entry is not exact")
        if not _is_sha256(entry["source_sha256"]):
            raise OfflineProvenanceError("offline provenance file is missing its sha")
        if not isinstance(entry["source_path"], str) or not entry["source_path"]:
            raise OfflineProvenanceError("offline provenance file path is absent")
        if not isinstance(entry["row_count"], int) or entry["row_count"] < 0:
            raise OfflineProvenanceError("offline provenance file row_count is invalid")
    return None


def build_offline_provenance(
    source, source_bytes_sha256, file_provenance, response_schema_sha256,
    attempted_at, record_count,
):
    return {
        "acquisition_kind": OFFLINE_ACQUISITION_KIND,
        "as_of": attempted_at,
        "information_set_mode": source["information_set_mode"],
        "record_count": record_count,
        "response_schema_sha256": response_schema_sha256,
        "schema_version": OFFLINE_PROVENANCE_SCHEMA,
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
        "transcoder_parser_version": vct.TRANSCODER_PARSER_VERSION,
    }


def admit_offline_vintage(pipeline, source, csv_paths, attempted_at):
    """Land one deep-vintage base's on-disk CSVs into the store as the source
    object, with a truthful offline provenance record. ZERO network: this
    function never references pipeline.http_client. Reuses the append-only
    family gate and the proven deep parser; does NOT bind (the wall)."""
    store = pipeline.store
    store.initialize()
    # (d) append-only family gate — the new kind MUST NOT bypass it. This is the
    # identical validation the online onboarding runs; it raises on collision.
    feed_factory._validate_source_candidate(
        pipeline.project_root, pipeline.config, source,
    )
    # transport: on-disk CSV vintages -> the exact FRED output_type=2 body.
    body, file_provenance = vct.transcode_base(csv_paths)
    body_bytes = vct.body_bytes(body)
    response_schema_sha256 = vct.response_schema_sha256(body)
    # the transcoder output body IS the content-addressed store object.
    source_digest, _ = store.store_source_object(body_bytes)
    # round-trip through the proven deep parser (no network): the count is the
    # measured landed-observation total for the in-window vintages.
    records = normalize(source, body_bytes, attempted_at)
    provenance = build_offline_provenance(
        source, source_digest, file_provenance, response_schema_sha256,
        attempted_at, len(records),
    )
    validate_offline_provenance(provenance)
    provenance_digest, provenance_path = store.store_offline_provenance(
        source["source_id"], provenance,
    )
    landed_series = {}
    for record in records:
        landed_series[record["series_id"]] = landed_series.get(
            record["series_id"], 0) + 1
    return {
        "acquisition_kind": OFFLINE_ACQUISITION_KIND,
        "landed_series": landed_series,
        "outcome": "admitted_offline",
        "provenance_path": str(provenance_path),
        "provenance_sha256": provenance_digest,
        "record_count": len(records),
        "source_bytes_sha256": source_digest,
        "source_id": source["source_id"],
    }
