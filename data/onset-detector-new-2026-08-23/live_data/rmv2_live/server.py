"""Loopback-only read-only HTTP API for the local live-data files."""

from __future__ import absolute_import

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .canonical import (
    CanonicalDataError,
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from .store import (
    generation_storage_fingerprint,
    read_verified_generation,
    safe_regular_file,
)
from .publish_gate import (
    discover_project_root,
    filter_snapshot_series,
    load_source_publish_class_map,
    series_item_is_publishable,
)


ALLOWED_ORIGIN_RE = re.compile(r"^http://(?:127\.0\.0\.1|localhost)(?::\d+)?$")


class SnapshotUnavailableError(FileNotFoundError):
    """Raised only when no public generation pointer has been published."""


class LiveDataApiHandler(BaseHTTPRequestHandler):
    server_version = "RecessionMonitorV2LiveData/1.0"

    def log_message(self, format_string, *args):
        # Keep launchd output quiet; errors are returned as typed JSON.
        return

    def _security_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")

    def _origin(self):
        origin = self.headers.get("Origin")
        if origin is None:
            return None
        if origin == "null" or ALLOWED_ORIGIN_RE.match(origin):
            return origin
        raise PermissionError("origin is not allowed")

    def _validate_host(self):
        host = self.headers.get("Host", "")
        hostname = host.rsplit(":", 1)[0].strip("[]").lower()
        if hostname not in ("127.0.0.1", "localhost"):
            raise PermissionError("host is not allowed")

    def _send_json(self, status, value, origin=None):
        data = canonical_json_bytes(value)
        try:
            self.send_response(status)
            self._security_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            if origin is not None:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # A browser that times out or closes a tab may leave no response
            # channel. This is not a local-state failure and must not trigger
            # a second error response on the same closed socket.
            return False
        return True

    def _error(self, status, code, message, origin=None):
        self._send_json(status, {
            "error": {"code": code, "message": message},
            "schema_version": "recession-monitor-v2.api-error.v1",
        }, origin)

    def do_OPTIONS(self):
        try:
            self._validate_host()
            origin = self._origin()
        except PermissionError as exc:
            self._error(403, "forbidden", str(exc))
            return
        self.send_response(204)
        self._security_headers()
        if origin is not None:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_HEAD(self):
        self._handle_read()

    def do_GET(self):
        self._handle_read()

    def _reject_write(self):
        try:
            self._validate_host()
            origin = self._origin()
        except PermissionError as exc:
            self._error(403, "forbidden", str(exc))
            return
        self._error(405, "method_not_allowed", "the API is read-only", origin)

    def do_POST(self):
        self._reject_write()

    def do_PUT(self):
        self._reject_write()

    def do_DELETE(self):
        self._reject_write()

    def do_PATCH(self):
        self._reject_write()

    def _read_public_json(self, name):
        data = safe_regular_file(self.server.public_root / name, self.server.public_root)
        return strict_json_loads(data)

    def _read_generation(self):
        return self.server.read_generation()

    def _read_status_generation(self):
        return self.server.read_status_generation()

    def _generation_member(self, name):
        return self._read_generation()["members"][name]

    def _status_generation_member(self):
        return self._read_status_generation()["members"]["status.json"]

    def _read_atomic_bundle(self):
        """Return one verified immutable generation plus separate operations state."""
        generation = self._read_generation()
        specification = generation["manifest"]["members"]["snapshot.json"]
        operational_status = None
        try:
            operational_status = self._read_public_json("operational_status.json")
        except FileNotFoundError:
            operational_status = None
        return {
            "operational_status": operational_status,
            "pointer": generation["pointer"],
            "schema_version": "recession-monitor-v2.live-api-bundle.v2",
            "snapshot_bytes": specification["bytes"],
            "status": generation["members"]["status.json"],
        }

    def _handle_read(self):
        try:
            self._validate_host()
            origin = self._origin()
        except PermissionError as exc:
            self._error(403, "forbidden", str(exc))
            return
        path = urlsplit(self.path).path
        try:
            if path in ("/", "/api/v1/health", "/healthz"):
                generation = self._read_status_generation()
                status = generation["members"]["status.json"]
                service_state = status["service_state"]
                try:
                    operational = self._read_public_json("operational_status.json")
                    if (
                        operational.get("schema_version") !=
                        "recession-monitor-v2.live-operational-status.v1" or
                        operational.get("active_generation_sha256") !=
                        generation["pointer"]["generation_sha256"]
                    ):
                        service_state = "degraded"
                    else:
                        service_state = operational.get(
                            "service_state",
                            "degraded",
                        )
                except FileNotFoundError:
                    service_state = "degraded"
                self._send_json(200, {
                    "generated_at": status["generated_at"],
                    "no_ai": True,
                    "schema_version": "recession-monitor-v2.health.v1",
                    "service_state": service_state,
                }, origin)
                return
            if path == "/api/v1/status":
                self._send_json(200, self._generation_member("status.json"), origin)
                return
            if path == "/api/v1/operational-status":
                self._send_json(
                    200,
                    self._read_public_json("operational_status.json"),
                    origin,
                )
                return
            if path == "/api/v1/pointer":
                self._send_json(200, self._read_generation()["pointer"], origin)
                return
            if path == "/api/v1/bundle":
                self._send_json(200, self._read_atomic_bundle(), origin)
                return
            if path in ("/api/v1/snapshot", "/api/v1/latest"):
                # Rights firewall (B-LAND-11-R2): strip internal_only series so
                # no raw value or observation history of a licensed family is
                # served publicly. Internal tools read the store directly.
                snapshot = filter_snapshot_series(
                    self._generation_member("snapshot.json"),
                    self.server.publish_class_map(),
                )
                self._send_json(200, snapshot, origin)
                return
            if path == "/api/v1/sources":
                self._send_json(200, self._generation_member("coverage.json"), origin)
                return
            prefix = "/api/v1/series/"
            if path.startswith(prefix):
                series_id = unquote(path[len(prefix):])
                if not series_id or "/" in series_id or "\\" in series_id or len(series_id) > 180:
                    self._error(400, "invalid_series_id", "series id is invalid", origin)
                    return
                snapshot = self._generation_member("snapshot.json")
                item = snapshot["series"].get(series_id)
                # Rights firewall: a licensed (internal_only) series is 404, the
                # same response as an absent series, so publicness of a licensed
                # id is not even confirmed.
                if item is None or not series_item_is_publishable(
                    item, self.server.publish_class_map()
                ):
                    self._error(404, "series_not_found", "series was not found", origin)
                    return
                self._send_json(200, item, origin)
                return
            self._error(404, "not_found", "route was not found", origin)
        except SnapshotUnavailableError:
            self._error(503, "snapshot_unavailable", "no live snapshot has been published", origin)
        except (CanonicalDataError, FileNotFoundError, OSError, ValueError):
            self._error(
                500,
                "invalid_local_state",
                "the local generation failed integrity validation",
                origin,
            )


class LoopbackHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address,
        handler,
        public_root,
        generations_root,
        bind_and_activate=True,
    ):
        self.public_root = Path(public_root).resolve()
        self.generations_root = Path(generations_root).resolve()
        # Locate the production registry by walking up (public_root is
        # <root>/live_data/public in deploy, <root>/public in tests). None when
        # no production registry exists -> the rights filter no-ops.
        self._project_root = discover_project_root(self.public_root)
        self._publish_class_map = None
        self._publish_class_map_lock = threading.Lock()
        self._generation_cache = None
        self._generation_cache_lock = threading.Lock()
        self._status_generation_cache = None
        self._status_generation_cache_lock = threading.Lock()
        ThreadingHTTPServer.__init__(
            self,
            address,
            handler,
            bind_and_activate=bind_and_activate,
        )

    def publish_class_map(self):
        """Lazily-cached source_id -> publish_class map (rights firewall, P2).

        Read once from the registry + sources config; the registry is an
        authority-tree file that only changes via a committed batch, so caching
        for the server's lifetime is safe and keeps the read off the hot path.
        """
        with self._publish_class_map_lock:
            if self._publish_class_map is None:
                self._publish_class_map = (
                    load_source_publish_class_map(self._project_root)
                    if self._project_root is not None
                    else {}
                )
            return self._publish_class_map

    def handle_error(self, request, client_address):
        """Swallow client-disconnect noise; still report genuine bugs.

        A loopback client that times out or closes a tab tears down the
        socket mid-response. That surfaces as a connection-family error while
        the handler flushes; it is not a local-state failure and must not spew
        a traceback on every short-timeout client. Any other exception is a
        real defect and is reported exactly as the base server would.
        """
        exc_type = sys.exc_info()[0]
        if exc_type is not None and issubclass(exc_type, (ConnectionError, BrokenPipeError)):
            return
        ThreadingHTTPServer.handle_error(self, request, client_address)

    def warm(self):
        """Pre-authenticate the active generation before accepting requests.

        Cold reads fully re-verify every immutable member and source-evidence
        chain (the locked integrity contract). Doing that once here, off the
        request path, keeps the first ``/api/v1/bundle`` and ``/api/v1/health``
        after a (re)start prompt instead of blocking a client for the whole
        verification and provoking BrokenPipe churn.
        """
        self.read_generation()
        self.read_status_generation()

    def _read_pointer_bytes(self):
        try:
            return safe_regular_file(
                self.public_root / "latest.pointer.json",
                self.public_root,
            )
        except FileNotFoundError as exc:
            raise SnapshotUnavailableError(
                "no live snapshot has been published"
            ) from exc

    def read_generation(self):
        pointer_bytes = self._read_pointer_bytes()
        with self._generation_cache_lock:
            if (
                self._generation_cache is not None and
                self._generation_cache["pointer_bytes"] == pointer_bytes
            ):
                current_fingerprint = generation_storage_fingerprint(
                    self.public_root,
                    self.generations_root,
                    self._generation_cache["pointer"],
                    self._generation_cache["source_bindings"],
                )
                if (
                    current_fingerprint ==
                    self._generation_cache["storage_fingerprint"]
                ):
                    return self._generation_cache
            generation = read_verified_generation(
                self.public_root,
                self.generations_root,
                attest_bindings=True,
            )
            self._generation_cache = generation
            return generation

    def read_status_generation(self):
        pointer_bytes = self._read_pointer_bytes()
        with self._status_generation_cache_lock:
            if (
                self._status_generation_cache is not None and
                self._status_generation_cache["pointer_bytes"] == pointer_bytes
            ):
                current_fingerprint = generation_storage_fingerprint(
                    self.public_root,
                    self.generations_root,
                    self._status_generation_cache["pointer"],
                    self._status_generation_cache["source_bindings"],
                )
                if (
                    current_fingerprint ==
                    self._status_generation_cache[
                        "storage_fingerprint"
                    ]
                ):
                    return self._status_generation_cache
            generation = read_verified_generation(
                self.public_root,
                self.generations_root,
                materialize_members=("status.json",),
                attest_bindings=True,
            )
            self._status_generation_cache = generation
            return generation


def create_server(
    host,
    port,
    public_root,
    generations_root=None,
    bind_and_activate=True,
):
    if host != "127.0.0.1":
        raise ValueError("live data API may only bind to 127.0.0.1")
    public_root = Path(public_root).resolve()
    if generations_root is None:
        generations_root = public_root.parent / "store" / "generations"
    return LoopbackHttpServer(
        (host, int(port)),
        LiveDataApiHandler,
        public_root,
        generations_root,
        bind_and_activate=bind_and_activate,
    )
