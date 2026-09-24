"""B-OFFLINE-3-R2 — the DTS Table-I "Operating Cash Balance" account -> series
projection adapter, per director ruling 20260806T084233Z (B=Option 1: ten clean
literal series, SPLICE NOTHING) and the value-column measurement filed as
20260806T153123Z (per-member ``value_field``; the post-2022 TGA "Cash Balance
Details" lines carry their figure in ``open_today_bal``, not ``close_today_bal``).

The strict merge core is covered by test_treasury_dts_operating_cash.py; this file
exercises the projection: correct member routing, per-line value column, "null" ->
unavailable, truncation variants dropped (never merged), and a real-corpus
end-to-end count that matches the CH-R51 / taxonomy measurements.
"""
from __future__ import absolute_import

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "live_data"))

import pytest  # noqa: E402

from rmv2_live.adapters import (  # noqa: E402
    SourceUnavailable,
    parse_treasury_dts_operating_cash,
)
from rmv2_live.treasury_dts_operating_cash import (  # noqa: E402
    MERGE_SCHEMA,
    TABLE_NBR,
    TABLE_NM,
    merge_operating_cash_pages,
    serialize_merged_body,
)

CACHE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "research", "prefetch", "dts"
)
AS_OF = "2026-08-06T15:31:00Z"


def _row(account_type, sub_table, record_date, src_line, **cols):
    base = {
        "account_type": account_type,
        "sub_table_name": sub_table,
        "record_date": record_date,
        "src_line_nbr": src_line,
        "table_nbr": TABLE_NBR,
        "table_nm": TABLE_NM,
        "close_today_bal": "null",
        "open_today_bal": "null",
    }
    base.update(cols)
    return base


def _source(members):
    return {
        "adapter": "treasury_dts_operating_cash",
        "source_id": "treasury_dts_operating_cash_current",
        "endpoint": "https://api.fiscaldata.treasury.gov/x/operating_cash_balance",
        "information_set_mode": "current_revised",
        "method_version": "treasury_dts_operating_cash_offline.v1",
        "publisher_release_clock": "daily ~16:00 America/New_York",
        "rights_status": "us_government_public_domain",
        "value_status": "actual",
        "series": {
            "index_label": "Treasury DTS Operating Cash Balance (Table I)",
            "unit": "USD millions",
            "members": members,
        },
    }


def _members():
    return [
        {
            "series_id": "DTS_OCB_FEDERAL_RESERVE_ACCOUNT",
            "account_type": "Federal Reserve Account",
            "value_field": "close_today_bal",
            "label": "legacy Type-of-account line; value from close_today_bal",
        },
        {
            "series_id": "DTS_OCB_TGA_CLOSING_BALANCE",
            "account_type": "Treasury General Account (TGA) Closing Balance",
            "value_field": "open_today_bal",
            "label": "post-2022 Cash Balance Details line; value from open_today_bal",
        },
    ]


def _body(rows):
    merged = {
        "schema_version": MERGE_SCHEMA,
        "table_nbr": TABLE_NBR,
        "table_nm": TABLE_NM,
        "row_count": len(rows),
        "data": rows,
    }
    return serialize_merged_body(merged)


def test_per_member_value_field_and_truncation_drop():
    rows = [
        _row("Federal Reserve Account", "Type of account", "2005-10-03", "1",
             close_today_bal="5448"),
        _row("Treasury General Account (TGA) Closing Balance",
             "Cash Balance Details", "2022-04-18", "4", open_today_bal="841253"),
        # truncation variant -> NOT in member map -> must be dropped, never merged
        _row("Financial Institution Accoun", "Type of account", "2008-12-05", "2",
             close_today_bal="9999"),
    ]
    records = parse_treasury_dts_operating_cash(_source(_members()), _body(rows), AS_OF)
    assert len(records) == 2  # truncation variant dropped
    by_series = {r["series_id"]: r for r in records}
    frb = by_series["DTS_OCB_FEDERAL_RESERVE_ACCOUNT"]
    assert frb["value"] == 5448
    assert frb["dts_value_field"] == "close_today_bal"
    assert frb["observation_period"] == "2005-10-03"
    tga = by_series["DTS_OCB_TGA_CLOSING_BALANCE"]
    assert tga["value"] == 841253  # from open_today_bal, NOT close_today_bal("null")
    assert tga["dts_value_field"] == "open_today_bal"
    # no Financial Institution* series leaked in from the truncation variant
    assert not any("FINANCIAL" in s for s in by_series)


def test_null_value_field_emits_unavailable_but_keeps_the_record():
    rows = [
        _row("Treasury General Account (TGA) Closing Balance",
             "Cash Balance Details", "2022-04-19", "4", open_today_bal="null"),
    ]
    records = parse_treasury_dts_operating_cash(_source(_members()), _body(rows), AS_OF)
    assert len(records) == 1
    assert records[0]["value"] is None
    assert records[0]["value_status"] == "unavailable"


def test_negative_millions_preserved_verbatim():
    members = [{
        "series_id": "DTS_OCB_TGA_TOTAL_WITHDRAWALS",
        "account_type": "Total TGA Withdrawals (Table II) (-)",
        "value_field": "open_today_bal",
        "label": "withdrawals flow; value from open_today_bal",
    }]
    rows = [_row("Total TGA Withdrawals (Table II) (-)", "Cash Balance Details",
                 "2022-04-18", "3", open_today_bal="-12345")]
    records = parse_treasury_dts_operating_cash(_source(members), _body(rows), AS_OF)
    assert records[0]["value"] == -12345


def test_restructure_detector_populated_close_on_cash_balance_details_fails():
    """Condition 2: a 'Cash Balance Details' row whose close_today_bal is populated
    signals a feed restructure and must FAIL, never be silently taken."""
    rows = [
        _row("Treasury General Account (TGA) Closing Balance",
             "Cash Balance Details", "2027-01-01", "4",
             open_today_bal="900000", close_today_bal="900000"),  # both populated
    ]
    with pytest.raises(SourceUnavailable):
        parse_treasury_dts_operating_cash(_source(_members()), _body(rows), AS_OF)


def test_misdeclared_value_field_for_sub_table_fails():
    """Vice versa: a member declaring the wrong value column for its sub_table
    (e.g. close_today_bal on a Cash Balance Details line) is a hard error."""
    members = [{
        "series_id": "DTS_OCB_TGA_CLOSING_BALANCE",
        "account_type": "Treasury General Account (TGA) Closing Balance",
        "value_field": "close_today_bal",  # WRONG: this sub_table requires open_today_bal
        "label": "misconfigured",
    }]
    rows = [_row("Treasury General Account (TGA) Closing Balance",
                 "Cash Balance Details", "2022-04-18", "4", open_today_bal="841253")]
    with pytest.raises(SourceUnavailable):
        parse_treasury_dts_operating_cash(_source(members), _body(rows), AS_OF)


def test_unrecognized_sub_table_fails():
    members = [{
        "series_id": "DTS_OCB_TGA_CLOSING_BALANCE",
        "account_type": "Treasury General Account (TGA) Closing Balance",
        "value_field": "open_today_bal",
        "label": "x",
    }]
    rows = [_row("Treasury General Account (TGA) Closing Balance",
                 "Some New Sub Table", "2027-01-01", "4", open_today_bal="1")]
    with pytest.raises(SourceUnavailable):
        parse_treasury_dts_operating_cash(_source(members), _body(rows), AS_OF)


def test_real_corpus_projection_counts():
    """End-to-end over the 17 cached pages: the 10 clean lines land, the 6
    truncation variants drop, and the modern TGA lines land real values."""
    pages = []
    for i in range(1, 18):
        with open(os.path.join(CACHE_DIR,
                               "operating_cash_balance_p%03d.json" % i)) as fh:
            pages.append(json.load(fh))
    merged = merge_operating_cash_pages(pages)
    body = serialize_merged_body(merged)

    members = [
        ("DTS_OCB_FEDERAL_RESERVE_ACCOUNT", "Federal Reserve Account",
         "close_today_bal"),
        ("DTS_OCB_SUPPLEMENTARY_FINANCING_PROGRAM_ACCOUNT",
         "Supplementary Financing Program Account", "close_today_bal"),
        ("DTS_OCB_SHORT_TERM_CASH_INVESTMENTS",
         "Short-Term Cash Investments (Table V)", "close_today_bal"),
        ("DTS_OCB_TAX_AND_LOAN_NOTE_ACCOUNTS",
         "Tax and Loan Note Accounts (Table V)", "close_today_bal"),
        ("DTS_OCB_FINANCIAL_INSTITUTION_ACCOUNT",
         "Financial Institution Account", "close_today_bal"),
        ("DTS_OCB_TGA", "Treasury General Account (TGA)", "close_today_bal"),
        ("DTS_OCB_TGA_OPENING_BALANCE",
         "Treasury General Account (TGA) Opening Balance", "open_today_bal"),
        ("DTS_OCB_TGA_TOTAL_DEPOSITS", "Total TGA Deposits (Table II)",
         "open_today_bal"),
        ("DTS_OCB_TGA_TOTAL_WITHDRAWALS", "Total TGA Withdrawals (Table II) (-)",
         "open_today_bal"),
        ("DTS_OCB_TGA_CLOSING_BALANCE",
         "Treasury General Account (TGA) Closing Balance", "open_today_bal"),
    ]
    member_dicts = [
        {"series_id": sid, "account_type": at, "value_field": vf, "label": sid}
        for sid, at, vf in members
    ]
    records = parse_treasury_dts_operating_cash(
        _source(member_dicts), body, AS_OF)

    # 15,107 clean rows land (16,498 total minus 1,391 truncation-variant rows).
    assert len(records) == 15107
    landed_series = {r["series_id"] for r in records}
    assert len(landed_series) == 10
    unavailable = sum(1 for r in records if r["value_status"] == "unavailable")
    assert unavailable == 0  # every clean line now draws a populated column
    # the modern TGA closing balance is a real number, not the "null" it holds in
    # close_today_bal.
    tga_close = [r for r in records
                 if r["series_id"] == "DTS_OCB_TGA_CLOSING_BALANCE"]
    assert len(tga_close) == 1077
    assert all(isinstance(r["value"], (int, float)) for r in tga_close)
