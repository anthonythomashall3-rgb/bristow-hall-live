"""B-LAND-9 — New York Fed Staff Nowcast xlsx adapter (forecast_shape nyfed_nowcast).

FORECAST class: a forecast of a MEASUREMENT (real GDP growth), eligible LABELED
substituted_diagnostic input AND forecast_comparator; NEVER an NBER recession-LABEL
product. Family nyfed_nowcast (external_source_registry, role forecast_comparator,
access B, published_output_under_NY_Fed_terms).

The publisher's "Forecasts By Horizon" sheet is already tidy: one row per weekly
forecast date carrying the backcast (previous quarter), nowcast (current quarter),
and forecast (next quarter) of real GDP growth. This adapter lands three flat
weekly series keyed by the forecast date; empty horizon cells are skipped (a week
that tracks no previous/next quarter is simply absent, the anxious_index convention).

Counts measured from the CH-R35 cache bytes. No network, deterministic.
"""
import datetime
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from live_data.rmv2_live.adapters import normalize  # noqa: E402
from live_data.rmv2_live.forecast_xlsx import (  # noqa: E402
    ForecastXlsxDataError,
    parse_forecast_xlsx_bytes,
)

CACHE = os.path.join(str(PROJECT_ROOT), "research", "prefetch", "forecasts")
NYFED = os.path.join(CACHE, "nyfed_nowcast", "nyfed_staff_nowcast_2002-present.xlsx")


def _body():
    with open(NYFED, "rb") as handle:
        return handle.read()


def _config():
    return {
        "forecast_shape": "nyfed_nowcast",
        "sheet": "Forecasts By Horizon",
        "id_base": "NYFED_STAFF_GDP",
        "unit": "percent, annualized real GDP growth (SAAR)",
        "label": "New York Fed Staff Nowcast of real GDP growth",
    }


def _source():
    return {
        "adapter": "forecast_xlsx",
        "source_id": "nyfed_staff_nowcast",
        "information_set_mode": "substituted_diagnostic",
        "method_version": "nyfed_nowcast_offline.v1",
        "endpoint": "https://www.newyorkfed.org/research/policy/nowcast#nyfed.xlsx",
        "publisher_release_clock": "weekly Friday ~1245 ET named vintage",
        "rights_status": "published_output_under_NY_Fed_terms",
        "value_status": "actual",
        "series": _config(),
    }


# ---- three horizon series --------------------------------------------------

def test_emits_three_horizon_series():
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    ids = set(o["series_id"] for o in obs)
    assert ids == {
        "NYFED_STAFF_GDP_BACKCAST",
        "NYFED_STAFF_GDP_NOWCAST",
        "NYFED_STAFF_GDP_FORECAST",
    }


def test_measured_record_counts_per_horizon():
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    by = {}
    for o in obs:
        by.setdefault(o["series_id"], 0)
        by[o["series_id"]] += 1
    assert by["NYFED_STAFF_GDP_NOWCAST"] == 1026
    assert by["NYFED_STAFF_GDP_BACKCAST"] == 365
    assert by["NYFED_STAFF_GDP_FORECAST"] == 393


def test_nowcast_keyed_by_forecast_date_iso_first_value():
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    now = sorted(
        (o for o in obs if o["series_id"] == "NYFED_STAFF_GDP_NOWCAST"),
        key=lambda o: o["observation_period"],
    )
    first = now[0]
    assert first["observation_period"] == "2002-01-04"
    assert first["value"] == "-0.47"
    assert first["value_status"] == "actual"
    assert first["nyfed_reference_quarter"] == "2002Q1"
    assert first["nyfed_horizon"] == "nowcast"
    assert now[-1]["observation_period"] == "2021-08-27"


def test_skips_empty_horizon_cells_all_actual():
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    # every emitted observation is a real published value; empty cells never
    # produce an 'unavailable' placeholder (skip-None, anxious_index convention).
    assert all(o["value_status"] == "actual" for o in obs)
    assert all(o["value"] is not None for o in obs)


def test_no_duplicate_series_period_keys():
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    keys = [(o["series_id"], o["observation_period"]) for o in obs]
    assert len(keys) == len(set(keys))


def test_reference_quarter_matches_quarter_regex():
    import re
    obs = parse_forecast_xlsx_bytes(_config(), _body())
    q = re.compile(r"^\d{4}Q[1-4]$")
    assert all(q.match(o["nyfed_reference_quarter"]) for o in obs)


# ---- normalize integration -------------------------------------------------

def test_normalize_carries_nyfed_dimensions():
    records = normalize(_source(), _body(), "2026-08-06T10:00:00Z")
    assert records
    sample = next(
        r for r in records if r["series_id"] == "NYFED_STAFF_GDP_NOWCAST"
    )
    assert sample["nyfed_reference_quarter"]
    assert sample["nyfed_horizon"] == "nowcast"
    assert sample["information_set_mode"] == "substituted_diagnostic"
    assert sample["value_status"] == "actual"
    # spf-only dimension must NOT leak onto a nyfed record
    assert "spf_target_code" not in sample


# ---- contract failures -----------------------------------------------------

def test_bad_id_base_namespace_rejected():
    cfg = _config()
    cfg["id_base"] = "SPF_WRONG_NAMESPACE"
    with pytest.raises(ForecastXlsxDataError):
        parse_forecast_xlsx_bytes(cfg, _body())


def test_missing_sheet_rejected():
    cfg = _config()
    cfg["sheet"] = "No Such Sheet"
    with pytest.raises(ForecastXlsxDataError):
        parse_forecast_xlsx_bytes(cfg, _body())
