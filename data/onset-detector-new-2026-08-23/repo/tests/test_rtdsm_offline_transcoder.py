"""B-LAND-4-R2 §2 — TDD for the RTDSM xlsx -> FRED output_type=2 transcoder.

The proven deep parser (adapters.parse_fred_json_api_vintages_deep) owns
.DEEPASOF naming, the deep-window gate, the growth cap and mode tagging, but only
from an output_type=2 wide-matrix body. ``rtdsm_xlsx`` reads the Philadelphia Fed
real-time-data workbook into ``(vintage, period, value)`` cells; this transcoder
reshapes those cells, for ONE variable's OWN base id (e.g. ``RTDSM_RUC``), into
the exact output_type=2 body the proven parser accepts — so the proven parser,
not a bespoke one, emits the records and applies the window/cap.

Unlike the ALFRED / FRED-MD transcoders (one file per vintage), a single RTDSM
workbook carries EVERY vintage as a column; so ``transcode_base`` takes exactly
one file and its per-vintage provenance all shares that one workbook's sha256.

Own-base naming is binding (CLAIMSx/CMRMTSPLx precedent): RUC lands as
``RTDSM_RUC.DEEPASOF<vintage>`` and is NEVER aliased onto UNRATE.
"""
import io
import zipfile

import openpyxl
import pytest

from live_data.rmv2_live import rtdsm_offline_transcoder as rot
from live_data.rmv2_live import vintage_csv_transcoder as vct
from live_data.rmv2_live.adapters import parse_fred_json_api_vintages_deep


def _make_xlsx(sheet_name, header, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# A minimal RUC-shaped fixture: quarterly-vintage, monthly-obs. One in-window
# vintage (1965Q4 -> 19651101), one out-of-window (2026Q2 -> 20260501).
RUC_HEADER = ["DATE", "RUC65Q4", "RUC66Q1", "RUC26Q2"]
RUC_ROWS = [
    ["1948:01", "#N/A", "#N/A", "3.4"],
    ["1948:02", "5.9", "4.1", "3.5"],
    ["2026:04", "#N/A", "#N/A", "4.3"],
]


def _write_xlsx(tmp_path, name, header, rows):
    p = tmp_path / name
    p.write_bytes(_make_xlsx("ruc", header, rows))
    return str(p)


def _ruc_source():
    return {
        "adapter": "fred_json_api_vintages_deep",
        "endpoint": "https://www.philadelphiafed.org/rtdsm",
        "information_set_mode": "archive_snapshot_asof",
        "method_version": "philadelphia_rtdsm_ruc_vintages_deep.v1",
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": "RTDSM quarterly vintage release; underlying release time null",
        "rights_status": "public_with_attribution",
        "rtdsm_var": "RUC",
        "series": {
            "label": "Unemployment rate (RTDSM real-time as-of snapshots)",
            "series_id": "RTDSM_RUC",
            "unit": "Percent",
        },
        "source_id": "philadelphia_rtdsm_ruc_vintages_deep",
        "value_status": "actual",
    }


def test_transcode_base_emits_output_type2_wide_matrix(tmp_path):
    """Pivot cells into the exact output_type=2 body the deep parser accepts,
    columns keyed <BASE>_<vintage>, dates sorted."""
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    body, prov = rot.transcode_base([f], source=_ruc_source())
    assert body["file_type"] == "json" and body["output_type"] == "2"
    obs = {row["date"]: row for row in body["observations"]}
    # 1948-02 row carries the 1965Q4 (5.9), 1966Q1 (4.1) and 2026Q2 (3.5) columns
    assert obs["1948-02-01"]["RTDSM_RUC_19651101"] == "5.9"
    assert obs["1948-02-01"]["RTDSM_RUC_19660201"] == "4.1"
    assert obs["1948-02-01"]["RTDSM_RUC_20260501"] == "3.5"
    # 1948-01 row: only the 2026Q2 vintage carries a cell (#N/A elsewhere)
    assert obs["1948-01-01"] == {"date": "1948-01-01", "RTDSM_RUC_20260501": "3.4"}
    # dates are sorted ascending
    assert [r["date"] for r in body["observations"]] == [
        "1948-01-01", "1948-02-01", "2026-04-01",
    ]


def test_provenance_is_per_vintage_sharing_one_workbook_sha(tmp_path):
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    _, prov = rot.transcode_base([f], source=_ruc_source())
    # one entry per vintage column present in the workbook
    vintages = sorted(e["vintage"] for e in prov)
    assert vintages == ["19651101", "19660201", "20260501"]
    shas = {e["source_sha256"] for e in prov}
    assert len(shas) == 1  # all vintages come from the ONE workbook
    for e in prov:
        assert e["base"] == "RTDSM_RUC"
        assert e["source_path"] == f
        assert len(e["source_sha256"]) == 64
    # row_count reflects non-absence cells for that vintage
    by_v = {e["vintage"]: e["row_count"] for e in prov}
    assert by_v["19651101"] == 1   # only 1948:02 = 5.9
    assert by_v["20260501"] == 3   # 1948:01, 1948:02, 2026:04


def test_body_feeds_proven_deep_parser_own_base_window_gated(tmp_path):
    """The emitted body round-trips through the UNCHANGED deep parser: own-base
    RTDSM_RUC.DEEPASOF ids, out-of-window (2026) vintage dropped by the gate."""
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    body, _ = rot.transcode_base([f], source=_ruc_source())
    body_bytes = vct.body_bytes(body)
    records = parse_fred_json_api_vintages_deep(
        _ruc_source(), body_bytes, "2026-08-06T00:00:00Z"
    )
    ids = {r["series_id"] for r in records}
    # in-window vintages land under own base, never aliased to UNRATE
    assert "RTDSM_RUC.DEEPASOF19651101" in ids
    assert "RTDSM_RUC.DEEPASOF19660201" in ids
    assert all(sid.startswith("RTDSM_RUC.DEEPASOF") for sid in ids)
    assert not any(sid.startswith("UNRATE") for sid in ids)
    # the 2026Q2 vintage is out of the deep window -> not landed here
    assert "RTDSM_RUC.DEEPASOF20260501" not in ids


def test_shared_body_canonicalisation_matches_alfred_shape(tmp_path):
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    body, _ = rot.transcode_base([f], source=_ruc_source())
    # deterministic + identical canonicaliser/shape-sha as the ALFRED transcoder
    assert rot.body_bytes is vct.body_bytes
    assert rot.response_schema_sha256(body) == vct.response_schema_sha256(body)
    assert vct.body_bytes(body) == vct.body_bytes(body)


def test_requires_exactly_one_workbook(tmp_path):
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([f, f], source=_ruc_source())
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([], source=_ruc_source())


def test_requires_source_base(tmp_path):
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([f], source=None)
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([f], source={"rtdsm_var": "RUC"})  # no series_id
    # base that is neither RTDSM_<VAR> nor carries an rtdsm_var override -> refuse
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([f], source={"series": {"series_id": "FOO"}})


def test_var_derived_from_own_base_when_no_override(tmp_path):
    """The PERSISTED source carries only the standard config keys (no rtdsm_var),
    so the workbook variable is derived from the RTDSM_<VAR> base id."""
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", RUC_HEADER, RUC_ROWS)
    src = {  # no rtdsm_var key -> derived "RUC" from "RTDSM_RUC"
        "series": {"label": "l", "series_id": "RTDSM_RUC", "unit": "Percent"},
    }
    body, prov = rot.transcode_base([f], source=src)
    assert any("RTDSM_RUC_19651101" in row for row in body["observations"])
    assert {e["base"] for e in prov} == {"RTDSM_RUC"}


def test_duplicate_vintage_period_cell_refused(tmp_path):
    # two columns with the SAME vintage stamp would collide on (column, period)
    header = ["DATE", "RUC65Q4", "RUC65Q4"]
    rows = [["1948:02", "5.9", "5.9"]]
    f = _write_xlsx(tmp_path, "rucQvMd.xlsx", header, rows)
    with pytest.raises(rot.RtdsmTranscodeError):
        rot.transcode_base([f], source=_ruc_source())
