"""B-FIX-1 — publisher decimal-string preservation contract (regression pin).

CH-R68 (COMPLETE 20260806T153237Z) flagged 764 rows carrying "high-decimal"
values (float_precision_noise MED 143 groups + false_precision_padding LOW 621
groups) and hypothesised a float->str round-trip defect in the adapters.

That premise was REFUTED from source bytes — the flagged strings are
BYTE-IDENTICAL to what the publisher emitted (FRED sends both "3.7300000000"
and "3.73"; CFPB sends "977541.9191919171"). Evidence:
research/BFIX1_premise_refutation.json. Owner ruling (delegated 2026-08-08,
_mailbox/answers/20260806T232630Z_B-FIX-1_DECIMAL_PRESERVATION.md):

  "Do not normalize, round, or re-serialize any value whose string is present
   in the source bytes."

There is no round-trip defect because the canonical store CANNOT hold a Python
float: canonical.py:_validate_tree raises CanonicalDataError on any float, so
every numeric cell must already be a str (or int). Publisher decimal precision
is therefore preserved by construction, not by convention.

This test pins that contract VISIBLY so the next 100+ adapter landings inherit
it: a publisher decimal string round-trips byte-identical, and a raw float is
rejected rather than silently normalised. Weakening either half re-opens the
CH-R68 hypothesis this batch closed.
"""
from __future__ import absolute_import

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.canonical import (  # noqa: E402
    CanonicalDataError,
    canonical_json_bytes,
    strict_json_loads,
)

# The exact publisher strings proven byte-present in raw source bytes by
# research/BFIX1_premise_refutation.json. Collapsing any of these to its
# shorter float repr would be the defect CH-R68 suspected and the refutation
# disproved.
PUBLISHER_NATIVE_STRINGS = (
    "3.7300000000",        # fred_dtb3_api_current (false_precision_padding)
    "977541.9191919171",   # cfpb_credit_trends_current (float_precision_noise)
    "292.000000000",       # fred_claimsx_fredmd_panel_vintages_deep
)


class DecimalStringPreservationTests(unittest.TestCase):
    def test_publisher_decimal_string_round_trips_byte_identical(self):
        for raw in PUBLISHER_NATIVE_STRINGS:
            record = {"series_id": "X", "observations": [{"value": raw}]}
            reloaded = strict_json_loads(canonical_json_bytes(record))
            got = reloaded["observations"][0]["value"]
            self.assertIsInstance(got, str)
            # verbatim — NOT float(raw), NOT a shortened repr
            self.assertEqual(got, raw)

    def test_shorter_and_longer_forms_stay_distinct(self):
        # "3.7300000000" must NOT be normalised to "3.73"; both are legitimate
        # distinct publisher emissions and the store keeps whichever arrived.
        padded = strict_json_loads(canonical_json_bytes({"v": "3.7300000000"}))["v"]
        short = strict_json_loads(canonical_json_bytes({"v": "3.73"}))["v"]
        self.assertEqual(padded, "3.7300000000")
        self.assertEqual(short, "3.73")
        self.assertNotEqual(padded, short)

    def test_canonical_layer_rejects_raw_float(self):
        # The structural backstop: a float can never enter the store, so no
        # adapter can silently degrade a publisher string into float noise.
        with self.assertRaises(CanonicalDataError):
            canonical_json_bytes({"value": 3.73})
        with self.assertRaises(CanonicalDataError):
            canonical_json_bytes({"observations": [{"value": 977541.9191919171}]})

    def test_strict_loader_rejects_float_bearing_json(self):
        # Bytes that decode to a JSON float are rejected too, so a poisoned
        # cache cannot smuggle a float past the loader.
        with self.assertRaises(CanonicalDataError):
            strict_json_loads(b'{"value": 3.73}')


if __name__ == "__main__":
    unittest.main()
