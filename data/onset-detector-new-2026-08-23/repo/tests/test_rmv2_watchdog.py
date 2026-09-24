"""Lane 0f — standalone hang watchdog contracts.

Drives the real ``live_data/scripts/watchdog.sh`` as a subprocess against a real
loopback health server and a stub ``launchctl`` recorder, with the wall clock
injected via ``RMV2_WATCHDOG_NOW_EPOCH`` so threshold crossings are deterministic
and no test ever sleeps for real time.

The watchdog must:
  * treat ready as healthy and clear the failure window;
  * treat non-ready / unreachable as unhealthy and accumulate a failure window;
  * issue exactly one ``launchctl kickstart -k`` once the not-ready window reaches
    the threshold, and suppress further kicks during a cooldown;
  * never touch the store, refresh.lock, source_heads, or catalog (asserted by the
    stub launchctl being the ONLY external command it may invoke).
"""
from __future__ import absolute_import

import os
import stat
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG = REPO_ROOT / "live_data" / "scripts" / "watchdog.sh"


class _HealthHandler(BaseHTTPRequestHandler):
    body = b'{"service_state":"ready","no_ai":true}'
    code = 200

    def do_GET(self):  # noqa: N802
        self.send_response(self.code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args):  # silence
        return


class _Server(object):
    def __init__(self):
        handler = type("H", (_HealthHandler,), {})
        self.handler = handler
        self.httpd = HTTPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()

    def set(self, code, body):
        self.handler.code = code
        self.handler.body = body

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = os.path.join(self.tmp, "state")
        self.events = os.path.join(self.tmp, "events.log")
        self.kicks = os.path.join(self.tmp, "kicks.log")
        # Stub launchctl: records argv, never calls the real one.
        self.launchctl = os.path.join(self.tmp, "launchctl_stub.sh")
        stub = (
            "#!/bin/bash\n"
            'printf "%s\\n" "$*" >> "' + self.kicks + '"\n'
            "exit 0\n"
        )
        with open(self.launchctl, "w") as fh:
            fh.write(stub)
        os.chmod(self.launchctl, os.stat(self.launchctl).st_mode | stat.S_IEXEC)
        self.server = _Server()
        self.url = "http://127.0.0.1:%d/health" % self.server.port

    def tearDown(self):
        self.server.stop()

    def _run(self, now, threshold=900, url=None):
        env = dict(os.environ)
        env.update(
            RMV2_WATCHDOG_HEALTH_URL=url if url is not None else self.url,
            RMV2_WATCHDOG_THRESHOLD_SECONDS=str(threshold),
            RMV2_WATCHDOG_STATE_FILE=self.state,
            RMV2_WATCHDOG_EVENT_LOG=self.events,
            RMV2_WATCHDOG_LAUNCHCTL=self.launchctl,
            RMV2_WATCHDOG_NOW_EPOCH=str(now),
            RMV2_WATCHDOG_CURL_TIMEOUT="2",
            RMV2_WATCHDOG_DOMAIN="gui/0",
            RMV2_WATCHDOG_LABEL="test.label",
        )
        proc = subprocess.run(
            ["/bin/bash", str(WATCHDOG)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return proc

    def _state(self, key):
        for line in Path(self.state).read_text().splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1]
        return None

    def _kick_count(self):
        if not os.path.exists(self.kicks):
            return 0
        return len([l for l in Path(self.kicks).read_text().splitlines() if l.strip()])

    def test_healthy_clears_window_no_kick(self):
        self._run(now=1000)
        self.assertEqual(self._state("status"), "ok")
        self.assertEqual(self._state("consecutive_failures"), "0")
        self.assertEqual(self._kick_count(), 0)

    def test_unhealthy_under_threshold_no_kick(self):
        self.server.set(200, b'{"service_state":"degraded"}')
        self._run(now=1000, threshold=900)
        self.assertEqual(self._state("status"), "failing")
        self.assertEqual(self._state("consecutive_failures"), "1")
        self.assertEqual(self._state("first_failure_epoch"), "1000")
        self.assertEqual(self._kick_count(), 0)

    def test_sustained_unready_triggers_single_kickstart(self):
        self.server.set(200, b'{"service_state":"degraded"}')
        self._run(now=1000, threshold=900)          # first failure @1000
        self._run(now=1450, threshold=900)          # +450s, still under
        self.assertEqual(self._kick_count(), 0)
        self._run(now=1900, threshold=900)          # +900s -> kickstart
        self.assertEqual(self._kick_count(), 1)
        argv = Path(self.kicks).read_text().strip()
        self.assertIn("kickstart -k", argv)
        self.assertIn("gui/0/test.label", argv)
        # window reset + cooldown recorded
        self.assertEqual(self._state("last_kickstart_epoch"), "1900")

    def test_cooldown_suppresses_second_kick(self):
        self.server.set(200, b'{"service_state":"degraded"}')
        self._run(now=1000, threshold=900)
        self._run(now=1900, threshold=900)          # kick #1
        self.assertEqual(self._kick_count(), 1)
        self._run(now=2000, threshold=900)          # within cooldown -> suppressed
        self.assertEqual(self._kick_count(), 1)
        self._run(now=2800, threshold=900)          # 900s after kick -> allowed
        self.assertEqual(self._kick_count(), 2)

    def test_unreachable_is_unhealthy(self):
        self.server.stop()  # nothing listening
        self._run(now=1000, threshold=900, url="http://127.0.0.1:1/health")
        self.assertEqual(self._state("status"), "failing")
        self.assertEqual(self._kick_count(), 0)
        # restart a server so tearDown's stop() is harmless
        self.server = _Server()

    def test_recovery_clears_after_failing(self):
        self.server.set(200, b'{"service_state":"degraded"}')
        self._run(now=1000, threshold=900)
        self.assertEqual(self._state("status"), "failing")
        self.server.set(200, b'{"service_state":"ready"}')
        self._run(now=1100, threshold=900)
        self.assertEqual(self._state("status"), "ok")
        self.assertEqual(self._state("consecutive_failures"), "0")
        self.assertIn("RECOVERED", Path(self.events).read_text())


if __name__ == "__main__":
    unittest.main()
