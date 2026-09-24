import datetime as dt
import tempfile
import unittest
from pathlib import Path

from forecaster.targets import Episode, episodes_from_usrecd, horizon_end, onset_label


class TargetTests(unittest.TestCase):
    def setUp(self):
        self.episodes = [
            Episode(
                episode_id="1990-91",
                peak_month="1990-07",
                onset=dt.date(1990, 7, 1),
                trough_end=dt.date(1991, 3, 31),
                announced_at=dt.datetime(
                    1991, 4, 25, 16, tzinfo=dt.timezone.utc
                ),
            )
        ]

    def test_pre_onset_cutoff_is_first_day_of_peak_month(self):
        self.assertEqual(
            onset_label(
                dt.date(1990, 6, 30), 1, self.episodes, dt.date(1992, 12, 31)
            ),
            1,
        )
        self.assertIsNone(
            onset_label(
                dt.date(1990, 7, 1), 1, self.episodes, dt.date(1992, 12, 31)
            )
        )

    def test_right_censored_horizon_is_unscored(self):
        self.assertIsNone(
            onset_label(
                dt.date(1992, 7, 31), 12, self.episodes, dt.date(1992, 12, 31)
            )
        )

    def test_calendar_month_addition_clips_day(self):
        self.assertEqual(horizon_end(dt.date(2024, 1, 31), 1), dt.date(2024, 2, 29))
        self.assertEqual(horizon_end(dt.date(2025, 1, 31), 1), dt.date(2025, 2, 28))

    def test_daily_state_transition_maps_to_nber_peak_month(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "USRECD.csv"
            path.write_text(
                "observation_date,USRECD\n"
                "2001-03-31,0\n"
                "2001-04-01,1\n"
                "2001-11-30,1\n"
                "2001-12-01,0\n",
                encoding="utf-8",
            )
            episodes = episodes_from_usrecd(path)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].peak_month, "2001-03")
        self.assertEqual(episodes[0].onset, dt.date(2001, 3, 1))
        self.assertEqual(episodes[0].trough_end, dt.date(2001, 11, 30))

    def test_three_month_recovery_exclusion_is_unscored(self):
        self.assertIsNone(
            onset_label(
                dt.date(1991, 5, 1), 12, self.episodes, dt.date(1993, 1, 1),
                recovery_exclusion_months=3,
            )
        )
        self.assertEqual(
            onset_label(
                dt.date(1991, 7, 1), 12, self.episodes, dt.date(1993, 1, 1),
                recovery_exclusion_months=3,
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
