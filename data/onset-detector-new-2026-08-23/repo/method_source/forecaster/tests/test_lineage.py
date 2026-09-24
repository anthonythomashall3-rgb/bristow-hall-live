import datetime as dt
import unittest

from forecaster.schema import FeatureValue, Observation, VintageClass


UTC = dt.timezone.utc


class LineageTests(unittest.TestCase):
    def test_derived_feature_retains_dependency_hashes(self):
        observation = Observation(
            series_id="T10Y3M",
            reference_date=dt.date(2026, 7, 21),
            value=0.72,
            available_at=dt.datetime(2026, 7, 22, tzinfo=UTC),
            ingested_at=dt.datetime(2026, 7, 22, 1, tzinfo=UTC),
            vintage_id="2026-07-22",
            vintage_class=VintageClass.INVARIANT,
            raw_checksum="a" * 64,
            source_uri="fixture://T10Y3M",
        )
        feature = FeatureValue.derive(
            name="term_spread_10y3m",
            issue_at=dt.datetime(2026, 7, 22, 2, tzinfo=UTC),
            value=observation.value,
            transform="identity",
            observations=[observation],
        )
        self.assertEqual(feature.dependencies, [observation.lineage_hash()])
        self.assertEqual(len(feature.lineage_hash()), 64)
        self.assertLessEqual(observation.available_at, feature.issue_at)

    def test_feature_rejects_future_dependency(self):
        future = Observation(
            series_id="CANARY",
            reference_date=dt.date(2027, 1, 1),
            value=1.0,
            available_at=dt.datetime(2027, 2, 1, tzinfo=UTC),
            ingested_at=dt.datetime(2027, 2, 1, tzinfo=UTC),
            vintage_id="future",
            vintage_class=VintageClass.EXACT_VINTAGE,
            raw_checksum="b" * 64,
            source_uri="fixture://CANARY",
        )
        with self.assertRaises(ValueError):
            FeatureValue.derive(
                name="impossible",
                issue_at=dt.datetime(2027, 1, 1, tzinfo=UTC),
                value=1.0,
                transform="identity",
                observations=[future],
            )


if __name__ == "__main__":
    unittest.main()
