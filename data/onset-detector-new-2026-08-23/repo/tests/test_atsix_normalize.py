"""B-ACQ-REALTIME-EXPECTATIONS item 4 — TDD for the ATSIX normalize path.

The parse-only ATSIX shape adapter (``atsix_termstructure``) is already proven by
``tests/test_atsix_termstructure.py``. This suite pins the NEW normalize wiring:
``adapters.normalize`` -> ``parse_atsix_termstructure_xlsx`` -> canonical records,
which the offline-current binder consumes to land the forecast_comparator lane
(owner ruling 20260806T162209Z Option 1).

The four proofs: (a) only the owner-specified horizons land (Real/Factors and the
unconfigured infexp3 column are dropped); (b) reference date -> YYYY-MM month, used
as BOTH observation_period and forecast_origin; (c) values copy verbatim as strings,
value_status=forecast, forecast_horizon set; (d) blank cell is absence, not a hole.
"""
import datetime as _dt
import io

import openpyxl

from live_data.rmv2_live import adapters


def _make_xlsx(sheets):
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


def _source():
    return {
        "adapter": "atsix_termstructure_xlsx",
        "endpoint": "https://www.philadelphiafed.org/-/media/FRBP/Assets/"
                    "Surveys-And-Data/atsix/ATSIX_Vintages.xlsx",
        "information_set_mode": "substituted_diagnostic",
        "method_version": "atsix_infexp_offline.v1",
        "publisher": "Federal Reserve Bank of Philadelphia",
        "publisher_release_clock": "irregular ATSIX model production release",
        "rights_status": "published_survey_data",
        "source_id": "philadelphia_atsix_infexp_current_offline",
        "value_status": "forecast",
        "series": {
            "index_label": "ATSIX inflation-expectations term structure (InfExp)",
            "unit": "percent annualized expected CPI inflation",
            "members": [
                {"series_id": "ATSIX_INFEXP12", "horizon_column": "infexp12",
                 "horizon_months": 12, "label": "expected 12m inflation"},
                {"series_id": "ATSIX_INFEXP24", "horizon_column": "infexp24",
                 "horizon_months": 24, "label": "expected 24m inflation"},
                {"series_id": "ATSIX_INFEXP60", "horizon_column": "infexp60",
                 "horizon_months": 60, "label": "expected 60m inflation"},
                {"series_id": "ATSIX_INFEXP120", "horizon_column": "infexp120",
                 "horizon_months": 120, "label": "expected 120m inflation"},
            ],
        },
    }


def _body():
    infexp = (
        "InfExp",
        ["_date_", "infexp3", "infexp12", "infexp24", "infexp60", "infexp120"],
        [
            # infexp120 blank on the first row = absence, not a hole.
            [_dt.datetime(1998, 1, 1), 2.10, 2.33304588634996, 2.40, 2.50, None],
            [_dt.datetime(1998, 2, 1), 2.11, 2.35, 2.41, 2.51, 2.60],
        ],
    )
    real = ("Real", ["_date_", "real3", "real120"],
            [[_dt.datetime(1998, 1, 1), 0.5, 0.9]])
    factors = ("Factors", ["_date_", "level", "slope", "curvature", "lambda"],
               [[_dt.datetime(1998, 1, 1), 2.3, -0.1, 0.2, 0.06]])
    return _make_xlsx([infexp, real, factors])


def test_a_only_configured_horizons_land():
    records = adapters.normalize(_source(), _body(), "2026-08-09T07:54:10Z")
    ids = sorted({r["series_id"] for r in records})
    assert ids == ["ATSIX_INFEXP12", "ATSIX_INFEXP120",
                   "ATSIX_INFEXP24", "ATSIX_INFEXP60"]
    # infexp3 (present in workbook, not configured) never leaks; Real/Factors
    # sheets are untouched.
    assert not any("real" in r["series_id"].lower() for r in records)


def test_b_reference_month_is_period_and_origin():
    records = adapters.normalize(_source(), _body(), "2026-08-09T07:54:10Z")
    r = next(r for r in records
             if r["series_id"] == "ATSIX_INFEXP12" and r["observation_period"] == "1998-01")
    assert r["observation_period"] == "1998-01"
    assert r["forecast_origin"] == "1998-01"
    assert r["forecast_horizon"] == 12


def test_c_values_verbatim_forecast_labeled():
    records = adapters.normalize(_source(), _body(), "2026-08-09T07:54:10Z")
    r = next(r for r in records
             if r["series_id"] == "ATSIX_INFEXP12" and r["observation_period"] == "1998-01")
    # copied verbatim from the cell text, not re-derived / not floated.
    assert r["value"] == "2.33304588634996"
    assert isinstance(r["value"], str)
    assert r["value_status"] == "forecast"
    assert r["information_set_mode"] == "substituted_diagnostic"
    assert r["provider_vintage_kind"] == "atsix_model_expectation"


def test_d_blank_cell_is_absence():
    records = adapters.normalize(_source(), _body(), "2026-08-09T07:54:10Z")
    got = {(r["series_id"], r["observation_period"]) for r in records}
    # infexp120 has no 1998-01 value (blank) -> no record; 1998-02 present.
    assert ("ATSIX_INFEXP120", "1998-01") not in got
    assert ("ATSIX_INFEXP120", "1998-02") in got
