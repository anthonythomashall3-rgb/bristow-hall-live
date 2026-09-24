"""B-PROD-1 — many producers, one committer.

The store is content-addressed: identical bytes hash to an identical object, so
object PRODUCTION parallelizes safely — two producers can never corrupt each
other's work because a collision means byte-identical content. Everything racy
— the generation pointer, the receipt chain, sources.v1.json, verify — is
touched by exactly ONE writer, the committer, serially under the existing
refresh + writer locks. Producers make bytes; the committer makes truth.

This module is the two halves:

  * ``produce`` — the parallel half. Deterministic fetch of one source's bytes
    into its OWN exclusive staging dir (``live_data/staging/<producer_id>/``):
    the fetched payload stored as ``<sha256>.bin`` plus a ``draft.v1.json``
    manifest. NO store write, NO config write, NO receipt-chain write, NO
    pointer touch — enforced, not promised (a test asserts the produce source
    imports no store-mutation entry point, and that two producers leave the
    store + config byte-identical).

  * ``commit_staged`` — the serial half. Scans ``staging/*/draft.v1.json`` in
    deterministic order, re-hashes each payload against its manifest (byte
    truth), runs the proven append-only family/shape gate, and admits via the
    proven binding path with an ADDITIVE ``live_http_staged`` acquisition
    receipt that carries the REAL http request/response block plus producer_id
    and the true fetch timestamp. Receipts chain serially; a per-draft failure
    is filed under ``rejected/<reason>/`` and the commit continues (nothing
    silent). Content-addressed re-admit of an already-landed head is a no-op,
    so a crash mid-commit is idempotent on re-run. The caller composes and
    publishes ONE generation after commit returns (verify runs there).

Contract: no AI. ``produce`` never references a store-mutation API; only the
committer writes the store, receipts, or config.
"""
from __future__ import absolute_import

from pathlib import Path

from .adapters import normalize
from .canonical import (
    CanonicalDataError,
    atomic_write_json,
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)

PRODUCE_DRAFT_SCHEMA = "recession-monitor-v2.produce-draft.v1"
STAGED_ACQUISITION_KIND = "live_http_staged"
STAGED_ACQUISITION_RECEIPT_SCHEMA = (
    "recession-monitor-v2.staged-acquisition-receipt.v1"
)
DRAFT_FILENAME = "draft.v1.json"


class StagedReject(Exception):
    """A staged draft failed a commit gate; file it and continue (§19.4)."""

    def __init__(self, reason):
        super(StagedReject, self).__init__(reason)
        self.reason = reason


def _compact(stamp):
    """A filesystem-safe compaction of an ISO-8601 UTC stamp."""
    return "".join(c for c in str(stamp) if c.isalnum())


def producer_id(source_id, attempted_at, split=None):
    """``<source>[_<split>]_<utc-stamp>`` — one exclusive dir per producer run."""
    split_part = ("_" + str(split)) if split else ""
    return "%s%s_%s" % (source_id, split_part, _compact(attempted_at))


def _parse_timestamp(value):
    # produce is transport-only; the http client accepts a naive ``now`` used
    # solely for conditional-fetch bookkeeping. We hand it the string stamp and
    # let the client decide — the seams the offline path used take ``now=None``.
    return None


def produce(http_client, source, attempted_at, staging_root, split=None):
    """Fetch one source's bytes into an exclusive producer dir. NO store write.

    Writes only inside ``staging_root/<producer_id>/``: the fetched payload as
    ``<sha256>.bin`` and a ``draft.v1.json`` manifest recording the source spec,
    the payload sha, the real fetch timestamp, the adapter shape id, the
    reservation ids, and the true http request/response metadata. Never touches
    the store, config, receipts, or the pointer.
    """
    pid = producer_id(source["source_id"], attempted_at, split=split)
    pdir = Path(staging_root) / pid
    # exclusive: a collision on the same (source, split, stamp) is a hard error,
    # never a silent overwrite of another run's bytes.
    pdir.mkdir(parents=True, exist_ok=False)
    response = http_client.fetch(
        source, now=_parse_timestamp(attempted_at), conditional_headers={})
    body = response.body
    digest = sha256_bytes(body)
    (pdir / (digest + ".bin")).write_bytes(body)
    draft = {
        "adapter": source["adapter"],
        "fetched_at": attempted_at,
        "http": {
            "request": {
                "body_sha256": response.request_body_sha256,
                "conditional_headers": response.request_headers,
                "method": response.request_method,
                "parameters": response.request_parameters,
                "url": response.url,
            },
            "response": {
                "content_length": len(body),
                "content_type": response.headers.get("content-type"),
                "etag": response.headers.get("etag"),
                "last_modified": response.headers.get("last-modified"),
                "status": response.status,
            },
        },
        "method_version": source["method_version"],
        "payload": {"byte_length": len(body), "sha256": digest},
        "producer_id": pid,
        "reservation_ids": sorted(source.get("coverage_source_ids") or []),
        "schema_version": PRODUCE_DRAFT_SCHEMA,
        "source": source,
        "source_id": source["source_id"],
    }
    atomic_write_json(pdir / DRAFT_FILENAME, draft)
    return draft


def scan_drafts(staging_root):
    """Live drafts in deterministic (producer_id, draft filename) order.

    Only top-level ``<producer_id>/draft.v1.json`` files are live; committed and
    rejected drafts live under ``committed/`` / ``rejected/`` subdirs and are
    never re-scanned.
    """
    staging_root = Path(staging_root)
    if not staging_root.exists():
        return []
    found = []
    for pdir in sorted(p for p in staging_root.iterdir() if p.is_dir()):
        draft_path = pdir / DRAFT_FILENAME
        if draft_path.is_file():
            found.append((pdir.name, draft_path))
    return sorted(found, key=lambda item: (item[0], item[1].name))


def build_staged_receipt(source, draft, source_bytes_sha256, normalized_sha256,
                         predecessor_receipt_sha256):
    """The staged live_http acquisition receipt (§3).

    An otherwise-v1 http receipt PLUS producer_id + the explicit kind. The http
    request/response block is the REAL metadata the producer recorded; the
    clocks carry the true fetch timestamp. Nothing is fabricated.
    """
    fetched_at = draft["fetched_at"]
    response = dict(draft["http"]["response"])
    return {
        "acquisition_kind": STAGED_ACQUISITION_KIND,
        "clocks": {
            "provider_available_at": fetched_at,
            "publisher_released_at": None,
            "retrieved_at": fetched_at,
            "validated_at": fetched_at,
        },
        "information_set_mode": source["information_set_mode"],
        "normalized_sha256": normalized_sha256,
        "outcome": "retrieved_and_validated",
        "predecessor_receipt_sha256": predecessor_receipt_sha256,
        "producer_id": draft["producer_id"],
        "publisher": source["publisher"],
        "request": dict(draft["http"]["request"]),
        "response": response,
        "rights_status": source["rights_status"],
        "schema_version": STAGED_ACQUISITION_RECEIPT_SCHEMA,
        "source_bytes_sha256": source_bytes_sha256,
        "source_id": source["source_id"],
    }


def _require_staged_receipt_fields(receipt):
    """A local guard that the staged receipt carries the two additive fields the
    store closure demands: producer_id and the fetch timestamp. Raises so a
    committer never stores an un-attributed staged receipt."""
    producer = receipt.get("producer_id")
    if not isinstance(producer, str) or not producer:
        raise CanonicalDataError("staged receipt is missing producer_id")
    if receipt.get("acquisition_kind") != STAGED_ACQUISITION_KIND:
        raise CanonicalDataError("staged receipt kind is wrong")
    clocks = receipt.get("clocks")
    if (
        not isinstance(clocks, dict) or
        not isinstance(clocks.get("retrieved_at"), str) or
        not clocks["retrieved_at"]
    ):
        raise CanonicalDataError("staged receipt is missing the fetch timestamp")
    return None


def bind_staged(pipeline, source, body_bytes, draft,
                predecessor_receipt_sha256=None):
    """Admit one produced source's bytes as a store source head with a staged
    receipt. The committer's per-draft unit. Idempotent: if the head already
    binds these exact bytes under the same parser identity, this is a no-op
    (content-addressed re-admit), so a crash between admit and the committed/
    move re-runs cleanly. Raises StagedReject on a gate failure.
    """
    from . import feed_factory
    from .store import source_binding_from_head, verify_source_binding

    store = pipeline.store
    store.initialize()
    source_id = source["source_id"]
    fetched_at = draft["fetched_at"]
    source_digest = sha256_bytes(body_bytes)

    prior = store.read_source_head(source_id)
    if (
        prior is not None and
        prior.get("source_bytes_sha256") == source_digest and
        prior.get("adapter") == source["adapter"] and
        prior.get("method_version") == source["method_version"]
    ):
        return {
            "outcome": "unchanged",
            "predecessor_receipt_sha256": predecessor_receipt_sha256,
            "producer_id": draft["producer_id"],
            "receipt_sha256": prior["receipt_sha256"],
            "record_count": prior["record_count"],
            "source": source,
            "source_id": source_id,
        }

    # append-only family/shape gate — the staged kind MUST NOT bypass it. Raises
    # on an already-active id, a series collision, an unonboardable adapter
    # shape, or an AI endpoint token.
    try:
        feed_factory._validate_source_candidate(
            pipeline.project_root, pipeline.config, source)
        # byte truth: normalize the produced bytes through the proven parser.
        records = normalize(source, body_bytes, fetched_at)
    except (CanonicalDataError, ValueError) as exc:
        raise StagedReject("gate: %s" % exc)

    store.store_source_object(body_bytes)
    for record in records:
        record["provenance_url"] = draft["http"]["request"]["url"]
        record["retrieved_at"] = fetched_at
        record["source_bytes_sha256"] = source_digest
        record["validated_at"] = fetched_at
        record["vintage_id"] = source_digest
    normalized = {
        "parser_id": "rmv2-live/%s" % source["adapter"],
        "records": records,
        "retrieved_at": fetched_at,
        "schema_version": "recession-monitor-v2.normalized-source.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    normalized_digest, _ = store.store_normalized(normalized)
    receipt = build_staged_receipt(
        source, draft, source_digest, normalized_digest,
        predecessor_receipt_sha256)
    _require_staged_receipt_fields(receipt)
    receipt_digest, _ = store.store_receipt(source_id, receipt)
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
        "etag": draft["http"]["response"]["etag"],
        "latest_observation_period": latest_observation_period,
        "last_modified": draft["http"]["response"]["last_modified"],
        "method_version": source["method_version"],
        "normalized_sha256": normalized_digest,
        "record_count": len(records),
        "receipt_sha256": receipt_digest,
        "retrieved_at": fetched_at,
        "schema_version": "recession-monitor-v2.source-head.v1",
        "source_bytes_sha256": source_digest,
        "source_id": source_id,
    }
    store.write_source_head(source_id, head)
    binding = source_binding_from_head(source_id, head)
    # prove closure under the staged branch of the strict verify before status.
    verify_source_binding(store.root, binding)
    store.write_source_status(source_id, {
        "attempted_at": fetched_at,
        "error": None,
        "last_success_at": fetched_at,
        "outcome": "success",
        "receipt_sha256": receipt_digest,
        "schema_version": "recession-monitor-v2.source-status.v1",
        "source_id": source_id,
    })
    return {
        "outcome": "committed",
        "predecessor_receipt_sha256": predecessor_receipt_sha256,
        "producer_id": draft["producer_id"],
        "receipt_sha256": receipt_digest,
        "record_count": len(records),
        "source": source,
        "source_id": source_id,
    }


def _file_draft(pdir, draft_path, disposition, reason=None):
    """Move a scanned draft + its payload out of the live scan set."""
    draft = strict_json_loads(draft_path.read_bytes())
    payload_name = draft["payload"]["sha256"] + ".bin"
    if disposition == "committed":
        dest = pdir / "committed"
    else:
        safe = "".join(c if c.isalnum() else "_" for c in (reason or "reject"))
        dest = pdir / "rejected" / safe[:64]
    dest.mkdir(parents=True, exist_ok=True)
    (dest / DRAFT_FILENAME).write_bytes(draft_path.read_bytes())
    payload = pdir / payload_name
    if payload.exists():
        (dest / payload_name).write_bytes(payload.read_bytes())
        payload.unlink()
    draft_path.unlink()


def commit_staged(pipeline, staging_root, as_of, predecessor_receipt_sha256=None):
    """Scan staged drafts in deterministic order and admit each serially.

    Returns one result per draft. A per-draft failure is filed under
    ``rejected/<reason>/`` and does NOT stop the commit; committed drafts move to
    ``committed/``. Receipts chain serially in commit order. The caller holds the
    refresh + writer locks and publishes ONE generation after this returns.
    """
    staging_root = Path(staging_root)
    results = []
    prev_receipt = predecessor_receipt_sha256
    for pid, draft_path in scan_drafts(staging_root):
        pdir = draft_path.parent
        reject_source_id = None
        try:
            draft = strict_json_loads(draft_path.read_bytes())
            if draft.get("schema_version") != PRODUCE_DRAFT_SCHEMA:
                raise StagedReject("schema: draft schema_version is wrong")
            reject_source_id = draft.get("source_id")
            source = draft["source"]
            payload = pdir / (draft["payload"]["sha256"] + ".bin")
            if not payload.is_file():
                raise StagedReject("payload: staged payload is missing")
            body = payload.read_bytes()
            if sha256_bytes(body) != draft["payload"]["sha256"]:
                raise StagedReject("sha_mismatch: payload bytes do not match manifest")
            outcome = bind_staged(pipeline, source, body, draft, prev_receipt)
        except StagedReject as exc:
            _file_draft(pdir, draft_path, "rejected", exc.reason)
            results.append({
                "outcome": "rejected",
                "producer_id": pid,
                "reason": exc.reason,
                "source_id": reject_source_id,
            })
            continue
        if outcome["outcome"] == "committed":
            prev_receipt = outcome["receipt_sha256"]
        _file_draft(pdir, draft_path, "committed")
        results.append(outcome)
    return results
