"""B-EXTREAD-DECLARE — the V2 external read-set is DECLARED and LOAD-BEARING.

`FORECASTER_RAW_ROOT` is mandatory at runtime (method_source/forecaster/
runner.py:319-322 raises without it) yet lived nowhere machine-readable in V2
source. This suite pins three things:

1. `live_data/config/external_read_roots.v1.json` exists and each entry carries
   path / required_by (file:line) / purpose / required / provenance.
2. The forecaster RESOLVES `FORECASTER_RAW_ROOT` from that file when the env var
   is unset (env still overrides). The declaration is load-bearing, so it cannot
   silently rot (§1.6: a file nothing depends on rots).
3. `assert_installed_v2_plists_registered()` DERIVES its read-set from that file
   (§1.6 derivation, not a hand-list): against the preserved quarantined plists
   it flags the three predecessor jobs that target the raw read-root
   (refresh / refresh-fast / forecaster-shadow) and does NOT claim the
   predecessor-tree jobs that only touch sibling subtrees (geo/, research/,
   ~/.local/share/recession-monitor/).
"""

from __future__ import absolute_import

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live_data.rmv2_admission import runner  # noqa: E402
from method_source.forecaster import catalog as forecaster_catalog  # noqa: E402
from method_source.forecaster import runner as forecaster_runner  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
QUARANTINE = REPO / "_quarantined_plists"
CONFIG = REPO / "live_data" / "config" / "external_read_roots.v1.json"

# Predecessor-tree jobs whose targets are SIBLINGS of the raw read-root (geo/,
# research/, ~/.local/share/...) — out of the read-set by measurement, must
# never be claimed by the read-root derivation.
OUT_OF_READ_SET = (
    "com.anthonyhall.recessionmonitor.monitor-v2",
    "com.anthonyhall.recessionmonitor.monitor-v2-live-shadow",
    "com.anthonyhall.recessionmonitor.p4",
    "com.anthonyhall.recessionmonitor.p4-v2",
    "com.anthonyhall.recessionmonitor.p4-v2-sync",
    "com.anthonyhall.recessionmonitor.p4-v2-watchdog",
    "com.anthonyhall.recessionmonitor.p5",
    "com.anthonyhall.recessionmonitor.p5-sync",
    "com.anthonyhall.recessionmonitor.p5-watchdog",
    "com.anthonyhall.recessionmonitor.research-shadow",
    "com.anthonyhall.recessionmonitor.site-smoke",
)

READ_ROOT_TARGETS = (
    "com.bristowhall.refresh",
    "com.bristowhall.refresh-fast",
    "com.bristowhall.forecaster-shadow",
)


def _load_config():
    import json

    return json.loads(CONFIG.read_text(encoding="utf-8"))


class DeclaredReadSetSchemaTests(unittest.TestCase):
    def test_config_exists_and_entries_are_fully_provenanced(self):
        self.assertTrue(CONFIG.is_file(), "external_read_roots.v1.json missing")
        data = _load_config()
        roots = data.get("roots")
        self.assertIsInstance(roots, list)
        self.assertTrue(roots, "no declared read roots")
        for entry in roots:
            for field in ("path", "required_by", "purpose", "required", "provenance"):
                self.assertIn(field, entry, "missing %s in %r" % (field, entry))
            self.assertIsInstance(entry["required"], bool)
            self.assertTrue(entry["required_by"], "required_by must cite a code site")
            # every required_by is a file:line citation, never prose
            sites = entry["required_by"]
            if isinstance(sites, str):
                sites = [sites]
            for site in sites:
                self.assertIn(":", site, "required_by must be file:line: %r" % site)

    def test_forecaster_raw_root_is_declared(self):
        entries = [
            e for e in _load_config()["roots"]
            if e.get("env_var") == "FORECASTER_RAW_ROOT"
        ]
        self.assertEqual(len(entries), 1, "FORECASTER_RAW_ROOT must be declared once")


class ForecasterResolvesFromDeclarationTests(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("FORECASTER_RAW_ROOT", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["FORECASTER_RAW_ROOT"] = self._saved
        else:
            os.environ.pop("FORECASTER_RAW_ROOT", None)

    def _declared_path(self):
        entry = next(
            e for e in _load_config()["roots"]
            if e.get("env_var") == "FORECASTER_RAW_ROOT"
        )
        return Path(entry["path"]).resolve()

    def test_catalog_raw_root_resolves_declared_when_env_unset(self):
        self.assertEqual(forecaster_catalog.raw_root(), self._declared_path())

    def test_runner_resolves_declared_instead_of_raising(self):
        # Previously raised 'FORECASTER_RAW_ROOT is required'; now the repo can
        # NAME its mandatory input, so resolution succeeds from the declaration.
        self.assertEqual(
            forecaster_runner.raw_root_from_environment(), self._declared_path()
        )

    def test_env_still_overrides_declaration(self):
        os.environ["FORECASTER_RAW_ROOT"] = "/tmp/override_raw"
        self.assertEqual(
            forecaster_catalog.raw_root(), Path("/tmp/override_raw").resolve()
        )


class PlistCheckerDerivesReadSetTests(unittest.TestCase):
    def test_read_root_jobs_flagged_predecessor_tree_jobs_not(self):
        with self.assertRaises(runner.AdmissionContractError) as ctx:
            runner.assert_installed_v2_plists_registered(QUARANTINE)
        message = str(ctx.exception)
        for label in READ_ROOT_TARGETS:
            self.assertIn(label, message, "read-root writer not flagged: %s" % label)
        for label in OUT_OF_READ_SET:
            self.assertNotIn(
                label, message, "sibling-subtree job wrongly claimed: %s" % label
            )

    def test_derivation_reads_the_config_not_a_hardcode(self):
        # With an EMPTY read-set the three raw-root writers must drop out — proves
        # the flag comes FROM the declared file, not a hand-list in the checker.
        scoped = runner.installed_v2_scoped_labels(QUARANTINE, read_roots=[])
        for label in READ_ROOT_TARGETS:
            self.assertNotIn(label, scoped)
        # And with the declared read-set they reappear.
        scoped_declared = runner.installed_v2_scoped_labels(QUARANTINE)
        for label in READ_ROOT_TARGETS:
            self.assertIn(label, scoped_declared)

    def test_comparability_is_component_wise_not_substring(self):
        root = "/Users/anthonyhall/Projects/RecessionMonitor/raw"
        # ancestor of the read-root -> a job there can write into it
        self.assertTrue(
            runner._paths_comparable("/Users/anthonyhall/Projects/RecessionMonitor", root)
        )
        # descendant -> writes inside it
        self.assertTrue(runner._paths_comparable(root + "/vintages/x.csv", root))
        # sibling subtree -> cannot
        self.assertFalse(
            runner._paths_comparable(
                "/Users/anthonyhall/Projects/RecessionMonitor/geo/series.json", root
            )
        )
        # a bare string prefix must NOT match (substring trap)
        self.assertFalse(
            runner._paths_comparable(
                "/Users/anthonyhall/Projects/RecessionMonitor-evil/raw", root
            )
        )


if __name__ == "__main__":
    unittest.main()
