import json
import hashlib
import datetime
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
CONTRACT = (
    ROOT
    / "model_authority"
    / "projections"
    / "index_onset_watch_projection.v1.json"
)


class IndexOnsetWatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.page = PAGE.read_text(encoding="utf-8")

    def test_projection_contract_is_explicitly_non_scientific(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["schema_version"],
            "recession_monitor_v2.index_onset_watch_projection.v1",
        )
        self.assertEqual(contract["scientific_effect"], "none")
        self.assertEqual(
            contract["status"],
            "implemented_original_model_projection_not_new_v2_science",
        )
        self.assertFalse(contract["retrospective_chronology_is_rewritten"])
        page_bytes = PAGE.read_bytes()
        self.assertEqual(len(page_bytes), contract["implementation"]["bytes"])
        self.assertEqual(
            hashlib.sha256(page_bytes).hexdigest(),
            contract["implementation"]["sha256"],
        )

    def test_index_contains_one_shared_live_declaration_surface(self):
        self.assertIn('id="ch1-declaration"', self.page)
        self.assertIn('id="ch1-call-badge"', self.page)
        self.assertIn('id="ch1-call-copy"', self.page)
        self.assertIn('aria-live="polite"', self.page)
        self.assertIn('aria-atomic="true"', self.page)
        self.assertIn('href="#card-watch"', self.page)
        self.assertIn("renderIndexCallProjection()", self.page)
        self.assertLess(
            self.page.index('id="ch1-status"'),
            self.page.index('id="ch1-declaration"'),
        )
        self.assertLess(
            self.page.index('id="ch1-declaration"'),
            self.page.index('id="ch1-guide"'),
        )
        self.assertLess(
            self.page.index('id="ch1-guide"'),
            self.page.index('id="ch1" class="ch"'),
        )

    def test_online_call_and_retrospective_chronology_stay_distinct(self):
        self.assertIn("Online call marker", self.page)
        self.assertIn("retrospective model chronology", self.page)
        self.assertIn("INDEX_WATCH_CALLS", self.page)
        self.assertIn("watchCalls:()=>selST?[]:INDEX_WATCH_CALLS", self.page)
        self.assertIn("retrospective_chronology_is_rewritten", CONTRACT.read_text())

    def test_call_projection_fails_closed_and_marks_provisional_calls(self):
        self.assertIn("function deriveIndexCallProjection", self.page)
        self.assertIn('status:"provisional_recession_call"', self.page)
        self.assertIn('status:"confirmed_recession_call"', self.page)
        self.assertIn('status:"no_recession_call"', self.page)
        self.assertIn('status:"unavailable"', self.page)
        self.assertIn("PROVISIONAL RECESSION CALL", self.page)
        self.assertIn("not a retrospective peak date", self.page)

    def test_call_projection_executes_the_complete_state_table(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to execute the inline projection")
        start = self.page.index("function isStrictIsoCalendarDate")
        end = self.page.index("function renderIndexCallProjection")
        helper = self.page[start:end]
        cases = [
            [{"state": "clear", "watch_onset": None}, "no_recession_call"],
            [{"state": "expansion", "watch_onset": None}, "no_recession_call"],
            [{"state": "aftermath", "watch_onset": None}, "no_recession_call"],
            [
                {"state": "watch", "watch_onset": "2026-08-01"},
                "provisional_recession_call",
            ],
            [
                {"state": "confirmed", "watch_onset": "2026-08-01"},
                "confirmed_recession_call",
            ],
            [{"state": "watch", "watch_onset": None}, "unavailable"],
            [
                {"state": "clear", "watch_onset": "2026-08-01"},
                "unavailable",
            ],
            [{"state": "unknown", "watch_onset": None}, "unavailable"],
            [{"state": "watch", "watch_onset": "2026-99-99"}, "unavailable"],
            [{"state": "watch", "watch_onset": "2025-02-29"}, "unavailable"],
            [
                {"state": "watch", "watch_onset": "2024-02-29"},
                "provisional_recession_call",
            ],
            [
                {"state": "watch", "watch_onset": "2026-09-01"},
                "unavailable",
            ],
        ]
        js = (
            'function fmtD(value){return value===1?"2026-08-31":String(value);}\n'
            + helper
            + "\nconst cases="
            + json.dumps(cases, separators=(",", ":"))
            + ";\n"
            + "for(const row of cases){"
            + "const got=deriveIndexCallProjection(row[0],1).status;"
            + "if(got!==row[1])throw new Error(JSON.stringify({input:row[0],expected:row[1],got}));"
            + "}\n"
        )
        result = subprocess.run(
            [node],
            input=js,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_historical_markers_use_point_in_time_replay_not_hindsight_onsets(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            contract["historical_marker_source"],
            "VIN.episodes[].rt_call when call_stands is computed true",
        )
        self.assertIn("e.rt_call", self.page)
        self.assertNotIn("WAT.history||[]).filter", self.page)
        self.assertEqual(contract["historical_marker_coverage"], "daily_era_only")
        vin_start = self.page.index("const VIN=") + len("const VIN=")
        vin, _ = json.JSONDecoder().raw_decode(self.page[vin_start:])
        actual = [row["rt_call"] for row in vin["episodes"] if row["rt_call"]]
        self.assertEqual(actual, contract["historical_marker_dates"])
        self.assertEqual(len(actual), contract["historical_marker_count"])
        for value in actual:
            self.assertEqual(datetime.date.fromisoformat(value).isoformat(), value)

    def test_projection_cannot_mutate_retrospective_chronology(self):
        self.assertIn(
            'const INSTR=["1957-58","1960-61","1969-70","1973-75","1980",'
            '"1981-82","1990-91","2001","2007-09","2020","2022-23"]',
            self.page,
        )
        self.assertIn(
            ".filter(k=>DAT[k]).map(k=>[iso2d(DAT[k].onset),iso2d(DAT[k].end)])",
            self.page,
        )
        start = self.page.index("/* RMV2 INDEX+WATCH PROJECTION v1")
        end = self.page.index("/* ---------- monitor charts ---------- */", start)
        projection = self.page[start:end]
        self.assertIsNone(
            re.search(r"\b(?:INSTR|DAT)\s*(?:=|\.(?:push|splice|pop|shift|unshift))", projection)
        )

    def test_latest_and_index_use_the_same_live_projection(self):
        self.assertIn(
            "var _callProjection=deriveIndexCallProjection(",
            self.page,
        )

    def test_canvas_accessibility_names_both_layers(self):
        self.assertIn(
            "online Onset Watch call markers and separate retrospective "
            "recession bands",
            self.page,
        )


if __name__ == "__main__":
    unittest.main()
