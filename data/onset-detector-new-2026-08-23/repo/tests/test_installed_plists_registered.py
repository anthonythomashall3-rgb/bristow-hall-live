"""B-SAFE-1 §1.4 — installed-plist drift closure.

The runner already asserts that the repo *source* dir (live_data/launchd/)
carries only registered agents. This closes the other half: every launchd plist
actually INSTALLED under ~/Library/LaunchAgents/ that TARGETS the V2 repo (i.e.
can write into this store) must be a registered AGENT_LABELS agent. A
newly-dropped second writer into the store fails the suite closed.

The discriminator is the plist's target path, never its label string. Several
predecessor jobs (monitor-v2, p4-v2, p4-v2-sync, p4-v2-watchdog) carry a "v2"
token but run under ~/.local/share/recession-monitor/ or ~/Projects/ — the
predecessor tree — and are deliberately NOT in scope (B-SAFE-1 owner decision:
this batch owns V2, not the predecessor).

RED reproduction: the two plists quarantined by B-SAFE-1 are preserved byte-for
-byte under _quarantined_plists/. Pointing the same checker at that directory
reproduces the pre-quarantine violation (vaultbackup targeted the V2 repo and
was never a registered agent), so the failure path is a permanent regression
guard, not a one-time observation.
"""

from __future__ import absolute_import

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from live_data.rmv2_admission import runner  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
QUARANTINE = REPO / "_quarantined_plists"


class InstalledPlistRegistrationTests(unittest.TestCase):
    def test_live_installed_v2_plists_are_all_registered(self):
        """GREEN drift alarm against the real host. On a machine with no
        ~/Library/LaunchAgents (CI) the scan is empty and this passes trivially;
        on the operator host it fails closed if any V2-repo-targeting writer is
        installed that is not a registered agent."""
        covered = runner.assert_installed_v2_plists_registered()
        self.assertTrue(
            covered.issubset(set(runner.AGENT_LABELS)),
            "installed V2-repo plists escaped AGENT_LABELS: %s"
            % sorted(covered - set(runner.AGENT_LABELS)),
        )

    def test_quarantined_v2_plists_reproduce_the_violation(self):
        """RED reproduction: the preserved quarantined copies still target the
        V2 repo and are not registered, so the checker must raise and name the
        vault-backup writer explicitly."""
        self.assertTrue(QUARANTINE.is_dir(), "quarantine dir missing")
        with self.assertRaises(runner.AdmissionContractError) as ctx:
            runner.assert_installed_v2_plists_registered(QUARANTINE)
        self.assertIn("com.recessionmonitor.v2.vaultbackup", str(ctx.exception))

    def test_discriminator_is_target_path_not_label(self):
        """A predecessor job with a "v2" label but a predecessor script path is
        out of scope; only a plist that references the V2 repo is in scope."""
        predecessor_v2 = {
            "Label": "com.anthonyhall.recessionmonitor.p4-v2",
            "ProgramArguments": [
                "/bin/zsh",
                "/Users/anthonyhall/.local/share/recession-monitor/p4/p4_unattended_run_v2.sh",
            ],
        }
        repo_writer = {
            "Label": "com.example.rogue",
            "ProgramArguments": ["/bin/sh", str(REPO / "live_data/ops/x.sh")],
        }
        self.assertFalse(runner.plist_targets_v2_repo(predecessor_v2))
        self.assertTrue(runner.plist_targets_v2_repo(repo_writer))


if __name__ == "__main__":
    unittest.main()
