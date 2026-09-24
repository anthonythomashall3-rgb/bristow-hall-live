import datetime as dt
from pathlib import Path
import tempfile
import unittest

from forecaster.schema import SourceSpec, VintageClass
from forecaster.vintage import DataUnavailable, SnapshotVintageStore


UTC = dt.timezone.utc


def write_snapshot(root: Path, series: str, vintage: str, rows):
    body = "observation_date,value\n" + "".join(f"{day},{value}\n" for day, value in rows)
    (root / f"{series}_{vintage}.csv").write_text(body)


class VintageStoreTests(unittest.TestCase):
    def test_selects_latest_nonfuture_snapshot_and_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_snapshot(root, "INDPRO", "2020-01-20", [("2019-11-01", "100.0")])
            write_snapshot(
                root,
                "INDPRO",
                "2020-02-20",
                [("2019-11-01", "99.5"), ("2019-12-01", "100.2")],
            )
            store = SnapshotVintageStore(root)
            issue = dt.datetime(2020, 2, 20, 23, 59, tzinfo=UTC)
            value = store.latest_observation("INDPRO", issue)
            self.assertEqual(value.vintage_id, "2020-01-20")
            self.assertEqual(value.value, 100.0)
            issue_after = dt.datetime(2020, 2, 21, 0, 0, tzinfo=UTC)
            revised = store.latest_observation("INDPRO", issue_after)
            self.assertEqual(revised.vintage_id, "2020-02-20")
            self.assertEqual(revised.reference_date, dt.date(2019, 12, 1))

    def test_future_feature_canary_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_snapshot(root, "CANARY", "2030-01-20", [("2029-12-01", "999")])
            store = SnapshotVintageStore(root)
            with self.assertRaises(DataUnavailable):
                store.latest_observation(
                    "CANARY", dt.datetime(2029, 12, 31, 23, 59, tzinfo=UTC)
                )

    def test_strict_mode_rejects_current_vintage_fallback(self):
        spec = SourceSpec(
            series_id="X",
            provider="fixture",
            title="fixture",
            frequency="monthly",
            units="index",
            seasonal_adjustment="none",
            vintage_class=VintageClass.CURRENT_VINTAGE_LAGGED,
            lag_days=30,
            source_url="https://example.invalid/X",
            license_note="fixture only",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "X.csv"
            current.write_text("DATE,X\n2020-01-01,1.0\n")
            store = SnapshotVintageStore(root / "vintages", current_root=root)
            issue = dt.datetime(2020, 2, 15, tzinfo=UTC)
            with self.assertRaises(DataUnavailable):
                store.from_current(spec, issue, strict=True)
            value = store.from_current(spec, issue, strict=False)
            self.assertEqual(value.vintage_class, VintageClass.CURRENT_VINTAGE_LAGGED)


if __name__ == "__main__":
    unittest.main()
