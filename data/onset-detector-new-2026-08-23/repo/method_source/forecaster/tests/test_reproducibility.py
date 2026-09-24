import datetime as dt
import unittest

import numpy as np

from forecaster.backtest import enforce_horizon_coherence, synthetic_walk_forward


class ReproducibilityTests(unittest.TestCase):
    def test_same_seed_and_data_produce_identical_artifact_hash(self):
        issues = [dt.date(1990 + index // 12, index % 12 + 1, 20) for index in range(180)]
        x = np.array(
            [[np.sin(index / 8.0), np.cos(index / 13.0)] for index in range(180)]
        )
        y = np.array([int(index % 60 >= 55) for index in range(180)], dtype=float)
        first = synthetic_walk_forward(issues, x, y, minimum_train=60, seed=9)
        second = synthetic_walk_forward(issues, x, y, minimum_train=60, seed=9)
        self.assertEqual(first["artifact_hash"], second["artifact_hash"])
        self.assertEqual(first["predictions"], second["predictions"])
        self.assertGreater(len(first["predictions"]), 50)

    def test_cumulative_horizon_probabilities_are_projected_non_decreasing(self):
        result = {
            "horizons": {
                "1": {"term_spread_logit": [{"issue_date": "2020-01-20", "probability": 0.2}]},
                "3": {"term_spread_logit": [{"issue_date": "2020-01-20", "probability": 0.1}]},
                "6": {"term_spread_logit": [{"issue_date": "2020-01-20", "probability": 0.4}]},
            }
        }
        enforce_horizon_coherence(result)
        values = [
            result["horizons"][key]["term_spread_logit"][0]["probability"]
            for key in ["1", "3", "6"]
        ]
        self.assertEqual(values, [0.2, 0.2, 0.4])


if __name__ == "__main__":
    unittest.main()
