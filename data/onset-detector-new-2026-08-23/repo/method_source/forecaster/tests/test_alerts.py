import datetime as dt
import unittest

from forecaster.alerts import ForecastPoint, build_alert_episodes, match_alerts
from forecaster.targets import Episode


UTC = dt.timezone.utc


def point(day, probability):
    return ForecastPoint(dt.datetime.fromisoformat(day).replace(tzinfo=UTC), probability)


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.recessions = [
            Episode("r1", "2001-03", dt.date(2001, 3, 1), dt.date(2001, 11, 30), None),
            Episode("r2", "2007-12", dt.date(2007, 12, 1), dt.date(2009, 6, 30), None),
        ]

    def test_continuous_warning_creates_one_episode(self):
        alerts = build_alert_episodes(
            [point("2000-12-20", 0.4), point("2001-01-20", 0.5),
             point("2001-02-20", 0.35), point("2001-03-20", 0.1)],
            enter_threshold=0.3,
            exit_multiplier=0.7,
        )
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].start.date(), dt.date(2000, 12, 20))
        self.assertEqual(alerts[0].peak_probability, 0.5)

    def test_one_alert_cannot_credit_two_recessions(self):
        alerts = build_alert_episodes(
            [point("2000-01-20", 0.9), point("2010-01-20", 0.9)],
            enter_threshold=0.3,
        )
        result = match_alerts(alerts, self.recessions, horizon_months=24)
        self.assertLessEqual(len(result.matches), 1)
        self.assertGreaterEqual(len(result.missed), 1)

    def test_too_early_alert_is_false_alarm(self):
        alerts = build_alert_episodes(
            [point("1995-01-20", 0.8), point("1995-02-20", 0.0)],
            enter_threshold=0.3,
        )
        result = match_alerts(alerts, self.recessions, horizon_months=24)
        self.assertEqual(len(result.false_alarms), 1)
        self.assertEqual(len(result.matches), 0)

    def test_post_onset_alert_is_late_not_caught(self):
        alerts = build_alert_episodes(
            [point("2001-04-20", 0.8), point("2001-05-20", 0.0)],
            enter_threshold=0.3,
        )
        result = match_alerts(alerts, self.recessions[:1], horizon_months=12)
        self.assertEqual(len(result.matches), 0)
        self.assertEqual([item.episode_id for item in result.late], ["r1"])


if __name__ == "__main__":
    unittest.main()
