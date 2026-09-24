"""B-SAFE-1 §4.4 — deny_frozen PreToolUse guard.

Drives the hook as a subprocess with tool-call JSON on stdin (exactly how
Claude Code invokes it) and asserts the exit code: 2 = blocked, 0 = allowed.
"""

from __future__ import absolute_import

import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "deny_frozen.py"
SANCTIONS = REPO / "model_authority" / "sanctions"


def _stamp(dt):
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _now():
    return datetime.now(timezone.utc)


def run(event):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return proc.returncode, proc.stderr


def edit(path, old="", new=""):
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path), "old_string": old, "new_string": new}}


class TokenMixin(unittest.TestCase):
    """Creates real sanction tokens under model_authority/sanctions and removes
    them at teardown. Tokens must live in the real repo because the hook resolves
    the repo root from its own path."""

    def setUp(self):
        self._created = []
        self._dir_created = not SANCTIONS.exists()
        SANCTIONS.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        for p in self._created:
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        if self._dir_created:
            try:
                SANCTIONS.rmdir()
            except OSError:
                pass

    def make_token(self, batch_id, file_rel, expiry_dt):
        p = SANCTIONS / ("UNFREEZE.%s.json" % batch_id)
        p.write_text(json.dumps({
            "batch_id": batch_id,
            "file_path": file_rel,
            "expiry": _stamp(expiry_dt),
        }), encoding="utf-8")
        self._created.append(p)
        return p


class DenyFrozenTests(unittest.TestCase):
    def test_blocks_index_v1(self):
        rc, err = run(edit(REPO / "method_source/index_v1.py"))
        self.assertEqual(rc, 2)
        self.assertIn("frozen", err.lower())

    def test_blocks_target_ledger_member(self):
        rc, _ = run(edit(REPO / "model_authority/target_ledger/instrument_onset_target_ledger.v1.json"))
        self.assertEqual(rc, 2)

    def test_blocks_nowcast_and_forecaster_and_registry(self):
        for rel in ("method_source/nowcast_live.py", "method_source/forecaster_site.py",
                    "model_authority/parameters/parameter_registry.v1.json"):
            rc, _ = run(edit(REPO / rel))
            self.assertEqual(rc, 2, rel)

    def test_allows_ordinary_file(self):
        rc, _ = run(edit(REPO / "README.md", old="x", new="y"))
        self.assertEqual(rc, 0)

    def test_allows_write_to_ordinary_file(self):
        rc, _ = run({"tool_name": "Write", "tool_input": {"file_path": str(REPO / "PHASE2_PROGRESS.md"), "content": "z"}})
        self.assertEqual(rc, 0)

    def test_ignores_non_edit_tools(self):
        rc, _ = run({"tool_name": "Read", "tool_input": {"file_path": str(REPO / "method_source/index_v1.py")}})
        self.assertEqual(rc, 0)

    def test_growth_floor_raise_allowed(self):
        rc, _ = run(edit(REPO / GROWTH_REL, old='"fred_icsa": 100', new='"fred_icsa": 120'))
        self.assertEqual(rc, 0)

    def test_growth_floor_lowering_blocked(self):
        rc, err = run(edit(REPO / GROWTH_REL, old='"fred_icsa": 100', new='"fred_icsa": 80'))
        self.assertEqual(rc, 2)
        self.assertIn("lower", err.lower())

    def test_growth_floor_key_removal_blocked(self):
        rc, _ = run(edit(REPO / GROWTH_REL, old='"fred_icsa": 100, "fred_nfci": 50', new='"fred_icsa": 100'))
        self.assertEqual(rc, 2)

    def test_growth_floor_full_write_blocked(self):
        rc, _ = run({"tool_name": "Write", "tool_input": {"file_path": str(REPO / GROWTH_REL), "content": "{}"}})
        self.assertEqual(rc, 2)


GROWTH_REL = "live_data/config/source_registry_growth_floors.v1.json"
REGISTRY_REL = "model_authority/parameters/parameter_registry.v1.json"
REGISTRY_ABS = REPO / REGISTRY_REL
SCIENCE_PINS = (
    "method_source/index_v1.py",
    "method_source/nowcast_live.py",
    "method_source/forecaster_site.py",
    "model_authority/target_ledger/instrument_onset_target_ledger.v1.json",
)


class SanctionTokenTests(TokenMixin):
    """B-SAFE-2 — sanction-token override for the deny_frozen guard."""

    # Test 1: no token — frozen file still blocked (also covered by DenyFrozenTests).
    def test_no_token_registry_blocked(self):
        rc, err = run(edit(REGISTRY_ABS))
        self.assertEqual(rc, 2)
        self.assertIn("frozen", err.lower())

    # Test 2: token names a DIFFERENT file.
    def test_token_for_different_file_blocked(self):
        self.make_token("B-SCI-1_REGISTRY_DECLARATIONS",
                        "method_source/index_v1.py", _now() + timedelta(hours=1))
        rc, _ = run(edit(REGISTRY_ABS))
        self.assertEqual(rc, 2)

    # Test 3: EXPIRED token.
    def test_expired_token_blocked(self):
        self.make_token("B-SCI-1_REGISTRY_DECLARATIONS",
                        REGISTRY_REL, _now() - timedelta(hours=1))
        rc, _ = run(edit(REGISTRY_ABS))
        self.assertEqual(rc, 2)

    # Test 4: valid, matching, unexpired token — allowed.
    def test_valid_token_allows(self):
        self.make_token("B-SCI-1_REGISTRY_DECLARATIONS",
                        REGISTRY_REL, _now() + timedelta(hours=1))
        rc, err = run(edit(REGISTRY_ABS))
        self.assertEqual(rc, 0, err)

    # Test 5: token removal restores the block.
    def test_token_removal_restores_block(self):
        p = self.make_token("B-SCI-1_REGISTRY_DECLARATIONS",
                            REGISTRY_REL, _now() + timedelta(hours=1))
        self.assertEqual(run(edit(REGISTRY_ABS))[0], 0)
        p.unlink()
        self.assertEqual(run(edit(REGISTRY_ABS))[0], 2)

    # Test 7: the four true science pins stay blocked when NO token grants them,
    # even while a valid token unlocks a DIFFERENT frozen file.
    def test_science_pins_blocked_without_their_token(self):
        self.make_token("B-SCI-1_REGISTRY_DECLARATIONS",
                        REGISTRY_REL, _now() + timedelta(hours=1))
        for rel in SCIENCE_PINS:
            rc, _ = run(edit(REPO / rel))
            self.assertEqual(rc, 2, rel)

    # Malformed token never unlocks (fail-closed).
    def test_malformed_token_blocked(self):
        p = SANCTIONS / "UNFREEZE.B-BAD.json"
        p.write_text("{ not json", encoding="utf-8")
        self._created.append(p)
        rc, _ = run(edit(REGISTRY_ABS))
        self.assertEqual(rc, 2)

    # Token creation is allowed but logged loudly (director authors tokens).
    def test_token_creation_logged_and_allowed(self):
        ev = {"tool_name": "Write", "tool_input": {
            "file_path": str(SANCTIONS / "UNFREEZE.B-SCI-1_REGISTRY_DECLARATIONS.json"),
            "content": "{}"}}
        rc, err = run(ev)
        self.assertEqual(rc, 0)
        self.assertIn("token", err.lower())


class DoctorStaleTokenTests(TokenMixin):
    # Test 6: bh doctor's sanction check fails on a stale token.
    def test_doctor_check_fails_on_stale_token(self):
        from bh import doctor, sanctions
        self.make_token("B-OLD", REGISTRY_REL, _now() - timedelta(hours=2))
        stale = sanctions.stale_tokens(REPO)
        self.assertTrue(stale)
        name, passed, _ = doctor._check_sanctions()
        self.assertEqual(name, "sanctions")
        self.assertFalse(passed)

    def test_doctor_check_ok_when_token_fresh(self):
        from bh import doctor
        self.make_token("B-FRESH", REGISTRY_REL, _now() + timedelta(hours=2))
        _, passed, _ = doctor._check_sanctions()
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
