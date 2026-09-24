from __future__ import absolute_import

import copy
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import adapters
from live_data.rmv2_live.adapters import SourceUnavailable
from live_data.rmv2_live.config import load_config


CONFIG_PATH = PROJECT_ROOT / "live_data" / "config" / "sources.v1.json"
RETRIEVED_AT = "2026-07-30T17:00:00Z"
ENDPOINT = (
    "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    "?$select=femaDeclarationString,disasterNumber,state,declarationType,"
    "declarationDate,fyDeclared,incidentType,declarationTitle,"
    "ihProgramDeclared,iaProgramDeclared,paProgramDeclared,"
    "hmProgramDeclared,incidentBeginDate,incidentEndDate,"
    "disasterCloseoutDate,tribalRequest,fipsStateCode,fipsCountyCode,"
    "placeCode,designatedArea,declarationRequestNumber,lastIAFilingDate,"
    "incidentId,region,designatedIncidentTypes,lastRefresh,hash,id"
    "&$filter=declarationDate%20ge%20"
    "%272026-01-01T00%3A00%3A00.000Z%27"
    "&$orderby=declarationDate%20asc,disasterNumber%20asc,"
    "placeCode%20asc,id%20asc&$top=10000&$metadata=false"
)


def source_config(page_limit=10000):
    return {
        "adapter": "openfema_disaster_declarations_json",
        "allowed_hosts": ["www.fema.gov"],
        "coverage_source_ids": ["fema_disasters"],
        "enabled": True,
        "endpoint": ENDPOINT,
        "expected_content_types": ["application/json"],
        "frequency": "rolling_20_minutes_current_year",
        "information_set_mode": "current_revised",
        "label": (
            "OpenFEMA v2 current-year disaster declarations and "
            "designated areas"
        ),
        "max_bytes": 12000000,
        "method_version": (
            "openfema_disaster_declarations_v2.current_year.v1"
        ),
        "poll_seconds": 1200,
        "publisher": "Federal Emergency Management Agency",
        "publisher_release_clock": (
            "OpenFEMA nominal rolling refresh R/PT20M; incident, "
            "declaration, record lastRefresh, retrieval, and validation "
            "clocks remain separate"
        ),
        "rights_status": "public_government_open_data_with_attribution",
        "secret_env": None,
        "secret_required": False,
        "series": {
            "declaration_year": 2026,
            "entity_key": "DisasterDeclarationsSummaries",
            "page_limit": page_limit,
            "projection": "state_and_national_declaration_aggregates_v1",
        },
        "source_id": "fema_disaster_declarations_current_year",
        "value_status": "actual",
    }


def declaration_row(
    declaration_string="DR-5000-CA",
    disaster_number=5000,
    state="CA",
    declaration_type="DR",
    declaration_date="2026-01-02T00:00:00.000Z",
    place_code="10000",
    designated_area="Alameda (County)",
    record_id="11111111-1111-4111-8111-111111111111",
    record_hash="1111111111111111111111111111111111111111",
    last_refresh="2026-01-03T04:05:06.789Z",
):
    return {
        "femaDeclarationString": declaration_string,
        "disasterNumber": disaster_number,
        "state": state,
        "declarationType": declaration_type,
        "declarationDate": declaration_date,
        "fyDeclared": 2026,
        "incidentType": "Severe Storm",
        "declarationTitle": "WINTER STORM",
        "ihProgramDeclared": False,
        "iaProgramDeclared": True,
        "paProgramDeclared": True,
        "hmProgramDeclared": False,
        "incidentBeginDate": "2026-01-01T00:00:00.000Z",
        "incidentEndDate": None,
        "disasterCloseoutDate": None,
        "tribalRequest": False,
        "fipsStateCode": "06",
        "fipsCountyCode": "001",
        "placeCode": place_code,
        "designatedArea": designated_area,
        "declarationRequestNumber": "26001",
        "lastIAFilingDate": None,
        "incidentId": "2026010101",
        "region": 9,
        "designatedIncidentTypes": "R",
        "lastRefresh": last_refresh,
        "hash": record_hash,
        "id": record_id,
    }


def publisher_body(rows):
    return json.dumps(
        {"DisasterDeclarationsSummaries": rows},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def positive_rows():
    second_area = declaration_row(
        place_code="10001",
        designated_area="Alpine (County)",
        record_id="22222222-2222-4222-8222-222222222222",
        record_hash="2222222222222222222222222222222222222222",
        last_refresh="2026-01-04T04:05:06.789Z",
    )
    emergency = declaration_row(
        declaration_string="EM-5001-TX",
        disaster_number=5001,
        state="TX",
        declaration_type="EM",
        place_code="660",
        designated_area="Anderson (County)",
        record_id="33333333-3333-4333-8333-333333333333",
        record_hash="3333333333333333333333333333333333333333",
        last_refresh="2026-01-05T04:05:06.789Z",
    )
    emergency["fipsStateCode"] = "48"
    emergency["fipsCountyCode"] = "001"
    emergency["region"] = 6
    return [declaration_row(), second_area, emergency]


class FemaDisasterDeclarationsTests(unittest.TestCase):
    def test_state_and_national_counts_are_deterministic_administrative_events(self):
        records = adapters.normalize(
            source_config(),
            publisher_body(positive_rows()),
            RETRIEVED_AT,
        )

        self.assertEqual(len(records), 8)
        by_series = {row["series_id"]: row for row in records}
        self.assertEqual(
            by_series["FEMA.DECLARATIONS.CA.DR.EVENT_COUNT"]["value"],
            "1",
        )
        self.assertEqual(
            by_series[
                "FEMA.DECLARATIONS.CA.DR.DESIGNATED_AREA_COUNT"
            ]["value"],
            "2",
        )
        self.assertEqual(
            by_series["FEMA.DECLARATIONS.US.DR.EVENT_COUNT"]["value"],
            "1",
        )
        self.assertEqual(
            by_series[
                "FEMA.DECLARATIONS.US.DR.DESIGNATED_AREA_COUNT"
            ]["value"],
            "2",
        )
        state = by_series[
            "FEMA.DECLARATIONS.CA.DR.DESIGNATED_AREA_COUNT"
        ]
        self.assertEqual(state["observation_period"], "2026-01-02")
        self.assertEqual(state["value_status"], "actual")
        self.assertEqual(state["provider_vintage_kind"], "current_revised")
        self.assertFalse(state["strict_publisher_first_release_proven"])
        self.assertIsNone(state["release_at"])
        self.assertEqual(
            state["publisher_declaration_ids"],
            ["DR-5000-CA"],
        )
        self.assertEqual(len(state["publisher_record_ids"]), 2)
        self.assertEqual(
            state["publisher_last_refresh_max"],
            "2026-01-04T04:05:06.789Z",
        )
        self.assertEqual(
            state["publisher_semantic_guard"],
            (
                "administrative declaration and designated-area counts; "
                "not disaster severity, recession stress, or chronology"
            ),
        )

        reversed_records = adapters.normalize(
            source_config(),
            publisher_body(positive_rows()),
            RETRIEVED_AT,
        )
        self.assertEqual(records, reversed_records)

    def test_exact_envelope_fields_types_and_cross_field_identity_fail_closed(self):
        base = positive_rows()
        mutations = []

        extra = copy.deepcopy(base)
        extra[0]["declarationRequestDate"] = None
        mutations.append(extra)
        missing = copy.deepcopy(base)
        del missing[0]["lastRefresh"]
        mutations.append(missing)
        bad_boolean = copy.deepcopy(base)
        bad_boolean[0]["iaProgramDeclared"] = "true"
        mutations.append(bad_boolean)
        bad_integer = copy.deepcopy(base)
        bad_integer[0]["disasterNumber"] = "05000"
        mutations.append(bad_integer)
        bad_region = copy.deepcopy(base)
        bad_region[0]["region"] = 11
        mutations.append(bad_region)
        bad_hash = copy.deepcopy(base)
        bad_hash[0]["hash"] = "A" * 40
        mutations.append(bad_hash)
        bad_uuid = copy.deepcopy(base)
        bad_uuid[0]["id"] = "not-a-uuid"
        mutations.append(bad_uuid)
        bad_fips = copy.deepcopy(base)
        bad_fips[0]["fipsStateCode"] = "6"
        mutations.append(bad_fips)
        bad_place = copy.deepcopy(base)
        bad_place[0]["placeCode"] = "01000"
        mutations.append(bad_place)
        bad_date = copy.deepcopy(base)
        bad_date[0]["declarationDate"] = "2026-01-02"
        mutations.append(bad_date)
        bad_identity = copy.deepcopy(base)
        bad_identity[0]["femaDeclarationString"] = "DR-5000-TX"
        mutations.append(bad_identity)
        duplicate_uuid = copy.deepcopy(base)
        duplicate_uuid[1]["id"] = duplicate_uuid[0]["id"]
        mutations.append(duplicate_uuid)
        duplicate_composite = copy.deepcopy(base)
        duplicate_composite[1]["placeCode"] = duplicate_composite[0]["placeCode"]
        mutations.append(duplicate_composite)
        mutations.append(list(reversed(base)))

        for rows in mutations:
            with self.subTest(first=rows[0]):
                with self.assertRaises(SourceUnavailable):
                    adapters.normalize(
                        source_config(),
                        publisher_body(rows),
                        RETRIEVED_AT,
                    )

        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                b'{"DisasterDeclarationsSummaries":[],'
                b'"DisasterDeclarationsSummaries":[]}',
                RETRIEVED_AT,
            )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                json.dumps({
                    "DisasterDeclarationsSummaries": base,
                    "metadata": {},
                }).encode("utf-8"),
                RETRIEVED_AT,
            )

    def test_empty_or_page_limit_sized_responses_refuse_partial_coverage(self):
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                publisher_body([]),
                RETRIEVED_AT,
            )
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(page_limit=3),
                publisher_body(positive_rows()),
                RETRIEVED_AT,
            )

    def test_live_config_is_exact_current_year_disturbance_only_contract(self):
        config = load_config(CONFIG_PATH)
        source = next(
            row for row in config["sources"]
            if row["source_id"] ==
            "fema_disaster_declarations_current_year"
        )
        self.assertTrue(source["enabled"])
        self.assertEqual(
            source["adapter"],
            "openfema_disaster_declarations_json",
        )
        self.assertEqual(source["coverage_source_ids"], ["fema_disasters"])
        self.assertEqual(source["endpoint"], ENDPOINT)
        self.assertEqual(source["poll_seconds"], 1200)
        self.assertEqual(source["series"]["declaration_year"], 2026)
        self.assertEqual(source["series"]["page_limit"], 10000)
        self.assertEqual(source["information_set_mode"], "current_revised")
        self.assertEqual(source["value_status"], "actual")
        self.assertFalse(source["secret_required"])
        self.assertIn("clocks remain separate", source["publisher_release_clock"])

    def test_declaration_title_trailing_whitespace_is_normalized(self):
        """Regression: publisher emits titles with trailing space; B-FEEDFIX-1.

        Measured 20260815: 86 current-year rows carry declarationTitle with a
        trailing space (e.g. 'SEVERE WINTER STORM '). Descriptive free-text
        field, not identity -> normalize (strip), do not fail closed.
        """
        padded = declaration_row()
        padded["declarationTitle"] = "SEVERE WINTER STORM "
        records = adapters.normalize(
            source_config(),
            publisher_body([padded]),
            RETRIEVED_AT,
        )
        self.assertTrue(records)
        for row in records:
            self.assertEqual(
                row["publisher_declaration_titles"],
                ["SEVERE WINTER STORM"],
            )

    def test_declaration_title_internal_control_char_still_rejected(self):
        broken = declaration_row()
        broken["declarationTitle"] = "WINTER\nSTORM"
        with self.assertRaises(SourceUnavailable):
            adapters.normalize(
                source_config(),
                publisher_body([broken]),
                RETRIEVED_AT,
            )


if __name__ == "__main__":
    unittest.main()
