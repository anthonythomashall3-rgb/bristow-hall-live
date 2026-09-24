import datetime as dt
import unittest

from forecaster.backtest import eligible_training_indices, expanding_inner_splits


class FoldTests(unittest.TestCase):
    def test_horizon_and_embargo_are_closed_before_outer_origin(self):
        issues = [dt.date(2000, month, 20) for month in range(1, 13)]
        origin = dt.date(2000, 12, 20)
        indices = eligible_training_indices(issues, origin, horizon_months=3, embargo_days=21)
        for index in indices:
            closed = issues[index]
            # The function under test exposes its exact closure boundary.
            self.assertLessEqual(
                eligible_training_indices.outcome_closed_at(
                    closed, horizon_months=3, embargo_days=21
                ),
                origin,
            )
        self.assertNotIn(10, indices)
        self.assertNotIn(11, indices)

    def test_inner_splits_are_expanding_and_nonoverlapping(self):
        splits = expanding_inner_splits(100, minimum_train=40, folds=4)
        self.assertGreaterEqual(len(splits), 2)
        previous_train = 0
        previous_validation_end = 0
        for train, validation in splits:
            self.assertEqual(train, list(range(len(train))))
            self.assertGreater(len(train), previous_train)
            self.assertTrue(validation)
            self.assertGreaterEqual(validation[0], len(train))
            self.assertGreaterEqual(validation[0], previous_validation_end)
            self.assertTrue(set(train).isdisjoint(validation))
            previous_train = len(train)
            previous_validation_end = validation[-1] + 1


if __name__ == "__main__":
    unittest.main()
