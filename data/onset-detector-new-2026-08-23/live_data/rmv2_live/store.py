"""Content-addressed source store, append-only receipts, and atomic pointers."""

from __future__ import absolute_import

import fcntl
import os
import re
import secrets
import shutil
import stat
import warnings
from contextlib import contextmanager
from pathlib import Path

from .canonical import (
    CanonicalDataError,
    atomic_write,
    atomic_write_json,
    canonical_json_bytes,
    read_json,
    sha256_bytes,
    strict_json_loads,
    utc_now,
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
SNAPSHOT_PROJECTION_SCHEMA = "recession-monitor-v2.snapshot-projection.v1"
SNAPSHOT_PROJECTION_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
BINDING_ATTESTATION_SCHEMA = "recession-monitor-v2.binding-attestation.v1"
BINDING_ATTESTATION_VERSION = "v1"
BINDING_ATTESTATION_FIELDS = frozenset((
    "etag",
    "last_modified",
    "latest_observation_period",
    "normalized_sha256",
    "parser_id",
    "receipt_sha256",
    "record_count",
    "schema_version",
    "source_bytes_sha256",
    "source_id",
))
GENERATION_MEMBERS = (
    "coverage.json",
    "snapshot.json",
    "status.json",
)
SOURCE_BINDING_FIELDS = frozenset((
    "latest_observation_period",
    "normalized_sha256",
    "receipt_sha256",
    "record_count",
    "retrieved_at",
    "source_bytes_sha256",
    "source_id",
))
SOURCE_HEAD_FIELDS = frozenset(tuple(SOURCE_BINDING_FIELDS) + (
    "adapter",
    "etag",
    "last_modified",
    "method_version",
    "schema_version",
))
ACQUISITION_RECEIPT_FIELDS = frozenset((
    "clocks",
    "information_set_mode",
    "normalized_sha256",
    "outcome",
    "predecessor_receipt_sha256",
    "publisher",
    "request",
    "response",
    "rights_status",
    "schema_version",
    "source_bytes_sha256",
    "source_id",
))
ACQUISITION_RECEIPT_SCHEMA = "recession-monitor-v2.acquisition-receipt.v1"
# B-LAND-3 §1 — the additive OFFLINE acquisition-receipt variant. The kind is
# discriminated by schema_version (a v1 receipt is unchanged and implicitly
# live_http); an offline receipt carries the transcode provenance IN the receipt
# (the single §24 home) and has NO http request/response block — present = FAIL.
OFFLINE_ACQUISITION_RECEIPT_SCHEMA = (
    "recession-monitor-v2.offline-acquisition-receipt.v1"
)
OFFLINE_ACQUISITION_KIND = "offline_vintage_admission"
OFFLINE_ACQUISITION_RECEIPT_FIELDS = frozenset((
    "acquisition_kind",
    "as_of",
    "clocks",
    "information_set_mode",
    "normalized_sha256",
    "outcome",
    "predecessor_receipt_sha256",
    "publisher",
    "rights_status",
    "schema_version",
    "source_bytes_sha256",
    "source_files",
    "source_id",
    "transcoder",
))
OFFLINE_RECEIPT_TRANSCODER_FIELDS = frozenset((
    "parser_version",
    "response_schema_sha256",
    "source_bytes_length",
))
OFFLINE_RECEIPT_SOURCE_FILE_FIELDS = frozenset((
    "base",
    "row_count",
    "source_path",
    "source_sha256",
    "vintage",
))
# B-PROD-1 §3 — the additive STAGED live_http acquisition-receipt variant. A
# producer fetched REAL bytes into an exclusive staging dir; the committer admits
# them and stamps WHO produced them (producer_id) + the explicit kind. The http
# request/response block is real (nothing fabricated); the variant only adds
# producer_id + acquisition_kind to the v1 closed schema and is discriminated by
# schema_version exactly like the B-LAND-3 offline variant. Any other schema
# still falls through to the v1 branch and fails, as before.
STAGED_ACQUISITION_RECEIPT_SCHEMA = (
    "recession-monitor-v2.staged-acquisition-receipt.v1"
)
STAGED_ACQUISITION_KIND = "live_http_staged"
STAGED_ACQUISITION_RECEIPT_FIELDS = frozenset(
    tuple(ACQUISITION_RECEIPT_FIELDS) + ("acquisition_kind", "producer_id")
)
# B-OFFLINE-2 §1 — the additive OFFLINE-CURRENT acquisition-receipt variant. A
# generic (non-FRED-transcoder) offline bind admits adapter-normalized bytes that
# were captured to a sha-manifested prefetch cache (url + fetch UTC + sha256), for
# a NON-vintage lane (current_revised and the other information-set modes). Unlike
# the offline_vintage variant it carries NO per-file `vintage`/`base` list and NO
# transcoder identity (the cache bytes ARE the source object, byte-unchanged); it
# instead cites the cache manifest as the acquisition provenance and records the
# parser_id that normalized those bytes. Like the two prior variants it is
# discriminated purely by schema_version — any other schema still falls through to
# the v1 branch and fails, and the existing offline_vintage closure is untouched.
OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA = (
    "recession-monitor-v2.offline-current-acquisition-receipt.v1"
)
OFFLINE_CURRENT_ACQUISITION_KIND = "offline_current_cache"
OFFLINE_CURRENT_ACQUISITION_RECEIPT_FIELDS = frozenset((
    "acquisition_kind",
    "cache_manifest",
    "clocks",
    "information_set_mode",
    "normalized_sha256",
    "outcome",
    "parser_id",
    "predecessor_receipt_sha256",
    "publisher",
    "rights_status",
    "schema_version",
    "source_bytes_sha256",
    "source_id",
))
OFFLINE_CURRENT_RECEIPT_CACHE_MANIFEST_FIELDS = frozenset((
    "fetch_utc",
    "source_bytes_length",
    "source_sha256",
    "url",
))
NORMALIZED_SOURCE_FIELDS = frozenset((
    "parser_id",
    "records",
    "retrieved_at",
    "schema_version",
    "source_bytes_sha256",
    "source_id",
))
RECEIPT_CLOCK_FIELDS = frozenset((
    "provider_available_at",
    "publisher_released_at",
    "retrieved_at",
    "validated_at",
))
RECEIPT_REQUEST_FIELDS = frozenset((
    "body_sha256",
    "conditional_headers",
    "method",
    "parameters",
    "url",
))
RECEIPT_RESPONSE_FIELDS = frozenset((
    "content_length",
    "content_type",
    "etag",
    "last_modified",
    "status",
))


class LiveStore(object):
    def __init__(self, project_root, config):
        self.project_root = Path(project_root).resolve()
        self.root = (self.project_root / config["store"]["root"]).resolve()
        self.public = (self.project_root / config["store"]["public"]).resolve()
        self.runtime = (self.project_root / config["store"]["runtime"]).resolve()
        for path in (self.root, self.public, self.runtime):
            if self.project_root not in path.parents:
                raise CanonicalDataError("live-data path escaped the project root")
        paths = (self.root, self.public, self.runtime)
        for index, left in enumerate(paths):
            for right in paths[index + 1:]:
                if left == right or left in right.parents or right in left.parents:
                    raise CanonicalDataError("live-data roots must be pairwise disjoint")

    def initialize(self):
        paths = (
            self.root / "objects" / "sha256",
            self.root / "normalized" / "sha256",
            self.root / "receipts",
            self.root / "attempts",
            self.root / "generations",
            self.runtime / "atomic_bundles",
            self.runtime / "source_heads",
            self.runtime / "source_status",
            self.runtime / "logs",
            self.public,
        )
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def refresh_lock(self, label="live-data-refresh"):
        """Hold the one project-wide store writer barrier.

        Admission and autopilot have separate coordinator locks for at-most-once
        scheduling, but every store mutation serializes on this exact fd path.
        The holder sidecar makes direct live refreshes as observable as batch
        writers using :mod:`bh.writer_lock`.
        """
        if not isinstance(label, str) or not label:
            raise ValueError("writer lock label must be a non-empty string")
        self.initialize()
        path = self.runtime / "refresh.lock"
        holder_path = self.runtime / "refresh.lock.holder.json"
        descriptor = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(descriptor)
            raise RuntimeError("another live-data refresh is already running")
        try:
            atomic_write_json(holder_path, {
                "acquired_at": utc_now(),
                "label": label,
                "pid": os.getpid(),
            })
            yield
        finally:
            try:
                holder_path.unlink()
            except FileNotFoundError:
                holder_path = None
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _write_immutable(self, path, data):
        path = Path(path)
        if path.exists():
            existing = path.read_bytes()
            if existing != data:
                raise CanonicalDataError("immutable path collision: %s" % path)
            return
        atomic_write(path, data, mode=0o444)

    @staticmethod
    def _source_id(source_id):
        if not isinstance(source_id, str) or not SOURCE_ID_RE.match(source_id):
            raise CanonicalDataError("source_id is unsafe for storage")
        return source_id

    def store_source_object(self, data):
        digest = sha256_bytes(data)
        path = self.root / "objects" / "sha256" / digest[:2] / (digest + ".bin")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)
        return digest, path

    def store_normalized(self, value):
        data = canonical_json_bytes(value)
        digest = sha256_bytes(data)
        path = self.root / "normalized" / "sha256" / digest[:2] / (digest + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)
        return digest, path

    def store_receipt(self, source_id, receipt):
        source_id = self._source_id(source_id)
        data = canonical_json_bytes(receipt)
        digest = sha256_bytes(data)
        path = self.root / "receipts" / source_id / (digest + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)
        return digest, path

    def store_attempt(self, source_id, attempt):
        source_id = self._source_id(source_id)
        data = canonical_json_bytes(attempt)
        digest = sha256_bytes(data)
        path = self.root / "attempts" / source_id / (digest + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)
        return digest, path

    def store_offline_provenance(self, source_id, provenance):
        """Immutably store an offline-admission provenance record (B-LAND-2 §1).

        A content-addressed sidecar, parallel to store_receipt/store_attempt.
        It carries the TRUTHFUL non-http provenance for an offline vault landing
        (per-file source shas + transcoder parser_version + emitted response
        schema sha + as-of + information-set mode). It is deliberately NOT the
        acquisition-receipt.v1 the generation-binding closure consumes: an
        offline landing is not a fetch, so it never fabricates an http
        request/response. Binding this landing into a generation is the
        owner-adjudicated remainder (see the offline-admission DECISION blocker)
        and this method touches no verify closure."""
        source_id = self._source_id(source_id)
        data = canonical_json_bytes(provenance)
        digest = sha256_bytes(data)
        path = self.root / "offline_admissions" / source_id / (digest + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)
        return digest, path

    def write_source_head(self, source_id, head):
        source_id = self._source_id(source_id)
        atomic_write_json(self.runtime / "source_heads" / (source_id + ".json"), head)

    def write_source_status(self, source_id, status_value):
        source_id = self._source_id(source_id)
        atomic_write_json(self.runtime / "source_status" / (source_id + ".json"), status_value)

    def write_atomic_bundle(self, bundle_id, value):
        bundle_id = self._source_id(bundle_id)
        atomic_write_json(
            self.runtime / "atomic_bundles" / (bundle_id + ".json"),
            value,
        )

    def read_atomic_bundle(self, bundle_id):
        bundle_id = self._source_id(bundle_id)
        path = self.runtime / "atomic_bundles" / (bundle_id + ".json")
        return read_json(path) if path.exists() else None

    def read_source_head(self, source_id):
        source_id = self._source_id(source_id)
        path = self.runtime / "source_heads" / (source_id + ".json")
        return read_json(path) if path.exists() else None

    def read_source_status(self, source_id):
        source_id = self._source_id(source_id)
        path = self.runtime / "source_status" / (source_id + ".json")
        return read_json(path) if path.exists() else None

    def all_source_heads(self):
        result = {}
        directory = self.runtime / "source_heads"
        if not directory.exists():
            return result
        for path in sorted(directory.glob("*.json")):
            result[path.stem] = read_json(path)
        return result

    def all_source_statuses(self):
        result = {}
        directory = self.runtime / "source_status"
        if not directory.exists():
            return result
        for path in sorted(directory.glob("*.json")):
            result[path.stem] = read_json(path)
        return result

    def read_normalized(self, digest):
        path = self.root / "normalized" / "sha256" / digest[:2] / (digest + ".json")
        return read_json(path)

    def _snapshot_projection_path(self, materializer_version, digest):
        if not SHA256_RE.match(digest):
            raise CanonicalDataError("snapshot projection digest is unsafe")
        if not SNAPSHOT_PROJECTION_VERSION_RE.match(materializer_version):
            raise CanonicalDataError(
                "snapshot projection materializer version is unsafe"
            )
        return (
            self.root / "snapshot_projection" / materializer_version /
            "sha256" / digest[:2] / (digest + ".json")
        )

    def read_snapshot_projection(self, source_id, head, materializer_version):
        """Return the content-addressed per-source snapshot projection or None.

        A projection is a pure, deterministic function of the immutable
        normalized object (addressed by ``normalized_sha256``) under a fixed
        materializer version, so it is content-addressed and immutable.  The
        cache lets an incremental refresh skip re-reading and re-projecting the
        normalized records of sources whose evidence head is unchanged; the
        full raw->normalized->receipt closure is re-verified by ``verify
        --full``, never weakened here.  Byte-for-byte identical to the full
        rebuild: same binding, same latest-per-series projection, same count.
        """
        source_id = self._source_id(source_id)
        digest = head["normalized_sha256"]
        path = self._snapshot_projection_path(materializer_version, digest)
        if not path.exists():
            return None
        projection = read_json(path)
        if (
            not isinstance(projection, dict) or
            projection.get("schema_version") != SNAPSHOT_PROJECTION_SCHEMA or
            projection.get("materializer_version") != materializer_version or
            projection.get("normalized_sha256") != digest or
            projection.get("source_id") != source_id or
            projection.get("record_count") != head["record_count"] or
            not isinstance(projection.get("series"), dict) or
            not isinstance(projection.get("binding"), dict)
        ):
            raise CanonicalDataError(
                "snapshot projection cache is corrupt for %s" % source_id
            )
        return projection

    def write_snapshot_projection(
        self, source_id, head, materializer_version, projection
    ):
        source_id = self._source_id(source_id)
        digest = head["normalized_sha256"]
        record = {
            "binding": projection["binding"],
            "materializer_version": materializer_version,
            "normalized_sha256": digest,
            "record_count": projection["record_count"],
            "schema_version": SNAPSHOT_PROJECTION_SCHEMA,
            "series": projection["series"],
            "source_id": source_id,
        }
        data = canonical_json_bytes(record)
        path = self._snapshot_projection_path(materializer_version, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_immutable(path, data)

    def verify_source_binding(self, binding):
        return verify_source_binding(self.root, binding)

    def verify_offline_source_binding(self, binding):
        return verify_offline_source_binding(self.root, binding)

    def verify_offline_current_source_binding(self, binding):
        return verify_offline_current_source_binding(self.root, binding)

    def verify_source_head(self, source_id, head):
        return verify_source_head(self.root, source_id, head)

    def attest_source_binding(self, binding):
        return attest_source_binding(self.root, binding)

    def attest_source_head(self, source_id, head):
        return attest_source_head(self.root, source_id, head)

    def publish_generation(self, snapshot, status, coverage):
        snapshot_sources = snapshot.get("sources") if isinstance(snapshot, dict) else None
        if not isinstance(snapshot_sources, list):
            raise CanonicalDataError("snapshot source bindings are invalid")
        seen_source_ids = set()
        for binding in snapshot_sources:
            # Content-addressed attestation: verifies the immutable raw ->
            # normalized -> receipt -> binding closure on first sight of a
            # normalized digest and reuses it thereafter, so publishing a
            # generation is O(changed sources), not O(total normalized bytes).
            attestation = self.attest_source_binding(binding)
            if attestation["source_id"] in seen_source_ids:
                raise CanonicalDataError("snapshot source binding is duplicated")
            seen_source_ids.add(attestation["source_id"])
        member_bytes = {
            "coverage.json": canonical_json_bytes(coverage),
            "snapshot.json": canonical_json_bytes(snapshot),
            "status.json": canonical_json_bytes(status),
        }
        manifest = {
            "created_at": snapshot["generated_at"],
            "members": {
                name: {
                    "bytes": len(member_bytes[name]),
                    "sha256": sha256_bytes(member_bytes[name]),
                    "schema_version": strict_json_loads(member_bytes[name])[
                        "schema_version"
                    ],
                }
                for name in GENERATION_MEMBERS
            },
            "schema_version": "recession-monitor-v2.live-generation-manifest.v2",
            "source_head_receipt_sha256": {
                item["source_id"]: item["receipt_sha256"]
                for item in snapshot["sources"]
            },
        }
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_digest = sha256_bytes(manifest_bytes)
        generation_root = self.root / "generations" / manifest_digest
        if generation_root.exists():
            expected_names = set(GENERATION_MEMBERS) | {"manifest.json"}
            actual_names = {path.name for path in generation_root.iterdir()}
            if actual_names != expected_names:
                raise CanonicalDataError("immutable generation collision")
            for name, data in list(member_bytes.items()) + [
                ("manifest.json", manifest_bytes)
            ]:
                if (generation_root / name).read_bytes() != data:
                    raise CanonicalDataError("immutable generation collision")
        else:
            staging = generation_root.parent / (
                ".%s.%s.staging" % (manifest_digest, secrets.token_hex(8))
            )
            try:
                staging.mkdir(parents=True, exist_ok=False)
                for name in GENERATION_MEMBERS:
                    self._write_immutable(staging / name, member_bytes[name])
                self._write_immutable(staging / "manifest.json", manifest_bytes)
                os.replace(str(staging), str(generation_root))
                try:
                    directory_fd = os.open(str(generation_root.parent), os.O_RDONLY)
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
                except OSError as exc:
                    warnings.warn(
                        "generation directory fsync unavailable: %s" % exc,
                        RuntimeWarning,
                    )
            finally:
                if staging.exists():
                    shutil.rmtree(str(staging))

        current_path = self.public / "live_snapshot.json"
        prior_pointer_bytes = None
        pointer_path = self.public / "latest.pointer.json"
        if pointer_path.exists():
            prior_pointer_bytes = safe_regular_file(pointer_path, self.public)
        if current_path.exists():
            current = safe_regular_file(current_path, self.public)
            atomic_write(self.public / "live_snapshot.previous.json", current)
        atomic_write(self.public / "live_snapshot.json", member_bytes["snapshot.json"])
        atomic_write(self.public / "live_snapshot.lkg.json", member_bytes["snapshot.json"])
        atomic_write(self.public / "live_status.json", member_bytes["status.json"])
        atomic_write(self.public / "source_coverage.json", member_bytes["coverage.json"])
        pointer = {
            "coverage_sha256": manifest["members"]["coverage.json"]["sha256"],
            "generation_sha256": manifest_digest,
            "manifest_sha256": manifest_digest,
            "schema_version": "recession-monitor-v2.live-pointer.v2",
            "snapshot_sha256": manifest["members"]["snapshot.json"]["sha256"],
            "status_sha256": manifest["members"]["status.json"]["sha256"],
            "updated_at": snapshot["generated_at"],
        }
        pointer_bytes = canonical_json_bytes(pointer)
        if prior_pointer_bytes is not None:
            atomic_write(
                self.public / "latest.previous.pointer.json",
                prior_pointer_bytes,
            )
            atomic_write(
                self.public / "latest.rollback.pointer.json",
                prior_pointer_bytes,
            )
        atomic_write(self.public / "latest.lkg.pointer.json", pointer_bytes)
        # The pointer is the commit record and must be switched last.
        atomic_write(pointer_path, pointer_bytes)
        return pointer


def safe_regular_file(path, allowed_root):
    """Descriptor-read a regular file beneath a root without following links."""
    candidate = Path(path)
    allowed_root = Path(allowed_root).resolve()
    # Canonicalize the candidate's PARENT the same way the root is resolved, so a
    # non-canonical configured root (e.g. macOS /var/folders -> /private/var/
    # folders) does not raise a false "escaped its root" BEFORE the
    # not-a-regular-file check runs. The leaf name stays unresolved; the
    # O_NOFOLLOW walk below is the actual no-symlink-traversal enforcement
    # (B-RELO-TESTFIX §18.1 — test untouched).
    path = candidate.absolute().parent.resolve() / candidate.name
    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        raise CanonicalDataError("public file escaped its root")
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise CanonicalDataError("public path is invalid")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    # O_NONBLOCK is REQUIRED for the S_ISREG check below to be reachable at all.
    # POSIX open() of a FIFO for reading BLOCKS until a writer appears, so without
    # it a named pipe left at a public member path (hostile or an interrupted
    # producer) hangs this reader forever and the "not a regular file" rejection
    # never runs. O_NONBLOCK has no effect on reads of regular files, so nothing
    # on the intended path changes.
    nonblock = getattr(os, "O_NONBLOCK", 0)
    directory_fd = os.open(str(allowed_root), os.O_RDONLY | directory_flag)
    opened_directories = []
    descriptor = None
    try:
        current_fd = directory_fd
        for part in relative.parts[:-1]:
            child_fd = os.open(
                part,
                os.O_RDONLY | directory_flag | nofollow,
                dir_fd=current_fd,
            )
            opened_directories.append(child_fd)
            current_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | nofollow | nonblock,
            dir_fd=current_fd,
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise CanonicalDataError("public path is not a regular file")
        if info.st_nlink != 1:
            raise CanonicalDataError("hard-linked public file is prohibited")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (
            info.st_dev != after.st_dev or
            info.st_ino != after.st_ino or
            info.st_size != after.st_size or
            info.st_mtime_ns != after.st_mtime_ns
        ):
            raise CanonicalDataError("public file changed during read")
        return b"".join(chunks)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise CanonicalDataError("unsafe or unavailable public file") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for child_fd in reversed(opened_directories):
            os.close(child_fd)
        os.close(directory_fd)


def safe_regular_file_identity(path, allowed_root):
    """Return a cheap tamper fingerprint without following path links."""
    candidate = Path(path)
    allowed_root = Path(allowed_root).resolve()
    # See safe_regular_file: resolve the candidate's parent consistently with the
    # root so a non-canonical root does not fire "escaped its root" ahead of the
    # not-a-regular-file check (B-RELO-TESTFIX §18.1 — test untouched).
    path = candidate.absolute().parent.resolve() / candidate.name
    try:
        relative = path.relative_to(allowed_root)
    except ValueError:
        raise CanonicalDataError("identity file escaped its root")
    if not relative.parts or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        raise CanonicalDataError("identity path is invalid")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    # See safe_regular_file: without O_NONBLOCK a FIFO at this path blocks the
    # open() forever and the S_ISREG rejection below is unreachable.
    nonblock = getattr(os, "O_NONBLOCK", 0)
    directory_fd = os.open(str(allowed_root), os.O_RDONLY | directory_flag)
    opened_directories = []
    descriptor = None
    try:
        current_fd = directory_fd
        for part in relative.parts[:-1]:
            child_fd = os.open(
                part,
                os.O_RDONLY | directory_flag | nofollow,
                dir_fd=current_fd,
            )
            opened_directories.append(child_fd)
            current_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | nofollow | nonblock,
            dir_fd=current_fd,
        )
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise CanonicalDataError(
                "identity path is not a regular file"
            )
        if info.st_nlink != 1:
            raise CanonicalDataError(
                "hard-linked identity file is prohibited"
            )
        return {
            "device": info.st_dev,
            "gid": info.st_gid,
            "inode": info.st_ino,
            "mode": stat.S_IMODE(info.st_mode),
            "mtime_ns": info.st_mtime_ns,
            "size": info.st_size,
            "uid": info.st_uid,
        }
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise CanonicalDataError(
            "unsafe or unavailable identity file"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for child_fd in reversed(opened_directories):
            os.close(child_fd)
        os.close(directory_fd)


def generation_storage_fingerprint(
    public_root,
    generations_root,
    pointer,
    source_bindings,
):
    """Fingerprint every file authenticated by one cached generation."""
    public_root = Path(public_root).resolve()
    generations_root = Path(generations_root).resolve()
    if not isinstance(pointer, dict):
        raise CanonicalDataError("cached pointer is invalid")
    generation_id = pointer.get("generation_sha256")
    if (
        not isinstance(generation_id, str) or
        not SHA256_RE.match(generation_id)
    ):
        raise CanonicalDataError("cached generation identity is invalid")
    if not isinstance(source_bindings, list):
        raise CanonicalDataError("cached source bindings are invalid")
    generation_root = generations_root / generation_id
    store_root = generations_root.parent
    paths = [
        (
            "public/latest.pointer.json",
            public_root / "latest.pointer.json",
            public_root,
        ),
        (
            "generation/manifest.json",
            generation_root / "manifest.json",
            generations_root,
        ),
    ]
    for name in GENERATION_MEMBERS:
        paths.append((
            "generation/" + name,
            generation_root / name,
            generations_root,
        ))
    seen = set()
    for raw_binding in source_bindings:
        binding = validate_source_binding(raw_binding)
        source_id = binding["source_id"]
        if source_id in seen:
            raise CanonicalDataError(
                "cached source binding is duplicated"
            )
        seen.add(source_id)
        paths.extend((
            (
                "source/%s/raw" % source_id,
                (
                    store_root / "objects" / "sha256" /
                    binding["source_bytes_sha256"][:2] /
                    (binding["source_bytes_sha256"] + ".bin")
                ),
                store_root,
            ),
            (
                "source/%s/normalized" % source_id,
                (
                    store_root / "normalized" / "sha256" /
                    binding["normalized_sha256"][:2] /
                    (binding["normalized_sha256"] + ".json")
                ),
                store_root,
            ),
            (
                "source/%s/receipt" % source_id,
                (
                    store_root / "receipts" / source_id /
                    (binding["receipt_sha256"] + ".json")
                ),
                store_root,
            ),
        ))
    rows = [
        {
            "identity": safe_regular_file_identity(path, root),
            "name": name,
        }
        for name, path, root in paths
    ]
    rows.sort(key=lambda row: row["name"])
    return sha256_bytes(canonical_json_bytes({
        "files": rows,
        "schema_version": (
            "recession-monitor-v2.generation-storage-fingerprint.v1"
        ),
    }))


def source_binding_from_head(source_id, head):
    """Return the exact public source binding from one runtime source head."""
    if (
        not isinstance(source_id, str) or
        not SOURCE_ID_RE.match(source_id) or
        not isinstance(head, dict) or
        frozenset(head) != SOURCE_HEAD_FIELDS or
        head.get("schema_version") != "recession-monitor-v2.source-head.v1" or
        head.get("source_id") != source_id
    ):
        raise CanonicalDataError("runtime source head schema is invalid")
    for field in (
        "normalized_sha256",
        "receipt_sha256",
        "source_bytes_sha256",
    ):
        if (
            not isinstance(head.get(field), str) or
            not SHA256_RE.match(head[field])
        ):
            raise CanonicalDataError(
                "runtime source head digest is invalid: %s" % field
            )
    if (
        type(head.get("record_count")) is not int or
        head["record_count"] < 0 or
        not isinstance(head.get("retrieved_at"), str) or
        not head["retrieved_at"] or
        (
            head.get("latest_observation_period") is not None and
            not isinstance(head["latest_observation_period"], str)
        ) or
        not isinstance(head.get("adapter"), str) or
        not head["adapter"] or
        not isinstance(head.get("method_version"), str) or
        not head["method_version"] or
        (
            head.get("etag") is not None and
            not isinstance(head["etag"], str)
        ) or
        (
            head.get("last_modified") is not None and
            not isinstance(head["last_modified"], str)
        )
    ):
        raise CanonicalDataError("runtime source head metadata is invalid")
    return {
        field: head[field]
        for field in SOURCE_BINDING_FIELDS
    }


def validate_source_binding(binding):
    """Validate and copy the exact seven-field immutable source binding."""
    if (
        not isinstance(binding, dict) or
        frozenset(binding) != SOURCE_BINDING_FIELDS
    ):
        raise CanonicalDataError("source evidence binding schema is invalid")
    source_id = binding.get("source_id")
    if not isinstance(source_id, str) or not SOURCE_ID_RE.match(source_id):
        raise CanonicalDataError("source evidence binding identity is invalid")
    for field in (
        "normalized_sha256",
        "receipt_sha256",
        "source_bytes_sha256",
    ):
        if (
            not isinstance(binding.get(field), str) or
            not SHA256_RE.match(binding[field])
        ):
            raise CanonicalDataError(
                "source evidence binding digest is invalid: %s" % field
            )
    if (
        type(binding.get("record_count")) is not int or
        binding["record_count"] < 0 or
        not isinstance(binding.get("retrieved_at"), str) or
        not binding["retrieved_at"] or
        (
            binding.get("latest_observation_period") is not None and
            not isinstance(binding["latest_observation_period"], str)
        )
    ):
        raise CanonicalDataError("source evidence binding metadata is invalid")
    return {
        field: binding[field]
        for field in SOURCE_BINDING_FIELDS
    }


def verify_source_binding(store_root, binding):
    """Verify raw -> normalized -> receipt -> binding closure exactly once."""
    store_root = Path(store_root).resolve()
    binding = validate_source_binding(binding)
    source_id = binding["source_id"]
    paths = {
        "normalized": (
            store_root / "normalized" / "sha256" /
            binding["normalized_sha256"][:2] /
            (binding["normalized_sha256"] + ".json")
        ),
        "receipt": (
            store_root / "receipts" / source_id /
            (binding["receipt_sha256"] + ".json")
        ),
        "source_object": (
            store_root / "objects" / "sha256" /
            binding["source_bytes_sha256"][:2] /
            (binding["source_bytes_sha256"] + ".bin")
        ),
    }
    payloads = {}
    for kind, path in paths.items():
        try:
            data = safe_regular_file(path, store_root)
        except FileNotFoundError:
            raise CanonicalDataError(
                "source %s evidence is missing for %s" % (kind, source_id)
            )
        expected = {
            "normalized": binding["normalized_sha256"],
            "receipt": binding["receipt_sha256"],
            "source_object": binding["source_bytes_sha256"],
        }[kind]
        if sha256_bytes(data) != expected:
            raise CanonicalDataError(
                "source %s evidence hash mismatch for %s" % (kind, source_id)
            )
        payloads[kind] = data

    receipt = strict_json_loads(payloads["receipt"])
    normalized = strict_json_loads(payloads["normalized"])
    # B-LAND-3 §1 — additive kind dispatch: an offline receipt (a distinct
    # schema_version) verifies against the offline requirements below; a v1
    # live_http receipt verifies against EXACTLY the prior closed schema (the
    # condition is byte-for-byte the pre-B-LAND-3 check). Any other schema falls
    # through the v1 branch and fails, as before.
    receipt_schema = (
        receipt.get("schema_version") if isinstance(receipt, dict) else None
    )
    if receipt_schema == OFFLINE_ACQUISITION_RECEIPT_SCHEMA:
        _verify_offline_receipt(receipt, binding, source_id, payloads)
    elif receipt_schema == OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA:
        _verify_offline_current_receipt(receipt, binding, source_id, payloads)
    elif receipt_schema == STAGED_ACQUISITION_RECEIPT_SCHEMA:
        _verify_staged_receipt(receipt, binding, source_id, payloads)
    elif (
        canonical_json_bytes(receipt) != payloads["receipt"] or
        not isinstance(receipt, dict) or
        frozenset(receipt) != ACQUISITION_RECEIPT_FIELDS or
        receipt.get("schema_version") !=
        "recession-monitor-v2.acquisition-receipt.v1" or
        receipt.get("source_id") != source_id or
        receipt.get("source_bytes_sha256") !=
        binding["source_bytes_sha256"] or
        receipt.get("normalized_sha256") != binding["normalized_sha256"] or
        not isinstance(receipt.get("clocks"), dict) or
        frozenset(receipt["clocks"]) != RECEIPT_CLOCK_FIELDS or
        receipt["clocks"].get("retrieved_at") != binding["retrieved_at"] or
        receipt["clocks"].get("validated_at") != binding["retrieved_at"] or
        not isinstance(receipt.get("request"), dict) or
        frozenset(receipt["request"]) != RECEIPT_REQUEST_FIELDS or
        not isinstance(receipt.get("response"), dict) or
        frozenset(receipt["response"]) != RECEIPT_RESPONSE_FIELDS or
        receipt["response"].get("content_length") !=
        len(payloads["source_object"])
    ):
        raise CanonicalDataError("source receipt binding is invalid for %s" % source_id)
    if (
        canonical_json_bytes(normalized) != payloads["normalized"] or
        not isinstance(normalized, dict) or
        frozenset(normalized) != NORMALIZED_SOURCE_FIELDS or
        normalized.get("schema_version") !=
        "recession-monitor-v2.normalized-source.v1" or
        normalized.get("source_id") != source_id or
        normalized.get("source_bytes_sha256") !=
        binding["source_bytes_sha256"] or
        normalized.get("retrieved_at") != binding["retrieved_at"] or
        not isinstance(normalized.get("records"), list) or
        len(normalized["records"]) != binding["record_count"]
    ):
        raise CanonicalDataError(
            "normalized source binding is invalid for %s" % source_id
        )
    periods = []
    for record in normalized["records"]:
        if (
            not isinstance(record, dict) or
            record.get("source_id") != source_id or
            record.get("source_bytes_sha256") !=
            binding["source_bytes_sha256"] or
            record.get("retrieved_at") != binding["retrieved_at"] or
            record.get("validated_at") != binding["retrieved_at"] or
            (
                record.get("observation_period") is not None and
                not isinstance(record["observation_period"], str)
            )
        ):
            raise CanonicalDataError(
                "normalized record provenance is invalid for %s" % source_id
            )
        if record.get("observation_period") is not None:
            periods.append(record["observation_period"])
    latest_observation_period = max(periods) if periods else None
    if latest_observation_period != binding["latest_observation_period"]:
        raise CanonicalDataError(
            "source latest observation binding is invalid for %s" % source_id
        )
    return {
        "binding": binding,
        "normalized": normalized,
        "receipt": receipt,
    }


def _verify_offline_receipt(receipt, binding, source_id, payloads):
    """B-LAND-3 §1 — the offline acquisition-receipt closure.

    The offline receipt is the single provenance home (§24): it carries the
    transcoder identity, the emitted response-schema sha, the per-file source
    shas and the as-of stamp, and NO http request/response block (present would
    fail the exact key set). Its bytes bind to the same source object / normalized
    object / clocks as a live receipt would, and its declared source-object byte
    length replaces the live receipt's http content_length check. Raises on any
    gap — a silent hole would let an un-attributed offline landing pass.
    """
    if (
        canonical_json_bytes(receipt) != payloads["receipt"] or
        not isinstance(receipt, dict) or
        frozenset(receipt) != OFFLINE_ACQUISITION_RECEIPT_FIELDS or
        receipt.get("schema_version") != OFFLINE_ACQUISITION_RECEIPT_SCHEMA or
        receipt.get("acquisition_kind") != OFFLINE_ACQUISITION_KIND or
        receipt.get("source_id") != source_id or
        receipt.get("source_bytes_sha256") !=
        binding["source_bytes_sha256"] or
        receipt.get("normalized_sha256") != binding["normalized_sha256"] or
        receipt.get("information_set_mode") != "archive_snapshot_asof" or
        not isinstance(receipt.get("as_of"), str) or
        not receipt["as_of"] or
        not isinstance(receipt.get("clocks"), dict) or
        frozenset(receipt["clocks"]) != RECEIPT_CLOCK_FIELDS or
        receipt["clocks"].get("retrieved_at") != binding["retrieved_at"] or
        receipt["clocks"].get("validated_at") != binding["retrieved_at"] or
        not isinstance(receipt.get("transcoder"), dict) or
        frozenset(receipt["transcoder"]) !=
        OFFLINE_RECEIPT_TRANSCODER_FIELDS or
        not isinstance(receipt["transcoder"].get("parser_version"), str) or
        not receipt["transcoder"]["parser_version"] or
        not isinstance(
            receipt["transcoder"].get("response_schema_sha256"), str
        ) or
        not SHA256_RE.match(receipt["transcoder"]["response_schema_sha256"]) or
        receipt["transcoder"].get("source_bytes_length") !=
        len(payloads["source_object"]) or
        not isinstance(receipt.get("source_files"), list) or
        not receipt["source_files"]
    ):
        raise CanonicalDataError(
            "source receipt binding is invalid for %s" % source_id
        )
    for entry in receipt["source_files"]:
        if (
            not isinstance(entry, dict) or
            frozenset(entry) != OFFLINE_RECEIPT_SOURCE_FILE_FIELDS or
            not isinstance(entry.get("source_sha256"), str) or
            not SHA256_RE.match(entry["source_sha256"]) or
            not isinstance(entry.get("source_path"), str) or
            not entry["source_path"] or
            not isinstance(entry.get("base"), str) or
            not entry["base"] or
            not isinstance(entry.get("vintage"), str) or
            not entry["vintage"] or
            type(entry.get("row_count")) is not int or
            entry["row_count"] < 0
        ):
            raise CanonicalDataError(
                "source receipt binding is invalid for %s" % source_id
            )


def _verify_offline_current_receipt(receipt, binding, source_id, payloads):
    """B-OFFLINE-2 §1 — the offline-CURRENT acquisition-receipt closure.

    A generic offline bind stored adapter-normalized cache bytes AS the source
    object (byte-unchanged, no transcode) and normalized them through a live
    adapter's parser. The receipt is the single provenance home: it cites the
    prefetch cache manifest (url + fetch UTC + sha256 + byte length) as the
    acquisition provenance, records the parser_id, and carries NO http
    request/response block and NO per-file vintage list. Its declared cache sha
    MUST equal the stored source-object sha (the cache bytes are the object) and
    its declared byte length MUST equal the object's — a silent gap would let an
    un-attributed cache landing pass. Any information-set mode is accepted (the
    non-vintage lanes); the mode taxonomy itself is validated at source-config
    admission, not here.
    """
    manifest = receipt.get("cache_manifest")
    if (
        canonical_json_bytes(receipt) != payloads["receipt"] or
        not isinstance(receipt, dict) or
        frozenset(receipt) != OFFLINE_CURRENT_ACQUISITION_RECEIPT_FIELDS or
        receipt.get("schema_version") !=
        OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA or
        receipt.get("acquisition_kind") != OFFLINE_CURRENT_ACQUISITION_KIND or
        receipt.get("source_id") != source_id or
        receipt.get("source_bytes_sha256") !=
        binding["source_bytes_sha256"] or
        receipt.get("normalized_sha256") != binding["normalized_sha256"] or
        not isinstance(receipt.get("information_set_mode"), str) or
        not receipt["information_set_mode"] or
        not isinstance(receipt.get("parser_id"), str) or
        not receipt["parser_id"] or
        not isinstance(receipt.get("clocks"), dict) or
        frozenset(receipt["clocks"]) != RECEIPT_CLOCK_FIELDS or
        receipt["clocks"].get("retrieved_at") != binding["retrieved_at"] or
        receipt["clocks"].get("validated_at") != binding["retrieved_at"] or
        not isinstance(manifest, dict) or
        frozenset(manifest) != OFFLINE_CURRENT_RECEIPT_CACHE_MANIFEST_FIELDS or
        not isinstance(manifest.get("url"), str) or
        not manifest["url"] or
        not isinstance(manifest.get("fetch_utc"), str) or
        not manifest["fetch_utc"] or
        not isinstance(manifest.get("source_sha256"), str) or
        not SHA256_RE.match(manifest["source_sha256"]) or
        manifest["source_sha256"] != binding["source_bytes_sha256"] or
        type(manifest.get("source_bytes_length")) is not int or
        manifest["source_bytes_length"] != len(payloads["source_object"])
    ):
        raise CanonicalDataError(
            "source receipt binding is invalid for %s" % source_id
        )


def _verify_staged_receipt(receipt, binding, source_id, payloads):
    """B-PROD-1 §3 — the staged live_http acquisition-receipt closure.

    A producer fetched real bytes into a staging dir; the committer admitted them
    and stamped producer_id + the explicit live_http_staged kind onto an
    otherwise-v1 http receipt. This closure is byte-for-byte the v1 http closure
    (same request/response/clocks binding to the same objects), PLUS two required
    additive fields: producer_id (WHO produced the bytes) and acquisition_kind
    (the kind marker). A missing/empty producer_id, a wrong kind, or an empty
    fetch timestamp FAILS — a silent gap would let an un-attributed staged
    landing pass, defeating the point of the producer/committer split.
    """
    if (
        canonical_json_bytes(receipt) != payloads["receipt"] or
        not isinstance(receipt, dict) or
        frozenset(receipt) != STAGED_ACQUISITION_RECEIPT_FIELDS or
        receipt.get("schema_version") != STAGED_ACQUISITION_RECEIPT_SCHEMA or
        receipt.get("acquisition_kind") != STAGED_ACQUISITION_KIND or
        not isinstance(receipt.get("producer_id"), str) or
        not receipt["producer_id"] or
        receipt.get("source_id") != source_id or
        receipt.get("source_bytes_sha256") !=
        binding["source_bytes_sha256"] or
        receipt.get("normalized_sha256") != binding["normalized_sha256"] or
        not isinstance(receipt.get("clocks"), dict) or
        frozenset(receipt["clocks"]) != RECEIPT_CLOCK_FIELDS or
        not isinstance(receipt["clocks"].get("retrieved_at"), str) or
        not receipt["clocks"]["retrieved_at"] or
        receipt["clocks"].get("retrieved_at") != binding["retrieved_at"] or
        receipt["clocks"].get("validated_at") != binding["retrieved_at"] or
        not isinstance(receipt.get("request"), dict) or
        frozenset(receipt["request"]) != RECEIPT_REQUEST_FIELDS or
        not isinstance(receipt.get("response"), dict) or
        frozenset(receipt["response"]) != RECEIPT_RESPONSE_FIELDS or
        receipt["response"].get("content_length") !=
        len(payloads["source_object"])
    ):
        raise CanonicalDataError(
            "source receipt binding is invalid for %s" % source_id
        )


def verify_offline_source_binding(store_root, binding):
    """Strict offline binding verify: the full closure PLUS a kind guard.

    Runs the exact same raw -> normalized -> receipt -> binding closure as
    ``verify_source_binding`` and additionally requires the bound receipt to be
    the offline schema. This is the guard that a fabricated LIVE (v1 http)
    receipt for an offline object cannot masquerade as an offline landing —
    its bytes may be a structurally valid v1 receipt (the generic verify would
    accept them), but the declared offline kind is missing (§1.2 case d).
    """
    evidence = verify_source_binding(store_root, binding)
    if (
        evidence["receipt"].get("schema_version") !=
        OFFLINE_ACQUISITION_RECEIPT_SCHEMA
    ):
        raise CanonicalDataError(
            "offline binding requires the offline acquisition-receipt schema "
            "(kind mismatch) for %s" % binding["source_id"]
        )
    return evidence


def verify_offline_current_source_binding(store_root, binding):
    """Strict offline-current binding verify: the full closure PLUS a kind guard.

    Runs the exact same raw -> normalized -> receipt -> binding closure as
    ``verify_source_binding`` and additionally requires the bound receipt to be
    the offline-current schema. This is the guard that neither a fabricated LIVE
    (v1 http) receipt nor an offline_vintage receipt can masquerade as a generic
    offline-current landing — the declared offline-current kind must be present.
    """
    evidence = verify_source_binding(store_root, binding)
    if (
        evidence["receipt"].get("schema_version") !=
        OFFLINE_CURRENT_ACQUISITION_RECEIPT_SCHEMA
    ):
        raise CanonicalDataError(
            "offline-current binding requires the offline-current "
            "acquisition-receipt schema (kind mismatch) for %s"
            % binding["source_id"]
        )
    return evidence


def verify_source_head(store_root, source_id, head):
    """Verify the exact source-head schema plus its entire evidence chain."""
    binding = source_binding_from_head(source_id, head)
    evidence = verify_source_binding(store_root, binding)
    normalized = evidence["normalized"]
    receipt = evidence["receipt"]
    # An offline receipt carries no http response block; its head therefore has
    # no etag / last_modified validator (both None). A v1 receipt keeps its
    # response validators exactly as before.
    response = receipt.get("response")
    receipt_etag = response.get("etag") if isinstance(response, dict) else None
    receipt_last_modified = (
        response.get("last_modified") if isinstance(response, dict) else None
    )
    if (
        normalized.get("parser_id") != "rmv2-live/%s" % head["adapter"] or
        receipt_etag != head["etag"] or
        receipt_last_modified != head["last_modified"]
    ):
        raise CanonicalDataError(
            "runtime source head does not match immutable evidence"
        )
    return evidence


def _binding_attestation_path(store_root, digest):
    if not SHA256_RE.match(digest):
        raise CanonicalDataError("binding attestation digest is unsafe")
    return (
        Path(store_root) / "binding_attestation" /
        BINDING_ATTESTATION_VERSION / "sha256" / digest[:2] /
        (digest + ".json")
    )


def _require_binding_evidence_present(store_root, binding):
    """Fail-closed existence guard for attested evidence (stat only, no read)."""
    store_root = Path(store_root)
    paths = (
        store_root / "normalized" / "sha256" /
        binding["normalized_sha256"][:2] /
        (binding["normalized_sha256"] + ".json"),
        store_root / "receipts" / binding["source_id"] /
        (binding["receipt_sha256"] + ".json"),
        store_root / "objects" / "sha256" /
        binding["source_bytes_sha256"][:2] /
        (binding["source_bytes_sha256"] + ".bin"),
    )
    for path in paths:
        try:
            info = os.stat(str(path))
        except FileNotFoundError:
            raise CanonicalDataError(
                "attested source evidence is missing for %s" %
                binding["source_id"]
            )
        if not stat.S_ISREG(info.st_mode):
            raise CanonicalDataError(
                "attested source evidence is not a regular file for %s" %
                binding["source_id"]
            )


def _binding_attestation_record(binding, evidence):
    normalized = evidence["normalized"]
    receipt = evidence["receipt"]
    # Offline receipts carry no http response block -> no etag / last_modified.
    response = receipt.get("response")
    receipt_etag = response.get("etag") if isinstance(response, dict) else None
    receipt_last_modified = (
        response.get("last_modified") if isinstance(response, dict) else None
    )
    return {
        "etag": receipt_etag,
        "last_modified": receipt_last_modified,
        "latest_observation_period": binding["latest_observation_period"],
        "normalized_sha256": binding["normalized_sha256"],
        "parser_id": normalized.get("parser_id"),
        "receipt_sha256": binding["receipt_sha256"],
        "record_count": binding["record_count"],
        "schema_version": BINDING_ATTESTATION_SCHEMA,
        "source_bytes_sha256": binding["source_bytes_sha256"],
        "source_id": binding["source_id"],
    }


def attest_source_binding(store_root, binding):
    """Content-addressed source-binding attestation for the hot paths.

    Returns the derived facts (source_id, parser_id, etag, last_modified,
    record_count, latest_observation_period) that the publish, generation-read,
    and inventory hot paths consume, WITHOUT re-reading the (multi-GB, weekly-
    vintage) normalized blob when a content-addressed attestation already
    exists.  The complete raw -> normalized -> receipt -> binding closure is
    computed exactly once on a cache miss via ``verify_source_binding`` (which
    writes the immutable attestation) and remains the default in
    ``verify_source_binding`` / ``read_verified_generation`` / ``rmv2_live
    verify``; this fast path never weakens that oracle.  Byte-for-byte identical
    facts to the full closure: an attestation is a pure function of the
    immutable, content-addressed evidence keyed by ``normalized_sha256``.
    """
    store_root = Path(store_root).resolve()
    binding = validate_source_binding(binding)
    digest = binding["normalized_sha256"]
    path = _binding_attestation_path(store_root, digest)
    if path.exists():
        record = read_json(path)
        if (
            not isinstance(record, dict) or
            frozenset(record) != BINDING_ATTESTATION_FIELDS or
            record.get("schema_version") != BINDING_ATTESTATION_SCHEMA or
            record.get("normalized_sha256") != digest or
            record.get("receipt_sha256") != binding["receipt_sha256"] or
            record.get("source_bytes_sha256") !=
            binding["source_bytes_sha256"] or
            record.get("source_id") != binding["source_id"] or
            record.get("record_count") != binding["record_count"] or
            record.get("latest_observation_period") !=
            binding["latest_observation_period"]
        ):
            raise CanonicalDataError(
                "binding attestation is corrupt for %s" % binding["source_id"]
            )
        _require_binding_evidence_present(store_root, binding)
        return record
    evidence = verify_source_binding(store_root, binding)
    record = _binding_attestation_record(binding, evidence)
    data = canonical_json_bytes(record)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            atomic_write(path, data, mode=0o444)
        except OSError as exc:
            warnings.warn(
                "binding attestation cache write failed; verified evidence "
                "remains authoritative: %s" % exc,
                RuntimeWarning,
            )
    return record


def attest_source_head(store_root, source_id, head):
    """Attested analog of ``verify_source_head`` for the recovery hot path.

    Asserts the exact runtime-head-to-immutable-evidence relation
    (parser_id/etag/last_modified) against the content-addressed attestation,
    reading the normalized blob only on a cache miss. The full closure remains
    in ``verify_source_head`` (``_verify_store`` / ``rmv2_live verify``).
    """
    binding = source_binding_from_head(source_id, head)
    attestation = attest_source_binding(store_root, binding)
    if (
        attestation["parser_id"] != "rmv2-live/%s" % head["adapter"] or
        attestation["etag"] != head["etag"] or
        attestation["last_modified"] != head["last_modified"]
    ):
        raise CanonicalDataError(
            "runtime source head does not match immutable evidence"
        )
    return attestation


def read_verified_generation(
    public_root,
    generations_root,
    materialize_members=None,
    attest_bindings=False,
):
    """Resolve and authenticate an immutable public generation.

    Every member is byte-counted and hashed. ``materialize_members`` only
    controls which already-authenticated JSON members are parsed and returned.

    ``attest_bindings=False`` (default) re-runs the full per-source raw ->
    normalized -> receipt -> binding closure and is the integrity oracle used by
    ``rmv2_live verify``.  Hot operational readers (the pipeline tick, the live
    server, the post-publish readback) pass ``attest_bindings=True`` to use the
    content-addressed attestation instead, so authenticating a generation is
    O(changed sources) rather than O(total normalized bytes); the pointer,
    manifest, member SHA-256s, receipt map, and storage fingerprint are still
    checked identically.
    """
    if materialize_members is None:
        requested_members = tuple(GENERATION_MEMBERS)
    else:
        if isinstance(materialize_members, (str, bytes)):
            raise CanonicalDataError("generation materialization set is invalid")
        try:
            requested_members = tuple(materialize_members)
        except TypeError:
            raise CanonicalDataError("generation materialization set is invalid")
        if (
            not requested_members or
            len(set(requested_members)) != len(requested_members) or
            not set(requested_members).issubset(set(GENERATION_MEMBERS))
        ):
            raise CanonicalDataError("generation materialization set is invalid")
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
        if not isinstance(pointer[field], str) or not SHA256_RE.match(pointer[field]):
            raise CanonicalDataError("live pointer contains an invalid digest")
    if pointer["generation_sha256"] != pointer["manifest_sha256"]:
        raise CanonicalDataError("generation and manifest identity differ")

    generation_root = generations_root / pointer["generation_sha256"]
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
        actual_names = {path.name for path in generation_root.iterdir()}
    except FileNotFoundError:
        raise
    if actual_names != set(GENERATION_MEMBERS) | {"manifest.json"}:
        raise CanonicalDataError("generation contains an unexpected member set")
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
        raise CanonicalDataError("generation manifest has an invalid key set")
    if manifest["schema_version"] != "recession-monitor-v2.live-generation-manifest.v2":
        raise CanonicalDataError("unsupported generation manifest schema")
    if set(manifest["members"]) != set(GENERATION_MEMBERS):
        raise CanonicalDataError("generation member set is incomplete")
    manifest_source_receipts = manifest["source_head_receipt_sha256"]
    if not isinstance(manifest_source_receipts, dict):
        raise CanonicalDataError(
            "generation source receipt binding is invalid"
        )
    for source_id, receipt_sha256 in manifest_source_receipts.items():
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
        if set(specification) != {"bytes", "sha256", "schema_version"}:
            raise CanonicalDataError("generation member specification is invalid")
        data = safe_regular_file(generation_root / name, generations_root)
        if len(data) != specification["bytes"]:
            raise CanonicalDataError("generation member byte count mismatch")
        if sha256_bytes(data) != specification["sha256"]:
            raise CanonicalDataError("generation member hash mismatch")
        if pointer[pointer_fields[name]] != specification["sha256"]:
            raise CanonicalDataError("pointer member hash mismatch")
        if name == "snapshot.json" or name in requested_members:
            value = strict_json_loads(data)
            if value.get("schema_version") != specification["schema_version"]:
                raise CanonicalDataError("generation member schema mismatch")
            if name == "snapshot.json":
                snapshot_value = value
            if name in requested_members:
                members[name] = value

    snapshot_sources = snapshot_value.get("sources")
    if not isinstance(snapshot_sources, list):
        raise CanonicalDataError("generation snapshot sources are invalid")
    snapshot_source_receipts = {}
    for source in snapshot_sources:
        if not isinstance(source, dict):
            raise CanonicalDataError("generation snapshot source is invalid")
        source_id = source.get("source_id")
        receipt_sha256 = source.get("receipt_sha256")
        if (
            not isinstance(source_id, str) or
            not SOURCE_ID_RE.match(source_id) or
            source_id in snapshot_source_receipts or
            not isinstance(receipt_sha256, str) or
            not SHA256_RE.match(receipt_sha256)
        ):
            raise CanonicalDataError("generation snapshot source is invalid")
        snapshot_source_receipts[source_id] = receipt_sha256
    if snapshot_source_receipts != manifest_source_receipts:
        raise CanonicalDataError(
            "generation source receipt binding differs from snapshot"
        )
    store_root = generations_root.parent
    for source in snapshot_sources:
        if attest_bindings:
            attest_source_binding(store_root, source)
        else:
            verify_source_binding(store_root, source)

    pointer_bytes_after = safe_regular_file(pointer_path, public_root)
    if pointer_bytes_before != pointer_bytes_after:
        raise CanonicalDataError("live pointer changed during generation read")
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
        "storage_fingerprint": storage_fingerprint_after,
    }
