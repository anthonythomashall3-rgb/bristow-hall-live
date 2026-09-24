"""B-OFFLINE-3 item 1 — Dallas Fed WEI native workbook adapter.

The Dallas WEI xlsx carries the current WEI (col B) plus 7 embedded publisher
as-of snapshot columns (C..I). Owner ruling (2026-08-06, question
20260806T065219Z): land ONE flat offline-current EVIDENCE lane, 8 distinct
series, single declared information_set_mode = substituted_diagnostic; each as-of
column preserved with its snapshot date in the series_id AND as additive
per-record provenance. These are DIAGNOSTIC EVIDENCE, never store-native
archive_snapshot_asof vintages — a future batch (B-OFFLINE-6) re-lands them as
true vintages.
"""
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import normalize  # noqa: E402
from live_data.rmv2_live.dallas_wei import (  # noqa: E402
    DallasWeiDataError,
    parse_dallas_wei_workbook,
)


CACHE = os.path.join(
    str(PROJECT_ROOT), "research", "prefetch", "wei",
    "weekly-economic-index.xlsx",
)

UNIT = "percent scaled to four-quarter GDP growth"
SHEET = "2008-current"

ASOF = {
    "WEI_DALLAS_ASOF_20250925": "2025-09-25",
    "WEI_DALLAS_ASOF_20240926": "2024-09-26",
    "WEI_DALLAS_ASOF_20230928": "2023-09-28",
    "WEI_DALLAS_ASOF_20220929": "2022-09-29",
    "WEI_DALLAS_ASOF_20220125": "2022-01-25",
    "WEI_DALLAS_ASOF_20210729": "2021-07-29",
    "WEI_DALLAS_ASOF_20200728": "2020-07-28",
}


def _members():
    members = [{
        "series_id": "WEI_DALLAS_NATIVE",
        "column_kind": "current",
        "asof_date": None,
        "label": "Weekly Economic Index (Dallas Fed native, current column)",
    }]
    for sid, iso in ASOF.items():
        members.append({
            "series_id": sid,
            "column_kind": "asof",
            "asof_date": iso,
            "label": "Weekly Economic Index publisher as-of %s snapshot" % iso,
        })
    return members


def _series_config():
    return {
        "index_label": "Dallas Fed Weekly Economic Index native workbook",
        "unit": UNIT,
        "vintage_sheet": SHEET,
        "members": _members(),
    }


def _source():
    return {
        "adapter": "dallas_wei_xlsx",
        "endpoint": (
            "https://www.dallasfed.org/-/media/documents/research/wei/"
            "weekly-economic-index.xlsx"
        ),
        "information_set_mode": "substituted_diagnostic",
        "method_version": "dallas_wei_native_offline.v1",
        "publisher": "Federal Reserve Bank of Dallas",
        "publisher_release_clock": "Thursday_1130_ET",
        "rights_status": "published_output_with_component_rights",
        "series": _series_config(),
        "source_id": "dallas_wei_native_current",
        "value_status": "actual",
    }


def _body():
    with open(CACHE, "rb") as handle:
        return handle.read()


def test_parses_all_eight_series_with_expected_counts():
    obs = parse_dallas_wei_workbook(_series_config(), _body())
    by_series = {}
    for row in obs:
        by_series.setdefault(row["series_id"], []).append(row)
    assert set(by_series) == set(ASOF) | {"WEI_DALLAS_NATIVE"}
    # measured coverage (CH-R51 + independent probe)
    expect = {
        "WEI_DALLAS_NATIVE": 969,
        "WEI_DALLAS_ASOF_20250925": 925,
        "WEI_DALLAS_ASOF_20240926": 873,
        "WEI_DALLAS_ASOF_20230928": 821,
        "WEI_DALLAS_ASOF_20220929": 769,
        "WEI_DALLAS_ASOF_20220125": 734,
        "WEI_DALLAS_ASOF_20210729": 708,
        "WEI_DALLAS_ASOF_20200728": 656,
    }
    assert {k: len(v) for k, v in by_series.items()} == expect


def test_current_column_spans_full_range_and_matches_known_cells():
    obs = parse_dallas_wei_workbook(_series_config(), _body())
    cur = sorted(
        (r for r in obs if r["series_id"] == "WEI_DALLAS_NATIVE"),
        key=lambda r: r["observation_period"],
    )
    assert cur[0]["observation_period"] == "2008-01-05"
    assert cur[-1]["observation_period"] == "2026-07-25"
    first = {r["observation_period"]: r["value"] for r in cur}
    assert first["2008-01-05"] == "1.95"


def test_asof_provenance_and_dates():
    obs = parse_dallas_wei_workbook(_series_config(), _body())
    for row in obs:
        if row["series_id"] == "WEI_DALLAS_NATIVE":
            assert row["provider_asof_date"] is None
        else:
            assert row["provider_asof_date"] == ASOF[row["series_id"]]
        assert row["unit"] == UNIT
    # a known as-of cell: col I (2020-07-28 snapshot), 2008-01-05 = 1.41
    i = {
        r["observation_period"]: r["value"]
        for r in obs if r["series_id"] == "WEI_DALLAS_ASOF_20200728"
    }
    assert i["2008-01-05"] == "1.41"
    # the 2020-07-28 snapshot ends at its as-of week, not the current tail
    last = max(
        r["observation_period"]
        for r in obs if r["series_id"] == "WEI_DALLAS_ASOF_20200728"
    )
    assert last == "2020-07-25"


def test_normalize_stamps_single_diagnostic_mode_and_source():
    src = _source()
    records = normalize(src, _body(), "2026-08-06T00:00:00Z")
    assert records, "expected records"
    for record in records:
        assert record["information_set_mode"] == "substituted_diagnostic"
        assert record["source_id"] == "dallas_wei_native_current"
        assert record["value_status"] in ("actual", "unavailable")
    # native series must NOT reuse the FRED headline id "WEI"
    assert all(r["series_id"] != "WEI" for r in records)


def test_deterministic_across_two_parses():
    a = parse_dallas_wei_workbook(_series_config(), _body())
    b = parse_dallas_wei_workbook(_series_config(), _body())
    assert a == b


def test_rejects_non_xlsx_bytes():
    with pytest.raises(DallasWeiDataError):
        parse_dallas_wei_workbook(_series_config(), b"not a zip file at all")


def test_rejects_config_member_absent_from_file():
    cfg = _series_config()
    cfg["members"].append({
        "series_id": "WEI_DALLAS_ASOF_19990101",
        "column_kind": "asof",
        "asof_date": "1999-01-01",
        "label": "phantom as-of not present in the workbook",
    })
    with pytest.raises(DallasWeiDataError):
        parse_dallas_wei_workbook(cfg, _body())


def test_rejects_file_column_absent_from_config():
    cfg = _series_config()
    # drop one real as-of member -> its file column is now unmapped -> reject
    cfg["members"] = [
        m for m in cfg["members"]
        if m["series_id"] != "WEI_DALLAS_ASOF_20200728"
    ]
    with pytest.raises(DallasWeiDataError):
        parse_dallas_wei_workbook(cfg, _body())
