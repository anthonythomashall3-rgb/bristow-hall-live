from __future__ import absolute_import

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "live_data" / "scripts" / "feed_factory.command"
README = PROJECT_ROOT / "live_data" / "feed_factory" / "README.md"
PYTHON_38 = "/Users/anthonyhall/.pyenv/versions/3.8.10/bin/python3"
PYTHON_314 = "/opt/homebrew/opt/python@3.14/bin/python3.14"


class FeedFactoryLauncherTests(unittest.TestCase):
    def launcher_text(self):
        return LAUNCHER.read_text(encoding="utf-8")

    def run_launcher(self, *arguments):
        with tempfile.TemporaryDirectory() as temp_dir:
            return subprocess.run(
                [str(LAUNCHER)] + list(arguments),
                cwd=temp_dir,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                # Re-baselined 2026-08-04 (B2L): F1's content-addressed
                # binding-attestation cache turned the no-arg inventory into an
                # O(sources) attested scan (no whole-store re-verification), so at
                # 190 sources it now completes in a MEASURED 1.62s raw / 1.89s under
                # pytest — down from the pre-F1 O(store) ~44s that justified the old
                # 120s ceiling. Pin tightened to 30s: ~15x headroom over the measured
                # ~2s path for cold-cache/load/source-count growth, while staying well
                # below the pre-F1 O(store) regime so a reintroduced whole-store
                # re-verification regression is caught rather than hidden. This is a
                # performance guard, not a correctness assertion — the
                # returncode/schema/status checks below are unchanged.
                timeout=30,
            )

    def test_launcher_is_executable_and_shell_syntax_is_valid(self):
        self.assertTrue(LAUNCHER.is_file())
        self.assertTrue(LAUNCHER.stat().st_mode & stat.S_IXUSR)
        result = subprocess.run(
            ["/bin/bash", "-n", str(LAUNCHER)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_launcher_resolves_project_root_and_prefers_pinned_runtimes(self):
        text = self.launcher_text()
        self.assertIn('BASH_SOURCE[0]', text)
        self.assertIn('"${SCRIPT_DIR}/../.."', text)
        self.assertNotIn(str(PROJECT_ROOT), text)
        self.assertIn(PYTHON_38, text)
        self.assertIn(PYTHON_314, text)
        self.assertLess(text.index(PYTHON_38), text.index(PYTHON_314))
        self.assertNotIn("local.env", text)
        self.assertNotIn("API_KEY=", text)

    def test_no_argument_run_is_safe_inventory_from_any_working_directory(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["schema_version"],
            "recession-monitor-v2.feed-factory-inventory.v1",
        )
        self.assertEqual(payload["scientific_effect"], "none")
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(
            Path(payload["factory_root"]).resolve(),
            (PROJECT_ROOT / "live_data" / "feed_factory").resolve(),
        )

    def test_help_documents_all_commands_without_running_a_factory_action(self):
        result = self.run_launcher("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("inventory", "probe", "compile", "prepare", "apply"):
            self.assertIn(command, result.stdout)
        self.assertIn("does not apply", result.stdout.lower())
        self.assertEqual(result.stderr, "")

    def test_unknown_command_fails_closed(self):
        result = self.run_launcher("activate-everything")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported Feed Factory command", result.stderr)

    def test_launcher_dispatch_contract_requires_explicit_apply(self):
        text = self.launcher_text()
        self.assertIn('COMMAND="${1:-inventory}"', text)
        for command in ("inventory", "probe", "compile", "prepare", "apply"):
            self.assertIn("%s)" % command, text)
        self.assertIn(
            'feed-factory "${COMMAND}" "$@"',
            text,
        )
        self.assertNotIn("prepare apply", text)
        self.assertNotIn("probe apply", text)

    def test_operator_readme_keeps_one_factory_and_one_authority_boundary(self):
        text = README.read_text(encoding="utf-8")
        required_phrases = (
            "one Feed Factory",
            "parallel",
            "one registry",
            "one store",
            "one publication barrier",
            "no rival API",
            "CANDIDATE_NOT_ACTIVE",
            "scientific admission",
            "explicit",
            "local.env",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, text)
        for command in ("inventory", "probe", "compile", "prepare", "apply"):
            self.assertIn("feed_factory.command %s" % command, text)


if __name__ == "__main__":
    unittest.main()
