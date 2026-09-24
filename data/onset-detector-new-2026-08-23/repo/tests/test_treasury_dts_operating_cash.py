"""B-OFFLINE-3 item 2 — strict DTS Table I (Operating Cash Balance) parser + the
17-page deterministic merge, per the director's revised item-2 ruling.

These cover the RULING-INVARIANT core: the merge is deterministic and page-order
invariant, boundary overlaps are explicitly de-duplicated, and a Table-II body is
REJECTED rather than silently mis-parsed. The account -> series projection (which
depends on the pending account-identity ruling) is not exercised here.
"""
from __future__ import absolute_import

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "live_data"))

from rmv2_live.treasury_dts_operating_cash import (  # noqa: E402
    TreasuryDtsOperatingCashError,
    merge_operating_cash_pages,
)

CACHE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "research", "prefetch", "dts"
)

# CH-R51 measured invariants of the cached corpus.
EXPECTED_ROWS = 16498
EXPECTED_DATES = 5234


def _load_pages():
    pages = []
    for i in range(1, 18):
        path = os.path.join(CACHE_DIR, "operating_cash_balance_p%03d.json" % i)
        with open(path) as handle:
            pages.append(json.load(handle))
    return pages


def _small_table_i_page(rows):
    return {"data": rows, "meta": {"total-pages": 1}, "links": {}}


def _row(date, acct, line, close, table="I"):
    return {
        "record_date": date,
        "account_type": acct,
        "close_today_bal": close,
        "open_today_bal": close,
        "open_month_bal": close,
        "open_fiscal_year_bal": close,
        "table_nbr": table,
        "table_nm": "Operating Cash Balance" if table == "I" else "Deposits",
        "sub_table_name": "Type of account",
        "src_line_nbr": line,
        "record_fiscal_year": "2006",
        "record_fiscal_quarter": "1",
        "record_calendar_year": date[:4],
        "record_calendar_quarter": "4",
        "record_calendar_month": date[5:7],
        "record_calendar_day": date[8:10],
    }


def test_merge_of_real_corpus_matches_measured_invariants():
    merged = merge_operating_cash_pages(_load_pages())
    assert merged["table_nbr"] == "I"
    assert merged["row_count"] == EXPECTED_ROWS
    assert len(merged["data"]) == EXPECTED_ROWS
    dates = {r["record_date"] for r in merged["data"]}
    assert len(dates) == EXPECTED_DATES
    assert all(r["table_nbr"] == "I" for r in merged["data"])
    assert all(r["table_nm"] == "Operating Cash Balance" for r in merged["data"])


def test_merge_is_byte_identical_across_two_runs():
    pages = _load_pages()
    a = merge_operating_cash_pages(pages)
    b = merge_operating_cash_pages(_load_pages())
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_merge_is_invariant_to_page_order():
    pages = _load_pages()
    shuffled = list(reversed(pages))
    a = merge_operating_cash_pages(pages)
    b = merge_operating_cash_pages(shuffled)
    assert a == b


def test_merge_dedupes_a_byte_identical_boundary_overlap():
    r1 = _row("2020-01-02", "Federal Reserve Account", "1", "100")
    r2 = _row("2020-01-02", "Treasury General Account (TGA)", "2", "200")
    page_a = _small_table_i_page([r1, r2])
    page_b = _small_table_i_page([copy.deepcopy(r2)])  # r2 repeated at boundary
    merged = merge_operating_cash_pages([page_a, page_b])
    assert merged["row_count"] == 2  # r2 de-duplicated, not doubled


def test_merge_rejects_conflicting_values_for_same_key():
    r1 = _row("2020-01-02", "Federal Reserve Account", "1", "100")
    r2 = _row("2020-01-02", "Federal Reserve Account", "1", "999")  # same key, diff value
    with pytest.raises(TreasuryDtsOperatingCashError):
        merge_operating_cash_pages([_small_table_i_page([r1]),
                                    _small_table_i_page([r2])])


def test_merge_rejects_a_table_two_body():
    r = _row("2020-01-02", "Total Withheld Income and Employment Taxes", "1",
             "5000", table="II")
    with pytest.raises(TreasuryDtsOperatingCashError):
        merge_operating_cash_pages([_small_table_i_page([r])])


def test_merge_rejects_mixed_table_page():
    good = _row("2020-01-02", "Federal Reserve Account", "1", "100")
    bad = _row("2020-01-02", "Total TGA Deposits (Table II)", "2", "50",
               table="II")
    with pytest.raises(TreasuryDtsOperatingCashError):
        merge_operating_cash_pages([_small_table_i_page([good, bad])])


def test_merge_rejects_empty_input():
    with pytest.raises(TreasuryDtsOperatingCashError):
        merge_operating_cash_pages([])


def test_merge_sorted_deterministically():
    r1 = _row("2020-01-03", "Federal Reserve Account", "1", "100")
    r2 = _row("2020-01-02", "Federal Reserve Account", "1", "90")
    merged = merge_operating_cash_pages([_small_table_i_page([r1, r2])])
    assert [r["record_date"] for r in merged["data"]] == ["2020-01-02",
                                                          "2020-01-03"]
