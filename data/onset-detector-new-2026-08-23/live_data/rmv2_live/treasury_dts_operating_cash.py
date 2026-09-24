"""Strict normalization for the U.S. Treasury Daily Treasury Statement (DTS)
Table I "Operating Cash Balance", from the prefetch-cached fiscaldata JSON pages.

B-OFFLINE-3 item 2. The cached corpus is 17 paginated fiscaldata responses of the
``.../dts/operating_cash_balance`` endpoint (Table I only). The director's revised
item-2 ruling requires the 17 pages be merged into ONE canonical body BEFORE any
bind, with the merge (a) deterministic, (b) explicitly de-duplicating page-boundary
overlaps, (c) byte-identical across runs and page-order shuffles. It must REJECT a
Table-II body (the withheld-tax deposits table that the OTHER, hard-bound
``parse_treasury_dts_json`` adapter serves) rather than silently mis-parse it.

This module performs NO network I/O and holds NO account -> series identity map:
the account-series identity across the 2021/2022 DTS format change (Federal Reserve
Account -> Treasury General Account opening/closing/deposits/withdrawals) plus the
truncated account_type variants are an owner/identity question filed separately.
The merge here is identity-neutral: it preserves every published row verbatim under
its exact ``account_type`` string and makes no cross-format identity claim.
"""
from __future__ import absolute_import

import json


TABLE_NBR = "I"
TABLE_NM = "Operating Cash Balance"
MERGE_SCHEMA = "recession-monitor-v2.treasury-dts-operating-cash-merged.v1"

# The natural key that CH-R51 measured to be unique across all 17 pages
# (16,498 distinct == 16,498 total rows, zero conflicting values).
_KEY_FIELDS = ("record_date", "account_type", "src_line_nbr")


class TreasuryDtsOperatingCashError(ValueError):
    """Raised when the cached DTS bytes fail the reviewed Table-I contract."""


def _require(condition, message):
    if not condition:
        raise TreasuryDtsOperatingCashError(message)


def _row_key(row):
    return tuple(row[field] for field in _KEY_FIELDS)


def _validate_row(row):
    _require(isinstance(row, dict), "DTS row was not an object")
    for field in _KEY_FIELDS:
        value = row.get(field)
        _require(isinstance(value, str) and value != "",
                 "DTS row lacked a valid %s" % field)
    table_nbr = row.get("table_nbr")
    table_nm = row.get("table_nm")
    # The strict Table-I guard: a Table-II (or any non-Table-I) body is rejected
    # here, so the withheld-tax deposits table cannot be silently mis-parsed as
    # an operating-cash-balance body.
    _require(
        table_nbr == TABLE_NBR and table_nm == TABLE_NM,
        "DTS row is not Table I 'Operating Cash Balance' (table_nbr=%r "
        "table_nm=%r) -- refusing to mis-parse a non-Table-I body"
        % (table_nbr, table_nm),
    )


def merge_operating_cash_pages(pages):
    """Merge the 17 cached fiscaldata pages into ONE canonical Table-I body.

    ``pages`` is a list of parsed fiscaldata page objects (each with a ``data``
    list). Returns a canonical dict ``{schema_version, table_nbr, table_nm,
    row_count, data}`` where ``data`` is the de-duplicated, deterministically
    sorted union of every page's rows. The result is invariant to page order and
    identical across runs (so its serialized bytes are a stable bound-body sha).

    De-duplication is by the (record_date, account_type, src_line_nbr) natural
    key: a byte-identical repeat at a page boundary collapses to one row; two
    rows sharing a key with DIFFERENT content are a hard error (a real conflict
    the merge must never paper over). Any non-Table-I row fails the whole merge.
    """
    _require(isinstance(pages, list) and pages,
             "DTS merge requires a non-empty list of pages")
    by_key = {}
    for page in pages:
        _require(isinstance(page, dict), "DTS page was not an object")
        data = page.get("data")
        _require(isinstance(data, list) and data,
                 "DTS page lacked a non-empty data array")
        for row in data:
            _validate_row(row)
            key = _row_key(row)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = dict(row)
            elif existing != row:
                raise TreasuryDtsOperatingCashError(
                    "DTS merge found conflicting values for key %r" % (key,)
                )
            # else: byte-identical boundary overlap -> keep one copy.
    merged_rows = [by_key[key] for key in sorted(by_key, key=_sort_key)]
    return {
        "schema_version": MERGE_SCHEMA,
        "table_nbr": TABLE_NBR,
        "table_nm": TABLE_NM,
        "row_count": len(merged_rows),
        "data": merged_rows,
    }


def _sort_key(key):
    record_date, account_type, src_line_nbr = key
    # src_line_nbr sorts numerically when it is an integer string, else lexically;
    # the (date, line, account) order is stable and independent of input order.
    try:
        line_sort = (0, int(src_line_nbr))
    except (TypeError, ValueError):
        line_sort = (1, src_line_nbr)
    return (record_date, line_sort, account_type)


def serialize_merged_body(merged):
    """Serialize a merged canonical body to the exact bytes that get bound.

    Deterministic (sorted keys, compact separators) so the byte string — and thus
    its sha256 — is identical across runs and page-order shuffles. The offline
    binder stores THESE bytes as the source object and the DTS adapter parses THESE
    bytes back; they must be produced by one function so the bound sha and the
    re-parse never diverge.
    """
    return json.dumps(merged, sort_keys=True, separators=(",", ":")).encode("utf-8")
