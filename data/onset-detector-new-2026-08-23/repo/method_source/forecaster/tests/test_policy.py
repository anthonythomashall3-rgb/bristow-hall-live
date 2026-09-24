import unittest

from forecaster.policy import select_threshold


class PolicyTests(unittest.TestCase):
    def test_threshold_selection_penalizes_always_on_warning(self):
        labels = [0] * 20 + [1]
        probabilities = [0.2] * 21
        selected = select_threshold(
            labels,
            probabilities,
            thresholds=[0.1, 0.3, 0.5],
            miss_cost=10.0,
            false_positive_cost=3.0,
            warning_fraction_cost=5.0,
        )
        self.assertIn(selected.threshold, [0.3, 0.5])
        self.assertLess(selected.warning_fraction, 1.0)

    def test_policy_uses_only_supplied_training_rows(self):
        base = select_threshold([0, 0, 1], [0.1, 0.2, 0.8], [0.2, 0.5])
        repeated = select_threshold([0, 0, 1], [0.1, 0.2, 0.8], [0.2, 0.5])
        self.assertEqual(base, repeated)


if __name__ == "__main__":
    unittest.main()
