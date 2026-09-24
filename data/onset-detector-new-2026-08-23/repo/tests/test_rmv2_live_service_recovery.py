"""Phase 1 service-recovery contracts.

These pin the fixes for the cold-start / post-publish blocking symptom and the
client-disconnect BrokenPipe noise, without weakening the immutable-generation
verification contract exercised in ``test_rmv2_live_data_integrity``.
"""

from __future__ import absolute_import

import http.client
import io
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from live_data.rmv2_live import server as server_module
from live_data.rmv2_live.server import create_server
from live_data.rmv2_live.store import LiveStore
from live_data.rmv2_live.canonical import strict_json_loads

from tests.test_rmv2_live_data_integrity import (
    config_value,
    coverage_value,
    snapshot_value,
    status_value,
    write_registry,
)


class ServiceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_registry(self.root)
        self.store = LiveStore(self.root, config_value())
        self.store.initialize()
        self.pointer = self.store.publish_generation(
            snapshot_value("immutable"),
            status_value("immutable"),
            coverage_value("immutable"),
        )
        self.generations = self.store.root / "generations"

    def tearDown(self):
        self.temp.cleanup()

    def _build_server(self, bind_and_activate=True):
        return create_server(
            "127.0.0.1",
            0,
            self.store.public,
            generations_root=self.generations,
            bind_and_activate=bind_and_activate,
        )

    def _serve(self, server):
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return thread

    def _request(self, port, path):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request(
            "GET", path, headers={"Host": "127.0.0.1:%d" % port}
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, strict_json_loads(body)

    def test_deferred_bind_and_activate_defers_listening_until_activated(self):
        server = self._build_server(bind_and_activate=False)
        self.addCleanup(server.server_close)
        # Not yet bound: the requested wildcard port has not been resolved.
        self.assertEqual(server.server_address[1], 0)
        server.server_bind()
        server.server_activate()
        self.assertNotEqual(server.server_address[1], 0)

    def test_warm_primes_caches_so_requests_do_not_reverify(self):
        server = self._build_server()
        self.addCleanup(server.server_close)
        with mock.patch.object(
            server_module,
            "read_verified_generation",
            wraps=server_module.read_verified_generation,
        ) as verified:
            server.warm()
            calls_after_warm = verified.call_count
            self.assertGreaterEqual(calls_after_warm, 1)
            port = server.server_address[1]
            self._serve(server)
            self.assertEqual(self._request(port, "/api/v1/bundle")[0], 200)
            self.assertEqual(self._request(port, "/healthz")[0], 200)
            self.assertEqual(
                verified.call_count,
                calls_after_warm,
                "warmed caches must serve requests without re-verifying",
            )

    def test_handle_error_swallows_client_disconnect_without_traceback(self):
        server = self._build_server()
        self.addCleanup(server.server_close)
        captured = io.StringIO()
        original = sys.stderr
        sys.stderr = captured
        try:
            try:
                raise BrokenPipeError("client closed the socket")
            except BrokenPipeError:
                server.handle_error(object(), ("127.0.0.1", 12345))
        finally:
            sys.stderr = original
        self.assertNotIn("Traceback", captured.getvalue())
        self.assertNotIn("BrokenPipeError", captured.getvalue())

    def test_handle_error_still_reports_unexpected_errors(self):
        server = self._build_server()
        self.addCleanup(server.server_close)
        captured = io.StringIO()
        original = sys.stderr
        sys.stderr = captured
        try:
            try:
                raise ValueError("a genuine server bug")
            except ValueError:
                server.handle_error(object(), ("127.0.0.1", 12345))
        finally:
            sys.stderr = original
        self.assertIn("Traceback", captured.getvalue())

    def test_client_disconnect_leaves_service_healthy(self):
        server = self._build_server()
        self.addCleanup(server.server_close)
        server.warm()
        port = server.server_address[1]
        self._serve(server)
        # Connect, send a request, then abandon it without reading the reply.
        import socket

        raw = socket.create_connection(("127.0.0.1", port), timeout=5)
        raw.sendall(
            b"GET /api/v1/bundle HTTP/1.1\r\n"
            b"Host: 127.0.0.1:%d\r\n\r\n" % port
        )
        raw.close()
        # The service must keep answering after the abrupt disconnect.
        self.assertEqual(self._request(port, "/healthz")[0], 200)
        self.assertEqual(self._request(port, "/api/v1/bundle")[0], 200)


if __name__ == "__main__":
    unittest.main()
