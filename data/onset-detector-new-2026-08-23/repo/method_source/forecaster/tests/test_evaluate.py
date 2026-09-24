import datetime as dt
import unittest

from forecaster.evaluate import evaluate_candidate
from forecaster.targets import Episode


class EvaluationTests(unittest.TestCase):
    def test_accounts_for_caught_episode_and_late_alert(self):
        episode = Episode(
            "2001-03/2001-11",
            "2001-03",
            dt.date(2001, 3, 1),
            dt.date(2001, 11, 30),
            None,
        )
        rows = [
            {
                "issue_date": "2000-05-21",
                "probability": 0.8,
                "threshold": 0.3,
                "label": 1,
                "target_episode": episode.episode_id,
                "training_start": "1980-01-21",
                "training_end": "2000-03-21",
                "training_rows": 200,
                "training_positive_episodes": ["a", "b", "c"],
            },
            {
                "issue_date": "2000-06-21",
                "probability": 0.1,
                "threshold": 0.3,
                "label": 1,
                "target_episode": episode.episode_id,
            },
            {
                "issue_date": "2000-12-21",
                "probability": 0.1,
                "threshold": 0.3,
                "label": 1,
                "target_episode": episode.episode_id,
            },
            {
                "issue_date": "2001-04-21",
                "probability": 0.8,
                "threshold": 0.3,
                "label": 0,
                "target_episode": "",
            },
            {
                "issue_date": "2001-05-21",
                "probability": 0.1,
                "threshold": 0.3,
                "label": 0,
                "target_episode": "",
            },
        ]
        score = evaluate_candidate(
            rows, [episode], 12, dt.date(2002, 12, 31), seed=3
        )
        self.assertEqual(score["episode_metrics"]["caught_episode_count"], 1)
        self.assertEqual(score["episode_metrics"]["false_alarm_episode_count"], 1)
        self.assertEqual(score["episodes"][0]["status"], "caught")
        self.assertTrue(score["false_alarms"][0]["late_nowcast_or_detection"])
        self.assertFalse(score["deployment_eligible"])

    def test_empty_outer_predictions_are_unestablished(self):
        score = evaluate_candidate([], [], 12, dt.date(2026, 6, 30))
        self.assertEqual(score["status"], "unestablished_no_outer_predictions")
        self.assertFalse(score["joint_gate_pass"])


if __name__ == "__main__":
    unittest.main()
