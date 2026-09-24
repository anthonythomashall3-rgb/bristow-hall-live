import datetime as dt
from pathlib import Path
import tempfile
import unittest

from forecaster.audit import assess_source_file, future_canary_is_rejected
from forecaster.stress import (
    exclude_episode,
    leave_one_episode_influence,
    placebo_episodes,
    shuffled_auc_distribution,
)
from forecaster.targets import Episode


class AuditTests(unittest.TestCase):
    def test_future_feature_canary_is_rejected(self):
        self.assertTrue(future_canary_is_rejected())

    def test_source_faults_are_visible_not_low_risk(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = assess_source_file(root / "missing.csv", dt.datetime.now(dt.timezone.utc))
            self.assertEqual(missing["status"], "missing")
            corrupt_path = root / "corrupt.csv"
            corrupt_path.write_text("<html>blocked</html>")
            corrupt = assess_source_file(corrupt_path, dt.datetime.now(dt.timezone.utc))
            self.assertEqual(corrupt["status"], "corrupt")
            valid_path = root / "valid.csv"
            valid_path.write_text("DATE,X\n2020-01-01,1.0\n")
            stale = assess_source_file(
                valid_path,
                dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=100),
                maximum_age_days=1,
                maximum_reference_age_days=1,
            )
            self.assertEqual(stale["status"], "stale")
            self.assertEqual(stale["latest_reference_date"], "2020-01-01")

    def test_shuffling_destroys_perfect_discrimination_on_average(self):
        labels = [0] * 20 + [1] * 5
        probabilities = [index / 24 for index in range(25)]
        values = shuffled_auc_distribution(labels, probabilities, permutations=300, seed=4)
        self.assertGreater(sum(values) / len(values), 0.43)
        self.assertLess(sum(values) / len(values), 0.57)

    def test_placebo_and_pandemic_exclusion_preserve_identifiers(self):
        episodes = [
            Episode("gfc", "2007-12", dt.date(2007, 12, 1), dt.date(2009, 6, 30), None),
            Episode("pandemic", "2020-02", dt.date(2020, 2, 1), dt.date(2020, 4, 30), None),
        ]
        placebo = placebo_episodes(episodes, shift_days=400)
        self.assertEqual([item.episode_id for item in placebo], ["placebo-gfc", "placebo-pandemic"])
        without = exclude_episode(episodes, "pandemic")
        self.assertEqual([item.episode_id for item in without], ["gfc"])

    def test_leave_one_episode_influence_reports_every_episode(self):
        values = {"r1": 1.0, "r2": 1.0, "r3": 0.0}
        result = leave_one_episode_influence(values)
        self.assertEqual(set(result), set(values))
        self.assertAlmostEqual(result["r3"], 1.0)


if __name__ == "__main__":
    unittest.main()
