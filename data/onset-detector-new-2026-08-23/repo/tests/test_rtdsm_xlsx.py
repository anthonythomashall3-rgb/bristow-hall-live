"""B-LAND-4 §2.3 — TDD for the RTDSM real-time-data xlsx matrix shape.

RTDSM (Philadelphia Fed, Croushore-Stark J.Econometrics 105 2001) publishes one
xlsx per variable: row 1 = ``DATE`` + one vintage column per as-of snapshot
(``<VAR><YY>Q<N>`` quarterly-vintage or ``<VAR><YY>M<M>`` monthly-vintage);
rows 2+ = one observation period per row (``YYYY:QN`` or ``YYYY:MM``); each cell
= the value known as-of that vintage, ``#N/A`` where the observation did not yet
exist as-of that vintage (absence, NOT a hole).  Measured layout recorded in
research/AL4_layout.txt before any parse-at-scale.

The four required proofs: (a) vintage-column extraction, (b) observation /
realtime-window mapping, (c) malformed-cell rejection, (d) round-trip count
(non-#N/A cells == landed observations).
"""
import io
import zipfile

import openpyxl
import pytest

from live_data.rmv2_live import rtdsm_xlsx as rt


def _make_xlsx(sheet_name, header, rows):
    """Build an in-memory RTDSM-shaped workbook (faithful to the sampled files)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(header)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# A minimal RUC-shaped fixture: quarterly-vintage (Qv), monthly-obs (Md).
RUC_HEADER = ["DATE", "RUC65Q4", "RUC66Q1", "RUC26Q2"]
RUC_ROWS = [
    ["1947:01", "#N/A", "#N/A", "3.4"],
    ["1947:02", "#N/A", "4.1", "3.5"],
    ["2026:04", "#N/A", "#N/A", "4.3"],
]
# A ROUTPUT-shaped fixture: quarterly-vintage, quarterly-obs (Qd).
ROUT_HEADER = ["DATE", "ROUTPUT65Q4", "ROUTPUT66Q1"]
ROUT_ROWS = [
    ["1947:Q1", "306.4", "306.4"],
    ["1947:Q2", "309.0", "309.0"],
]
# An EMPLOY-shaped fixture: monthly-vintage (Mv), monthly-obs.
EMP_HEADER = ["DATE", "EMPLOY64M12", "EMPLOY65M1"]
EMP_ROWS = [
    ["1939:01", "29762.0", "29762.0"],
]


def test_vintage_stamp_quarterly_and_monthly():
    """(a) vintage-column extraction: 2-digit year + Q/M -> YYYYMMDD."""
    # quarterly vintage -> middle month of quarter (02/05/08/11), day 01
    assert rt.vintage_stamp("RUC65Q4", "RUC") == "19651101"
    assert rt.vintage_stamp("ROUTPUT66Q1", "ROUTPUT") == "19660201"
    assert rt.vintage_stamp("RUC26Q2", "RUC") == "20260501"
    # monthly vintage -> that month, day 01
    assert rt.vintage_stamp("EMPLOY64M12", "EMPLOY") == "19641201"
    assert rt.vintage_stamp("EMPLOY65M1", "EMPLOY") == "19650101"


def test_vintage_stamp_rejects_foreign_or_malformed():
    with pytest.raises(rt.RtdsmShapeError):
        rt.vintage_stamp("UNRATE65Q4", "RUC")        # wrong var prefix
    with pytest.raises(rt.RtdsmShapeError):
        rt.vintage_stamp("RUC65Q5", "RUC")           # quarter out of range
    with pytest.raises(rt.RtdsmShapeError):
        rt.vintage_stamp("RUC65X4", "RUC")           # neither Q nor M


def test_obs_period_quarterly_and_monthly():
    """(b) observation/realtime-window mapping: DATE cell -> canonical Y-M-D."""
    assert rt.obs_period("1947:Q1") == "1947-01-01"
    assert rt.obs_period("1947:Q4") == "1947-10-01"
    assert rt.obs_period("1947:01") == "1947-01-01"
    assert rt.obs_period("2026:04") == "2026-04-01"


def test_obs_period_rejects_malformed():
    with pytest.raises(rt.RtdsmShapeError):
        rt.obs_period("1947:Q5")
    with pytest.raises(rt.RtdsmShapeError):
        rt.obs_period("1947:13")
    with pytest.raises(rt.RtdsmShapeError):
        rt.obs_period("garbage")


def test_parse_matrix_roundtrip_count_and_absence():
    """(d) round-trip: emitted cells == non-#N/A cells; #N/A = absence, skipped."""
    body = _make_xlsx("ruc", RUC_HEADER, RUC_ROWS)
    cells, sha, meta = rt.parse_matrix(body, "RUC")
    # non-#N/A cells in RUC_ROWS: 3.4, 4.1, 3.5, 4.3 == 4
    assert len(cells) == 4
    assert meta["var"] == "RUC"
    assert meta["vintages"] == 3
    assert meta["obs_rows"] == 3
    assert len(sha) == 64
    # exact cell membership (vintage_stamp, obs_period, value)
    got = {(c["vintage"], c["period"], c["value"]) for c in cells}
    assert ("20260501", "1947-01-01", "3.4") in got     # RUC26Q2 @ 1947:01
    assert ("19660201", "1947-02-01", "4.1") in got      # RUC66Q1 @ 1947:02
    # #N/A cells never appear
    assert not any(c["value"] in ("#N/A", "", ".") for c in cells)


def test_parse_matrix_quarterly_obs_and_monthly_vintage_shapes():
    cells_q, _, meta_q = rt.parse_matrix(
        _make_xlsx("ROUTPUT", ROUT_HEADER, ROUT_ROWS), "ROUTPUT"
    )
    assert meta_q["vintages"] == 2 and len(cells_q) == 4
    assert ("19651101", "1947-01-01", "306.4") in {
        (c["vintage"], c["period"], c["value"]) for c in cells_q
    }
    cells_m, _, meta_m = rt.parse_matrix(
        _make_xlsx("EMPLOY", EMP_HEADER, EMP_ROWS), "EMPLOY"
    )
    assert len(cells_m) == 2
    assert ("19641201", "1939-01-01", "29762.0") in {
        (c["vintage"], c["period"], c["value"]) for c in cells_m
    }


def test_parse_matrix_rejects_malformed_shape():
    """(c) malformed-cell rejection: never silently coerce or skip a bad shape."""
    # header does not start with DATE
    with pytest.raises(rt.RtdsmShapeError):
        rt.parse_matrix(_make_xlsx("ruc", ["NOTDATE", "RUC65Q4"], [["1947:01", "3.4"]]), "RUC")
    # a foreign vintage column (wrong var) is refused, not ignored
    with pytest.raises(rt.RtdsmShapeError):
        rt.parse_matrix(
            _make_xlsx("ruc", ["DATE", "RUC65Q4", "UNRATE65Q4"], [["1947:01", "3.4", "3.4"]]),
            "RUC",
        )
    # a non-numeric non-#N/A value cell is refused
    with pytest.raises(rt.RtdsmShapeError):
        rt.parse_matrix(_make_xlsx("ruc", ["DATE", "RUC65Q4"], [["1947:01", "abc"]]), "RUC")


def test_series_id_naming_is_own_base_never_aliased():
    """Own-base RTDSM naming (CLAIMSx precedent): RTDSM_<VAR>.DEEPASOF<stamp>;
    mapping to FRED concepts is research, never an alias onto UNRATE/PAYEMS/..."""
    sid = rt.series_id("RTDSM", "RUC", "19651101")
    assert sid == "RTDSM_RUC.DEEPASOF19651101"
    # provider-neutral: does not begin with a FRED base
    assert not sid.startswith("UNRATE")
