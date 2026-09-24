import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from contrib.free_official_sources_v1 import collector


FHFA = (
    b"hpi_type,hpi_flavor,frequency,level,place_name,place_id,yr,period,"
    b"index_nsa,index_sa,rstderr,note\r\n"
    b"traditional,purchase-only,monthly,USA or Census Division,United States,"
    b"USA,2024,1,200.10,201.20,,\r\n"
    b"traditional,purchase-only,monthly,USA or Census Division,East North "
    b"Central Division,DV_ENC,2024,1,190.0,191.0,,\r\n"
    b"traditional,purchase-only,monthly,USA or Census Division,United States,"
    b"USA,2024,2,201.10,202.20,,revised\r\n"
)

OFR = (
    b"Date,OFR FSI,Credit,Equity valuation,Safe assets,Funding,Volatility,"
    b"United States,Other advanced economies,Emerging markets\n"
    b"2024-01-02,-0.1,0.1,-0.2,0.0,-9.076749291912794e-05,-0.01,-0.08,"
    b"-0.01,-0.01\n"
    b"2024-01-03,0.2,0.2,-0.1,0.0,0.02,0.08,0.15,0.03,0.02\n"
)

FDIC = json.dumps(
    {
        "meta": {"total": 2},
        "data": [
            {
                "data": {
                    "REPDTE": "20240630",
                    "count": 4610,
                    "sum_ASSET": 24102985567,
                    "sum_DEP": 18920503721,
                    "sum_LNLSNET": 12419352275,
                    "sum_NETINC": 137251415,
                }
            },
            {
                "data": {
                    "REPDTE": "20240331",
                    "count": 4640,
                    "sum_ASSET": 24174088924,
                    "sum_DEP": 19113933126,
                    "sum_LNLSNET": 12291727661,
                    "sum_NETINC": 65140148,
                }
            },
        ],
    },
    separators=(",", ":"),
).encode("utf-8")


class ParserTests(unittest.TestCase):
    def test_fhfa_selects_only_exact_national_monthly_purchase_only_rows(self):
        result = collector.parse_fhfa_hpi_monthly_us(FHFA)
        self.assertEqual(len(result["observations"]), 2)
        self.assertEqual(result["observations"][0]["observation_period"], "2024-01")
        self.assertEqual(result["observations"][1]["note"], "revised")

    def test_ofr_preserves_published_decimal_strings(self):
        result = collector.parse_ofr_fsi_daily(OFR)
        self.assertEqual(result["observations"][0]["ofr_fsi"], "-0.1")
        self.assertEqual(
            result["observations"][0]["funding"], "-0.00009076749291912794"
        )
        self.assertEqual(result["observations"][1]["united_states"], "0.15")

    def test_fdic_preserves_quarterly_aggregate_integers_as_strings(self):
        result = collector.parse_fdic_quarterly_aggregate(FDIC)
        self.assertEqual(result["observations"][0]["observation_period"], "2024-03-31")
        self.assertEqual(
            result["observations"][1]["assets_thousand_usd"], "24102985567"
        )

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaises(collector.CollectorError):
            collector.strict_json_loads(b'{"a":1,"a":2}')

    def test_canonical_json_rejects_floats(self):
        with self.assertRaises(collector.CollectorError):
            collector.canonical_json_bytes({"value": 1.5})

    def test_duplicate_observation_period_fails_closed(self):
        duplicated = FHFA + (
            b"traditional,purchase-only,monthly,USA or Census Division,"
            b"United States,USA,2024,2,201.10,202.20,,\r\n"
        )
        with self.assertRaises(collector.CollectorError):
            collector.parse_fhfa_hpi_monthly_us(duplicated)


class StoreTests(unittest.TestCase):
    def test_collection_is_content_addressed_and_verifiable(self):
        base = Path(__file__).resolve().parents[1]
        registry = collector.load_registry(base / "source_registry.v1.json")
        bodies = {
            "fdic_banking_aggregate_quarterly": FDIC,
            "fhfa_hpi_monthly_us": FHFA,
            "ofr_fsi_daily": OFR,
        }

        def fake_fetch(source):
            return bodies[source["source_id"]], {
                "content_type": source["expected_content_types"][0],
                "etag": "fixture",
                "last_modified": "fixture",
            }

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(collector, "fetch_source", side_effect=fake_fetch):
                manifest = collector.collect_all(
                    base / "source_registry.v1.json", temporary
                )
            self.assertEqual(
                manifest["source_ids"],
                [source["source_id"] for source in registry["sources"]],
            )
            verified = collector.verify_output(
                base / "source_registry.v1.json", temporary
            )
            self.assertEqual(verified["source_count"], 3)

    def test_registry_is_sorted_unique_and_nonadmitted(self):
        base = Path(__file__).resolve().parents[1]
        registry = collector.load_registry(base / "source_registry.v1.json")
        ids = [source["source_id"] for source in registry["sources"]]
        self.assertEqual(ids, sorted(set(ids)))
        self.assertTrue(all(source["scientific_admission"] is False for source in registry["sources"]))


if __name__ == "__main__":
    unittest.main()
