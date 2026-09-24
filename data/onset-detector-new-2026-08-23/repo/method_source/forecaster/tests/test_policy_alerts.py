import datetime as dt
import unittest

from forecaster.alerts import PolicyPoint, build_policy_alert_episodes


UTC = dt.timezone.utc


class PolicyAlertTests(unittest.TestCase):
    def test_uses_each_points_training_only_threshold_and_full_interval(self):
        points = [
            PolicyPoint(dt.datetime(2020, 1, 21, tzinfo=UTC), 0.19, 0.20),
            PolicyPoint(dt.datetime(2020, 2, 21, tzinfo=UTC), 0.21, 0.20),
            PolicyPoint(dt.datetime(2020, 3, 21, tzinfo=UTC), 0.17, 0.25),
        ]
        alerts = build_policy_alert_episodes(points)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].start.date(), dt.date(2020, 2, 21))
        self.assertEqual(alerts[0].end.date(), dt.date(2020, 3, 20))
        self.assertEqual(alerts[0].duration_days, 29)

    def test_rejects_invalid_threshold(self):
        with self.assertRaises(ValueError):
            PolicyPoint(dt.datetime(2020, 1, 21, tzinfo=UTC), 0.2, 0.0)


if __name__ == "__main__":
    unittest.main()
