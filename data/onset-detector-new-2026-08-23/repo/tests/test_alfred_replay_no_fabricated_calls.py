import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _embedded_vintage():
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    start = page.index("const VIN=") + len("const VIN=")
    return json.JSONDecoder().raw_decode(page[start:])[0]


def test_replay_only_publishes_call_date_when_evaluated_call_stands():
    source = (ROOT / "method_source/alfred_replay.py").read_text(
        encoding="utf-8"
    )
    assert 'row["rt_call"] = call if row["call_stands"] else None' in source
    assert "\n    RT =" not in source

    vintage = _embedded_vintage()
    for row in vintage["episodes"]:
        expected = row["call"] if row["call_stands"] else None
        assert row["rt_call"] == expected
        assert row["note"] == (
            "evaluated call date met the 1.0-sigma threshold"
            if row["call_stands"]
            else "evaluated call date did not meet the 1.0-sigma threshold; "
            "no later call date was computed"
        )


def test_projection_contract_only_pins_computed_non_null_markers():
    vintage = _embedded_vintage()
    contract = json.loads(
        (
            ROOT
            / "model_authority/projections/index_onset_watch_projection.v1.json"
        ).read_text()
    )
    expected = [
        row["rt_call"] for row in vintage["episodes"] if row["rt_call"]
    ]
    assert contract["historical_marker_dates"] == expected
    assert contract["historical_marker_count"] == len(expected)
    assert contract["historical_marker_source"] == (
        "VIN.episodes[].rt_call when call_stands is computed true"
    )
