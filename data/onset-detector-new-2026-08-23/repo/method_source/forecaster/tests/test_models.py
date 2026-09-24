import unittest

import numpy as np

from forecaster.backtest import fit_family_bundle
from forecaster.models import PlattCalibrator, fit_logistic


class ModelTests(unittest.TestCase):
    def test_ridge_logistic_learns_monotonic_fixture(self):
        x = np.arange(-3.0, 3.1, 0.2).reshape(-1, 1)
        y = (x[:, 0] > 0).astype(float)
        model = fit_logistic(x, y, l2=1.0, positive_weight=1.0)
        probabilities = model.predict_proba(x)
        self.assertTrue(np.all(probabilities >= 0.0))
        self.assertTrue(np.all(probabilities <= 1.0))
        self.assertGreater(probabilities[-1], probabilities[0])
        self.assertGreater(model.coefficients[0], 0.0)

    def test_scaler_is_fit_only_to_training_values(self):
        x = np.array([[0.0], [1.0], [2.0], [1000.0]])
        y = np.array([0.0, 0.0, 1.0])
        model = fit_logistic(x[:3], y, l2=1.0, positive_weight=1.0)
        self.assertAlmostEqual(model.means[0], 1.0)
        self.assertLess(model.predict_proba(x[3:])[0], 1.0)

    def test_platt_calibrator_returns_bounded_probabilities(self):
        raw = np.array([0.1, 0.2, 0.7, 0.9])
        labels = np.array([0.0, 0.0, 1.0, 1.0])
        calibrator = PlattCalibrator.fit(raw, labels)
        values = calibrator.transform(raw)
        self.assertTrue(np.all(values > 0.0))
        self.assertTrue(np.all(values < 1.0))
        self.assertGreater(values[-1], values[0])

    def test_nested_family_bundle_is_deterministic(self):
        x = np.array(
            [[np.sin(index / 5.0), np.cos(index / 9.0)] for index in range(100)]
        )
        y = np.array([int(index % 30 >= 25) for index in range(100)], dtype=float)
        first = fit_family_bundle("ridge_channel_logit", x, y)
        second = fit_family_bundle("ridge_channel_logit", x, y)
        self.assertEqual(first.spec_digest, second.spec_digest)
        self.assertEqual(first.threshold, second.threshold)
        self.assertAlmostEqual(first.predict(x[-1]), second.predict(x[-1]), places=12)


if __name__ == "__main__":
    unittest.main()
