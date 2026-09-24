import math
import unittest

from forecaster.metrics import (
    binary_metrics,
    brier_score,
    calibration_intercept_slope,
    expected_calibration_error,
    log_loss,
    pr_auc,
    roc_auc,
)
from forecaster.uncertainty import bootstrap_interval


class MetricTests(unittest.TestCase):
    def test_exact_discrimination_and_proper_scores(self):
        labels = [0, 0, 1, 1]
        probabilities = [0.1, 0.2, 0.8, 0.9]
        self.assertAlmostEqual(roc_auc(labels, probabilities), 1.0)
        self.assertAlmostEqual(pr_auc(labels, probabilities), 1.0)
        self.assertAlmostEqual(brier_score(labels, probabilities), 0.025)
        self.assertTrue(math.isfinite(log_loss(labels, probabilities)))

    def test_binary_metrics_penalize_always_on_warning(self):
        result = binary_metrics([0, 0, 0, 1], [1, 1, 1, 1])
        self.assertAlmostEqual(result["balanced_accuracy"], 0.5)
        self.assertEqual(result["specificity"], 0.0)
        self.assertEqual(result["mcc"], 0.0)

    def test_ci_is_refused_below_eight_episode_units(self):
        self.assertIsNone(bootstrap_interval([1, 1, 0], resamples=100, seed=7))
        interval = bootstrap_interval(
            [1, 1, 1, 1, 1, 1, 1, 0], resamples=200, seed=7
        )
        self.assertIsNotNone(interval)
        self.assertLessEqual(interval[0], 0.875)
        self.assertGreaterEqual(interval[1], 0.875)

    def test_calibration_diagnostics_are_finite(self):
        labels = [0, 0, 0, 1, 1, 1]
        probabilities = [0.05, 0.15, 0.3, 0.7, 0.85, 0.95]
        calibration = calibration_intercept_slope(labels, probabilities)
        self.assertTrue(math.isfinite(calibration["intercept"]))
        self.assertTrue(math.isfinite(calibration["slope"]))
        self.assertLess(expected_calibration_error(labels, probabilities), 0.25)


if __name__ == "__main__":
    unittest.main()
