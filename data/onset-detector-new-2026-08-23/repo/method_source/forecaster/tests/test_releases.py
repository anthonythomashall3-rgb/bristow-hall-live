import datetime as dt
import unittest

from forecaster.releases import ReleaseEvent, is_available


UTC = dt.timezone.utc


class ReleaseBoundaryTests(unittest.TestCase):
    def test_value_changes_availability_only_at_release_instant(self):
        event = ReleaseEvent(
            source="BLS",
            series_id="PAYEMS",
            reference_date=dt.date(2025, 12, 1),
            released_at=dt.datetime(2026, 1, 9, 13, 30, tzinfo=UTC),
            release_id="empsit-2026-01",
        )
        self.assertFalse(
            is_available(event, dt.datetime(2026, 1, 9, 13, 29, 59, tzinfo=UTC))
        )
        self.assertTrue(
            is_available(event, dt.datetime(2026, 1, 9, 13, 30, tzinfo=UTC))
        )

    def test_naive_issue_timestamp_is_rejected(self):
        event = ReleaseEvent(
            source="BLS",
            series_id="PAYEMS",
            reference_date=dt.date(2025, 12, 1),
            released_at=dt.datetime(2026, 1, 9, 13, 30, tzinfo=UTC),
            release_id="empsit-2026-01",
        )
        with self.assertRaises(ValueError):
            is_available(event, dt.datetime(2026, 1, 9, 13, 30))


if __name__ == "__main__":
    unittest.main()
