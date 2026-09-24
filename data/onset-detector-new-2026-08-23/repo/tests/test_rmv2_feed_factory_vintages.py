"""Focused tests for the ALFRED vintage-lane onboarding rule in feed_factory.

Covers the owner-scoped derivation + family-prefix collision without touching
the live store (pure-function level).
"""
from __future__ import absolute_import

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live import feed_factory
from live_data.rmv2_live.feed_factory import (
    CanonicalDataError,
    FRED_VINTAGE_APPROVED_BASES,
    _adapter_output_series_ids,
    _fred_vintage_base,
)


def vintage_source(base="GDPC1", label="Real GDP", unit="USD"):
    return {
        "adapter": "fred_json_api_vintages",
        "series": {"label": label, "series_id": base, "unit": unit},
        "source_id": "fred_%s_api_vintages" % base.lower(),
    }


class VintageBaseScopeTest(unittest.TestCase):
    def test_all_approved_vintage_bases_accepted(self):
        # B1.1's original 6 owner bases were expanded to the full 15-base
        # vintage scope in B1.2 as the ALFRED vintage lane (shallow .ASOF and,
        # in B1.3b, deep .DEEPASOF) was drained. This pin is the measured
        # current scope, not the original six.
        # B-LAND-3C-R2, owner ruling 2026-08-05 (Option 4, strict): +2 FRED-MD
        # NEAR-class panel constructs (CLAIMSx, CMRMTSPLx) landed under their OWN
        # distinct ids, never aliased to ICSA/CMRMTSPL. Owner-authorized additive
        # scope growth, not a masked regression -> the pin grows to 17.
        # B-LAND-4-R2, owner ruling 2026-08-06 (Option 2, own-base): +1 RTDSM
        # real-time construct RTDSM_RUC (Philadelphia Fed unemployment-rate as-of
        # vintages), landed under its OWN id per the standing CLAIMSx/CMRMTSPLx
        # precedent, NEVER aliased onto UNRATE. Owner-authorized additive scope
        # growth -> the pin grows to 18. (answers/20260805T232615Z_B-LAND-4_RTDSM.md)
        # B-LAND-10-R2, owner ruling 2026-08-06 (Option 2, DEPTH/replay): +3 RTDSM
        # tranche-A1 constructs (RTDSM_CPI, RTDSM_M1, RTDSM_M2), landed under their
        # OWN ids per the RTDSM_RUC precedent, NEVER aliased onto CPIAUCSL/M1SL/M2SL.
        # A real-time DEPTH acquisition, NOT a channel-diversity claim. Owner-
        # authorized additive scope growth -> the pin grows to 21.
        # (answers/20260806T120326Z_B-LAND-10_RTDSM_ROLLOUT_T1.md)
        # B-RTDSM-ROLL TRANCHE A2, CH-R103 lane decision of record + director
        # batch B-RTDSM-ROLL_TRANCHE_A2 (gated on CH-R103 COMPLETE): +5 RTDSM
        # NEAR-deeper constructs (RTDSM_RCON, RTDSM_NDPI, RTDSM_NPSAV,
        # RTDSM_RATESAV, RTDSM_CUM), own ids per the roster-wide own-base ruling
        # (feed_factory L534 "own-base is the roster-wide ruling"), NEVER aliased
        # onto PCEC96/DSPIC96/PSAVERT/CUMFNS. DEPTH acquisition, delegated
        # reversible acquisition decision (2026-08-08 delegation ruling; not
        # §22.2 universe closure, not a rights/product/§22.4 change). CH-R103
        # measured these 5 as the RTDSM-deeper NEAR pairs not landed in A1/ruc.
        # Owner-authorized (roster-wide) additive scope growth -> the pin grows to 26.
        # B-ACQ-RTDSM-GDI, director batch (gated on B-RTDSM-ROLL_TRANCHE_A2
        # COMPLETE): +24 RTDSM Gross Domestic Income (GDI-account) variables
        # (gen_doc_GDI), own ids per the roster-wide own-base ruling (feed_factory
        # L534), NEVER aliased onto any GDP-side FRED series -- GDI is the INCOME
        # side of the national accounts, NOT GDP. DEPTH acquisition, delegated
        # reversible acquisition decision (2026-08-08 delegation ruling; not §22.2
        # universe closure, not a rights/product/§22.4 change). MEASURED shallow
        # depth: headline YNGDI/YRGDI/YNSD first vintage 2005-02, other 21
        # components 2015-05 -> zero pre-2000 real-time recessions. Additive scope
        # growth -> the pin grows to 50.
        self.assertEqual(
            FRED_VINTAGE_APPROVED_BASES,
            frozenset((
                "CMRMTSPL", "GACDFSA066MSFRBPHI", "GDPC1", "HOUST", "ICSA",
                "INDPRO", "IURSA", "NFCI", "PAYEMS", "PERMIT", "SAHMREALTIME",
                "TCU", "UMCSENT", "UNRATE", "W875RX1",
                "CLAIMSx", "CMRMTSPLx",
                "RTDSM_RUC",
                "RTDSM_CPI", "RTDSM_M1", "RTDSM_M2",
                "RTDSM_RCON", "RTDSM_NDPI", "RTDSM_NPSAV", "RTDSM_RATESAV",
                "RTDSM_CUM",
                "RTDSM_YNGDI", "RTDSM_YRGDI", "RTDSM_YPDGDP", "RTDSM_YNCOMPEP",
                "RTDSM_YNWS", "RTDSM_YNSWS", "RTDSM_YNSD", "RTDSM_YNTAXR",
                "RTDSM_YNCTAX", "RTDSM_YNGSUB", "RTDSM_YNOS", "RTDSM_YNOSG",
                "RTDSM_YNOSP", "RTDSM_YNCFC", "RTDSM_YNCFCG", "RTDSM_YNCFCP",
                "RTDSM_YNCPRFW", "RTDSM_YNCPRFATW", "RTDSM_YNUCPRFW",
                "RTDSM_YNIPAID", "RTDSM_YNDPAID", "RTDSM_YNPINCW", "RTDSM_YNRINC",
                "RTDSM_YNTRPAY",
            )),
        )
        self.assertEqual(len(FRED_VINTAGE_APPROVED_BASES), 50)
        for base in FRED_VINTAGE_APPROVED_BASES:
            self.assertEqual(_fred_vintage_base(vintage_source(base)), base)

    def test_base_outside_scope_is_refused(self):
        with self.assertRaises(CanonicalDataError):
            _fred_vintage_base(vintage_source("CPIAUCSL"))

    def test_non_vintage_adapter_returns_none(self):
        src = vintage_source()
        src["adapter"] = "fred_json_api"
        self.assertIsNone(_fred_vintage_base(src))

    def test_series_shape_must_be_exact(self):
        src = vintage_source()
        src["series"]["extra"] = "x"
        with self.assertRaises(CanonicalDataError):
            _fred_vintage_base(src)

    def test_empty_label_or_unit_refused(self):
        with self.assertRaises(CanonicalDataError):
            _fred_vintage_base(vintage_source(label=""))
        with self.assertRaises(CanonicalDataError):
            _fred_vintage_base(vintage_source(unit=""))


class VintageDerivationTest(unittest.TestCase):
    def test_derives_empty_exact_set_for_valid_base(self):
        # Vintage IDs are data-dependent; the exact set is empty so the lane
        # coexists with the current lane (bare <BASE>) without a false collision.
        self.assertEqual(
            _adapter_output_series_ids(vintage_source(), require_complete=True),
            frozenset(),
        )

    def test_derivation_still_validates_scope(self):
        with self.assertRaises(CanonicalDataError):
            _adapter_output_series_ids(vintage_source("XYZ"), require_complete=True)


class VintageFamilyPrefixTest(unittest.TestCase):
    def test_family_prefix_matches_realized_ids_only(self):
        base = _fred_vintage_base(vintage_source())
        prefix = base + feed_factory.FRED_VINTAGE_FAMILY_SUFFIX
        # a realized as-of ID collides on the family prefix ...
        self.assertTrue(("GDPC1.ASOF20240101").startswith(prefix))
        # ... but the bare current-lane base does NOT (deliberate coexistence).
        self.assertFalse(("GDPC1").startswith(prefix))


if __name__ == "__main__":
    unittest.main()
