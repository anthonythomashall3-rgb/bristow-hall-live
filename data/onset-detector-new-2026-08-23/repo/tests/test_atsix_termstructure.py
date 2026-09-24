"""B-LAND-12 — TDD for the ATSIX inflation-expectations term-structure xlsx shape.

ATSIX (Aruoba, *Term Structure of Inflation Expectations*, Philadelphia Fed) is
NOT an RTDSM realized-vintage matrix.  Measured layout (research/_bland12_sheets.json,
recorded before any parse-at-scale):

    sheet InfExp:  _date_, infexp3, infexp4, ..., infexp120   (horizons, NOT vintages)
    sheet Real:    _date_, real3,   real4,   ..., real120
    sheet Factors: _date_, level, slope, curvature, lambda
    rows 2+     : <YYYY-MM-01 datetime>, value, value, ...

Each cell is ONE value at (reference date, horizon/factor); there is NO vintage-date
column axis, so the standard ``rtdsm_xlsx`` matrix parser cannot read it (CH-R39 already
classed atsix "forecast-class, not real-time realized data").  This adapter therefore
emits ``(sheet, series, date, value)`` records, NOT as-of ``(vintage, period)`` cells.

The four required proofs: (a) term-structure column extraction, (b) date mapping,
(c) malformed-cell rejection, (d) round-trip count (non-blank cells == emitted records),
plus the docProps/core.xml strip that openpyxl needs on Phil-Fed workbooks.
"""
import datetime as _dt
import io
import zipfile

import openpyxl
import pytest

from live_data.rmv2_live import atsix_termstructure as ats


def _make_xlsx(sheets):
    """Build an in-memory ATSIX-shaped workbook. ``sheets`` = [(name, header, rows)]."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, header, rows in sheets:
        ws = wb.create_sheet(name)
        ws.append(header)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


INFEXP = (
    "InfExp",
    ["_date_", "infexp3", "infexp12", "infexp120"],
    [
        [_dt.datetime(1998, 1, 1), 2.17197209049377, 2.33304588634996, None],
        [_dt.datetime(1998, 2, 1), 2.20, 2.35, 2.50],
    ],
)
REAL = (
    "Real",
    ["_date_", "real3", "real120"],
    [[_dt.datetime(1998, 1, 1), 3.2017199916683, 1.5]],
)
FACTORS = (
    "Factors",
    ["_date_", "level", "slope", "curvature", "lambda"],
    [[_dt.datetime(1998, 1, 1), 2.5698, 0.4966, 0.1357, 0.0542]],
)


def test_a_term_structure_columns_extracted():
    body = _make_xlsx([INFEXP])
    recs, sha, meta = ats.parse_sheet(body, "InfExp")
    series = {r["series"] for r in recs}
    assert series == {"infexp3", "infexp12", "infexp120"}
    assert meta["horizons"] == 3
    assert len(sha) == 64


def test_b_date_mapped_to_first_of_month():
    body = _make_xlsx([INFEXP])
    recs, _, _ = ats.parse_sheet(body, "InfExp")
    dates = sorted({r["date"] for r in recs})
    assert dates == ["1998-01-01", "1998-02-01"]


def test_c_blank_is_absence_not_a_hole():
    # row 1 infexp120 is None -> skipped, not zero, not error.
    body = _make_xlsx([INFEXP])
    recs, _, meta = ats.parse_sheet(body, "InfExp")
    got = {(r["date"], r["series"]) for r in recs}
    assert ("1998-01-01", "infexp120") not in got
    assert ("1998-02-01", "infexp120") in got
    # 2 rows * 3 cols = 6 cells, minus 1 blank = 5 records.
    assert meta["records"] == 5
    assert len(recs) == 5


def test_d_malformed_value_rejected_not_coerced():
    bad = ("InfExp", ["_date_", "infexp3"], [[_dt.datetime(1998, 1, 1), "n/a-oops"]])
    body = _make_xlsx([bad])
    with pytest.raises(ats.AtsixShapeError):
        ats.parse_sheet(body, "InfExp")


def test_e_header_must_start_with_date_marker():
    bad = ("InfExp", ["wrong", "infexp3"], [[_dt.datetime(1998, 1, 1), 1.0]])
    body = _make_xlsx([bad])
    with pytest.raises(ats.AtsixShapeError):
        ats.parse_sheet(body, "InfExp")


def test_f_factors_sheet_non_horizon_columns():
    body = _make_xlsx([FACTORS])
    recs, _, meta = ats.parse_sheet(body, "Factors")
    assert {r["series"] for r in recs} == {"level", "slope", "curvature", "lambda"}
    assert meta["horizons"] == 4  # generic column count, factors are not horizons


def test_g_roundtrip_all_sheets_and_corexml_strip():
    body = _make_xlsx([INFEXP, REAL, FACTORS])
    # inject a date-only docProps/core.xml that openpyxl 3.1 on py3.8 refuses,
    # to prove the strip path (faithful to the real Phil-Fed workbooks).
    src = zipfile.ZipFile(io.BytesIO(body))
    buf = io.BytesIO()
    dst = zipfile.ZipFile(buf, "w")
    for it in src.infolist():
        dst.writestr(it, src.read(it.filename))
    dst.writestr(
        "docProps/core.xml",
        '<?xml version="1.0"?><cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        '<dcterms:modified xsi:type="dcterms:W3CDTF" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">2026-08-05</dcterms:modified>'
        "</cp:coreProperties>",
    )
    dst.close()
    body2 = buf.getvalue()
    total = 0
    for sheet in ("InfExp", "Real", "Factors"):
        recs, _, meta = ats.parse_sheet(body2, sheet)
        total += meta["records"]
    # InfExp 5 + Real 2 + Factors 4 = 11
    assert total == 11
