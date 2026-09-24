"""R1A section 4 -- conditional HTTP gated to measured 304-honoring sources.

Advertised != honored: a validator on the response does not mean the publisher
answers 304. The gate sends If-Modified-Since / If-None-Match only where a real 304
was measured (positive allowlist), and is a no-op (prior behaviour) when the policy
config is absent, so tests and fresh checkouts are unaffected.
"""
from __future__ import absolute_import

import sys
import tempfile
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.pipeline import (
    RefreshPipeline,
    load_conditional_http_policy,
)


def _decide(policy, adapter, source_id):
    stub = types.SimpleNamespace(conditional_http_policy=policy)
    return RefreshPipeline._send_conditional(
        stub, {"adapter": adapter, "source_id": source_id})


class ConditionalHttpGate(unittest.TestCase):
    def test_policy_absent_is_backward_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_conditional_http_policy(d))
        # None policy -> always send (prior behaviour)
        self.assertTrue(_decide(None, "any_adapter", "any_source"))

    def test_real_policy_loads_measured_honoring_set(self):
        policy = load_conditional_http_policy(str(PROJECT_ROOT))
        self.assertIsNotNone(policy)
        self.assertIn("fred_json_api", policy["adapters"])
        self.assertIn("fred_json_api_vintages", policy["adapters"])
        for sid in ("fdic_banking_aggregate_quarterly", "ofr_fsi_daily",
                    "tsa_throughput_current"):
            self.assertIn(sid, policy["source_ids"])

    def test_gate_sends_only_for_honoring_sources(self):
        policy = load_conditional_http_policy(str(PROJECT_ROOT))
        # honoring: FRED adapters + the three measured source_ids
        self.assertTrue(_decide(policy, "fred_json_api", "fred_indpro_api_current"))
        self.assertTrue(_decide(policy, "ofr_fsi_csv", "ofr_fsi_daily"))
        # not honoring: measured-ignore + untested adapters -> no conditional header
        self.assertFalse(_decide(policy, "fiscaldata_json", "treasury_debt_penny"))
        self.assertFalse(_decide(policy, "census_api", "census_eits_marts_current"))
        self.assertFalse(_decide(policy, "fred_graph_csv", "fred_anfci_current"))


if __name__ == "__main__":
    unittest.main()
