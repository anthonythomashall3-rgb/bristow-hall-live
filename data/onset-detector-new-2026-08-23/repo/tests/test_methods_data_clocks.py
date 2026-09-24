import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"


class MethodsDataAndClocksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_data_section_precedes_model_equations(self):
        self.assertIn('id="methods-data-clocks"', self.page)
        self.assertLess(
            self.page.index('id="methods-data-clocks"'),
            self.page.index("<summary>1 · The index</summary>"),
        )

    def test_feed_and_family_are_distinct_many_to_many_concepts(self):
        section = self._section()
        self.assertIn("A <b>feed</b> is one concrete acquisition route", section)
        self.assertIn("A <b>family</b> is a stable data concept", section)
        self.assertIn("many-to-many", section)
        self.assertIn("endpoint and query", section)
        self.assertIn("raw response bytes", section)
        self.assertIn("parser and schema version", section)
        self.assertIn("content hashes and receipt chain", section)

    def test_all_information_clocks_are_disclosed(self):
        section = self._section()
        for clock in (
            "observation_start",
            "observation_end",
            "publisher_released_at",
            "provider_available_at",
            "retrieved_at",
            "validated_at",
            "decision_cutoff",
            "revision_valid_from",
            "revision_valid_to",
            "forecast_issued_at",
            "forecast_target_start",
            "forecast_target_end",
        ):
            self.assertIn(f"<code>{clock}</code>", section)

    def test_information_modes_and_value_statuses_cannot_be_silently_mixed(self):
        section = self._section()
        for mode in (
            "original-vintage",
            "real-time / as-known",
            "current-revised",
            "provider-reconstructed vintage",
            "mixed / most up to date",
        ):
            self.assertIn(f"<b>{mode}</b>", section)
        for status in (
            "actual",
            "nowcast",
            "forecast",
            "model_estimate",
            "substituted",
            "unavailable",
        ):
            self.assertIn(f"<code>{status}</code>", section)
        self.assertIn("<code>observed_only</code>", section)
        self.assertIn("<code>nowcast_enhanced</code>", section)
        self.assertIn("never silently mixed", section)

    def test_native_frequency_and_daily_information_state_are_honest(self):
        section = self._section()
        self.assertIn("<code>daily_observed_information_state</code>", section)
        self.assertIn("<code>daily_family_model_estimate</code>", section)
        self.assertIn("does not turn a monthly or quarterly observation into a daily actual", section)
        self.assertIn("Retrieval time is not release time", section)
        self.assertIn("A nowcast estimates the present or not-yet-published recent period", section)
        self.assertIn("A forecast estimates a future period", section)

    @classmethod
    def _section(cls):
        start = cls.page.index('<details class="msec" id="methods-data-clocks"')
        end = cls.page.index("</details>", start) + len("</details>")
        return cls.page[start:end]


if __name__ == "__main__":
    unittest.main()
