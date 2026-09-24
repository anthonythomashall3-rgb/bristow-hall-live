"""HTTPS retrieval and deterministic normalization for admitted live sources."""

from __future__ import absolute_import

import io
import csv
import zipfile
import calendar
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .canonical import CanonicalDataError
from .census_btos import (
    CensusBtosDataError,
    parse_census_btos_xlsx as parse_census_btos_source_xlsx,
)
from .census_qss import (
    CensusQssDataError,
    parse_census_qss_zip as parse_census_qss_source_zip,
)
from .cfpb_credit_trends import (
    CfpbCreditTrendsDataError,
    parse_cfpb_credit_trends_csv as parse_cfpb_credit_trends_source_csv,
)
from .cfpb_mortgage import (
    CfpbMortgageDataError,
    parse_cfpb_mortgage_performance_state_csv as
    parse_cfpb_mortgage_source_csv,
)
from .cleveland_nowcast import (
    ClevelandNowcastDataError,
    parse_cleveland_nowcast_json as parse_cleveland_nowcast_source_json,
)
from .nber_macrohistory import (
    NberMacrohistoryDataError,
    parse_nber_macrohistory_dat as parse_nber_macrohistory_dat_bytes,
)
from .dallas_wei import (
    DallasWeiDataError,
    parse_dallas_wei_workbook,
)
from .philadelphia_ads import (
    PhiladelphiaAdsDataError,
    parse_philadelphia_ads_workbook,
)
from .forecast_xlsx import (
    ForecastXlsxDataError,
    parse_forecast_xlsx_bytes,
)
from .greenbook_row import (
    GreenbookRowDataError,
    parse_greenbook_row_workbook,
)
from .atsix_termstructure import (
    AtsixShapeError,
    parse_sheet as parse_atsix_sheet,
)
from .fed_ddp import (
    FedDdpDataError,
    parse_fed_ddp_csv as parse_fed_ddp_source_csv,
)
from .fema_disasters import (
    FemaDisasterDataError,
    parse_fema_disaster_declarations_json as
    parse_fema_disaster_declarations_source_json,
)
from .regional_survey import (
    RegionalSurveyDataError,
    parse_regional_survey_xlsx as parse_regional_survey_source_xlsx,
)
from .treasury_dts import (
    ENDPOINT as TREASURY_DTS_ENDPOINT,
    METHOD_VERSION as TREASURY_DTS_METHOD_VERSION,
    SOURCE_ID as TREASURY_DTS_SOURCE_ID,
    TreasuryDtsDataError,
    parse_treasury_dts_json as parse_treasury_dts_current_json,
)
from .treasury_dts_operating_cash import (
    MERGE_SCHEMA as TREASURY_DTS_OC_MERGE_SCHEMA,
    TABLE_NBR as TREASURY_DTS_OC_TABLE_NBR,
    TABLE_NM as TREASURY_DTS_OC_TABLE_NM,
    TreasuryDtsOperatingCashError,
)


class SourceUnavailable(RuntimeError):
    pass


class SourceBlocked(RuntimeError):
    pass


SECRET_REDACTION_PLACEHOLDER = b"__REDACTED_SECRET__"


def redact_secret_from_body(raw, secret_value):
    """Replace an echoed API secret in a response body with a fixed placeholder.

    Some keyed publishers (BEA GetData, EIA v2) echo the submitted key back
    inside the response body. Redacting it before the body is hashed, persisted
    as probe evidence, or normalized keeps a credential from resting on disk.
    Parsers ignore the echoed request block, so the emitted observations are
    unchanged.
    """
    if not secret_value:
        return raw
    secret_bytes = secret_value.encode("utf-8")
    if secret_bytes and secret_bytes in raw:
        return raw.replace(secret_bytes, SECRET_REDACTION_PLACEHOLDER)
    return raw


def strict_publisher_json_loads(data):
    """Decode publisher JSON without binary floating-point conversion."""
    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="strict")
    elif isinstance(data, str):
        text = data
    else:
        raise TypeError("publisher JSON requires bytes or str")

    def pairs_hook(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SourceUnavailable("duplicate publisher JSON key: %s" % key)
            result[key] = value
        return result

    def reject_constant(token):
        raise SourceUnavailable("non-finite publisher JSON number: %s" % token)

    try:
        return json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=str,
            parse_int=str,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceUnavailable("invalid publisher JSON: %s" % exc)


class UnsafeRedirectHandler(HTTPRedirectHandler):
    """Reject redirects outside the exact publisher host allowlist."""

    def __init__(self, allowed_hosts):
        HTTPRedirectHandler.__init__(self)
        self.allowed_hosts = frozenset(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise SourceBlocked("redirect left the publisher allowlist")
        return HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


class HttpResponse(object):
    def __init__(
        self,
        url,
        status,
        headers,
        body,
        request_body_sha256=None,
        request_headers=None,
        request_method="GET",
        request_parameters=None,
    ):
        self.url = url
        self.status = status
        self.headers = headers
        self.body = body
        self.request_body_sha256 = request_body_sha256
        self.request_headers = request_headers or {}
        self.request_method = request_method
        self.request_parameters = request_parameters or {}


class PublisherHttpClient(object):
    USER_AGENT = "RecessionMonitorV2/1.0 publisher-direct local collector"
    CLEVELAND_BROWSER_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    )

    def fetch(self, source, now=None, conditional_headers=None):
        secret_name = source.get("secret_env")
        if secret_name and source["secret_required"] and not os.environ.get(secret_name):
            raise SourceBlocked("missing required secret %s" % secret_name)

        current_year = (now or datetime.now(timezone.utc)).year
        endpoint = source["endpoint"].format(year=current_year)
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or parsed.hostname not in source["allowed_hosts"]:
            raise SourceBlocked("request URL is outside the source allowlist")

        user_agent = (
            self.CLEVELAND_BROWSER_USER_AGENT
            if source["adapter"] == "cleveland_nowcast_json"
            else self.USER_AGENT
        )
        headers = {
            "Accept": ", ".join(source["expected_content_types"]),
            "User-Agent": user_agent,
        }
        conditional_headers = conditional_headers or {}
        allowed_conditional_headers = {
            "If-Modified-Since",
            "If-None-Match",
        }
        if set(conditional_headers) - allowed_conditional_headers:
            raise SourceBlocked("unsupported conditional request header")
        for name in sorted(conditional_headers):
            value = conditional_headers[name]
            if not isinstance(value, str) or "\r" in value or "\n" in value:
                raise SourceBlocked("unsafe conditional request header")
        body = None
        method = "GET"
        request_parameters = {}
        if source["adapter"] == "bls_json":
            method = "POST"
            history_years = int(source["series"].get("history_years", 3))
            payload = {
                "seriesid": [item["series_id"] for item in source["series"]["items"]],
                "startyear": str(current_year - history_years + 1),
                "endyear": str(current_year),
            }
            if secret_name and os.environ.get(secret_name):
                payload["registrationkey"] = os.environ[secret_name]
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
            request_parameters = {
                "endyear": payload["endyear"],
                "seriesid": payload["seriesid"],
                "startyear": payload["startyear"],
            }
        if source["adapter"] == "dol_ui_weekly_claims_report_html":
            method = "POST"
            # report.asp returns the requested year's 52 week-ending rows; it caps
            # to final_yr regardless of strtdate, so the current lane pulls the
            # current calendar year. Keyless — no secret on the wire.
            form = {
                "enddate": "12/31/%d" % current_year,
                "filetype": "html",
                "final_yr": str(current_year),
                "level": "us",
                "strtdate": "01/01/%d" % current_year,
                "submit": "Submit",
            }
            body = urlencode(sorted(form.items())).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            request_parameters = dict(form)
        if method == "GET":
            for name in sorted(conditional_headers):
                headers[name] = conditional_headers[name]
        else:
            conditional_headers = {}

        request_endpoint = endpoint
        stored_url = None  # keyless URL to persist; None -> use final_url
        if source["adapter"] == "fred_json_api":
            if not (secret_name and os.environ.get(secret_name)):
                raise SourceBlocked("FRED JSON API requires its API key")
            separator = "&" if "?" in endpoint else "?"
            request_endpoint = "%s%sapi_key=%s" % (
                endpoint,
                separator,
                quote(os.environ[secret_name], safe=""),
            )
            stored_url = endpoint  # never persist the keyed request URL
        if source["adapter"] == "census_api":
            if not (secret_name and os.environ.get(secret_name)):
                raise SourceBlocked("Census API requires its API key")
            separator = "&" if "?" in endpoint else "?"
            request_endpoint = "%s%skey=%s" % (
                endpoint,
                separator,
                quote(os.environ[secret_name], safe=""),
            )
            stored_url = endpoint  # never persist the keyed request URL
        if source["adapter"] == "bea_api":
            if not (secret_name and os.environ.get(secret_name)):
                raise SourceBlocked("BEA API requires its UserID key")
            separator = "&" if "?" in endpoint else "?"
            request_endpoint = "%s%sUserID=%s" % (
                endpoint,
                separator,
                quote(os.environ[secret_name], safe=""),
            )
            stored_url = endpoint  # never persist the keyed request URL
        if source["adapter"] == "eia_v2_json":
            if not (secret_name and os.environ.get(secret_name)):
                raise SourceBlocked("EIA API requires its api_key")
            separator = "&" if "?" in endpoint else "?"
            request_endpoint = "%s%sapi_key=%s" % (
                endpoint,
                separator,
                quote(os.environ[secret_name], safe=""),
            )
            stored_url = endpoint  # never persist the keyed request URL
        if source["adapter"] in ("fred_json_api_vintages", "fred_json_api_vintages_deep"):
            # ALFRED vintage matrix lane (output_type=2). Same keyed-GET,
            # keyless-persist hygiene as fred_json_api: the API key is appended
            # to the WIRE url only; stored_url is forced keyless so provenance,
            # receipts, and probe evidence never carry the credential. The
            # config endpoint must already request output_type=2 (the parser
            # refuses any other output_type), so the vintage matrix is never
            # spliced onto the current lane.
            if not (secret_name and os.environ.get(secret_name)):
                raise SourceBlocked("FRED vintage API requires its API key")
            if "output_type=2" not in endpoint:
                raise SourceBlocked("FRED vintage lane endpoint must request output_type=2")
            separator = "&" if "?" in endpoint else "?"
            request_endpoint = "%s%sapi_key=%s" % (
                endpoint,
                separator,
                quote(os.environ[secret_name], safe=""),
            )
            stored_url = endpoint  # never persist the keyed request URL
        opener = build_opener(UnsafeRedirectHandler(source["allowed_hosts"]))
        request = Request(request_endpoint, data=body, headers=headers, method=method)
        try:
            with opener.open(request, timeout=30) as response:
                final_url = response.geturl()
                final_host = urlparse(final_url).hostname
                if final_host not in source["allowed_hosts"]:
                    raise SourceBlocked("final response host is not allowlisted")
                limit = source["max_bytes"]
                raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise SourceUnavailable("publisher response exceeded max_bytes")
                # Some keyed publishers (BEA GetData, EIA v2) echo the submitted
                # API key back inside the response body's request block. Redact
                # the secret before the body is ever hashed, persisted as probe
                # evidence, or normalized. Parsers ignore the echoed request
                # block, so redaction cannot change any emitted observation; it
                # only prevents a credential from resting in a fixture on disk.
                if secret_name and os.environ.get(secret_name):
                    raw = redact_secret_from_body(raw, os.environ[secret_name])
                response_headers = {
                    str(key).lower(): str(value)
                    for key, value in response.headers.items()
                }
                result = HttpResponse(
                    stored_url or final_url,
                    int(getattr(response, "status", response.getcode())),
                    response_headers,
                    raw,
                    request_body_sha256=(
                        hashlib.sha256(body).hexdigest()
                        if body is not None else None
                    ),
                    request_headers={
                        key: conditional_headers[key]
                        for key in sorted(conditional_headers)
                    },
                    request_method=method,
                    request_parameters=request_parameters,
                )
        except HTTPError as exc:
            if exc.code == 304:
                final_url = exc.geturl() or endpoint
                if urlparse(final_url).hostname not in source["allowed_hosts"]:
                    raise SourceBlocked("304 response host is not allowlisted")
                response_headers = {
                    str(key).lower(): str(value)
                    for key, value in exc.headers.items()
                }
                return HttpResponse(
                    stored_url or final_url,
                    304,
                    response_headers,
                    b"",
                    request_body_sha256=(
                        hashlib.sha256(body).hexdigest()
                        if body is not None else None
                    ),
                    request_headers={
                        key: conditional_headers[key]
                        for key in sorted(conditional_headers)
                    },
                    request_method=method,
                    request_parameters=request_parameters,
                )
            raise SourceUnavailable("publisher returned HTTP %s" % exc.code)
        validate_response(source, result)
        return result


def validate_response(source, response):
    if response.status == 304:
        if response.body:
            raise SourceUnavailable("HTTP 304 response unexpectedly contained a body")
        return
    if response.status != 200:
        raise SourceUnavailable("publisher response was not HTTP 200")
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    allowed = tuple(item.lower() for item in source["expected_content_types"])
    if content_type not in allowed and not any(
        content_type.startswith(item.rstrip("*")) for item in allowed if item.endswith("*")
    ):
        raise SourceUnavailable("unexpected content type %r" % content_type)
    prefix = response.body[:512].lstrip().lower()
    if (
        (
            prefix.startswith(b"<!doctype html") or
            prefix.startswith(b"<html")
        ) and
        source["adapter"] not in (
            "tsa_passenger_html",
            "dol_ui_weekly_claims_report_html",
        )
    ):
        raise SourceUnavailable("publisher returned HTML instead of data")
    if not response.body:
        raise SourceUnavailable("publisher returned an empty body")


def _base_record(source, series_id, reference_period, value, unit, retrieved_at):
    return {
        "available_at": retrieved_at,
        "forecast_horizon": None,
        "forecast_origin": None,
        "information_set_mode": source["information_set_mode"],
        "method_version": source["method_version"],
        "observation_period": reference_period,
        "observed_at": reference_period,
        "provenance_url": source["endpoint"],
        "publisher_release_clock": source["publisher_release_clock"],
        "release_at": None,
        "revision_sequence": None,
        "rights_status": source["rights_status"],
        "series_id": series_id,
        "source_id": source["source_id"],
        "unit": unit,
        "value": value,
        "value_status": source["value_status"],
    }


def parse_treasury_yield_xml(source, body, retrieved_at):
    upper_prefix = body[:4096].upper()
    if b"<!DOCTYPE" in upper_prefix or b"<!ENTITY" in upper_prefix:
        raise SourceUnavailable("Treasury XML declarations are prohibited")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise SourceUnavailable("invalid Treasury XML: %s" % exc)
    data_ns = "http://schemas.microsoft.com/ado/2007/08/dataservices"
    metadata_ns = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
    atom_ns = "http://www.w3.org/2005/Atom"
    records = []
    ignored = frozenset(("Id", "NEW_DATE", "BC_30YEARDISPLAY"))
    allowed_fields = frozenset((
        "BC_1MONTH",
        "BC_1_5MONTH",
        "BC_2MONTH",
        "BC_3MONTH",
        "BC_4MONTH",
        "BC_6MONTH",
        "BC_1YEAR",
        "BC_2YEAR",
        "BC_3YEAR",
        "BC_5YEAR",
        "BC_7YEAR",
        "BC_10YEAR",
        "BC_20YEAR",
        "BC_30YEAR",
    ))
    for entry in root.findall("{%s}entry" % atom_ns):
        props = entry.find(".//{%s}properties" % metadata_ns)
        if props is None:
            continue
        row = {}
        for child in list(props):
            tag = child.tag.rsplit("}", 1)[-1]
            row[tag] = child.text
        raw_date = row.get("NEW_DATE")
        if (
            not raw_date or
            not re.match(r"^\d{4}-\d{2}-\d{2}(?:T.*)?$", raw_date)
        ):
            continue
        try:
            datetime.strptime(raw_date[:10], "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("Treasury XML contained an invalid date")
        reference_period = raw_date[:10]
        for field in sorted(set(row) - ignored):
            value = row[field]
            if value is None or not field.startswith("BC_"):
                continue
            if field not in allowed_fields:
                raise SourceUnavailable("Treasury XML contained an unknown yield field")
            if not re.match(r"^-?\d+(?:\.\d+)?$", value):
                raise SourceUnavailable("Treasury XML contained a non-decimal yield")
            record = _base_record(
                source,
                "%s.%s" % (source["source_id"], field),
                reference_period,
                value,
                "percent",
                retrieved_at,
            )
            record["publisher_field"] = field
            records.append(record)
    if not records:
        raise SourceUnavailable("Treasury XML contained no yield observations")
    return records


def parse_nyfed_reference_rate_json(source, body, retrieved_at):
    payload = strict_publisher_json_loads(body)
    rows = payload.get("refRates")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("NY Fed response contained no refRates")
    records = []
    units = {
        "percentRate": "percent",
        "percentPercentile1": "percent",
        "percentPercentile25": "percent",
        "percentPercentile75": "percent",
        "percentPercentile99": "percent",
        "targetRateFrom": "percent",
        "targetRateTo": "percent",
        "volumeInBillions": "USD billions",
    }
    for row in rows:
        if not isinstance(row, dict):
            raise SourceUnavailable("NY Fed refRates rows must be objects")
        reference_period = row.get("effectiveDate")
        rate_type = row.get("type")
        if not reference_period or not rate_type:
            raise SourceUnavailable("NY Fed rate row lacked identity")
        try:
            datetime.strptime(reference_period, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("NY Fed rate row had an invalid date")
        expected_type = {
            "nyfed_effr_current": "EFFR",
            "nyfed_sofr_current": "SOFR",
        }.get(source.get("method_version"))
        if expected_type is not None and rate_type != expected_type:
            raise SourceUnavailable("NY Fed returned the wrong reference-rate type")
        for field in sorted(units):
            if field not in row or row[field] is None:
                continue
            value = str(row[field])
            record = _base_record(
                source,
                "%s.%s.%s" % (source["source_id"], rate_type, field),
                reference_period,
                value,
                units[field],
                retrieved_at,
            )
            record["revision_indicator"] = row.get("revisionIndicator") or ""
            records.append(record)
    if not records:
        raise SourceUnavailable("NY Fed response contained no measurements")
    return records


def parse_bls_json(source, body, retrieved_at):
    payload = strict_publisher_json_loads(body)
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise SourceUnavailable("BLS API status was not REQUEST_SUCCEEDED")
    results = payload.get("Results")
    if not isinstance(results, dict):
        raise SourceUnavailable("BLS response lacked Results")
    series_rows = results.get("series")
    if not isinstance(series_rows, list):
        raise SourceUnavailable("BLS response lacked series")
    metadata = {
        item["series_id"]: item
        for item in source["series"]["items"]
    }
    returned_ids = [series.get("seriesID") for series in series_rows]
    if (
        any(not isinstance(series_id, str) for series_id in returned_ids) or
        len(returned_ids) != len(set(returned_ids))
    ):
        raise SourceUnavailable("BLS returned duplicate or invalid series identities")
    if set(returned_ids) != set(metadata):
        raise SourceUnavailable("BLS returned an incomplete or unexpected series set")
    records = []
    for series in series_rows:
        if not isinstance(series, dict):
            raise SourceUnavailable("BLS series rows must be objects")
        series_id = series.get("seriesID")
        if series_id not in metadata:
            raise SourceUnavailable("BLS returned an unrequested series")
        details = metadata[series_id]
        data_rows = series.get("data")
        if not isinstance(data_rows, list):
            raise SourceUnavailable("BLS series lacked a data list")
        for row in data_rows:
            if not isinstance(row, dict):
                raise SourceUnavailable("BLS data rows must be objects")
            period = row.get("period")
            year = row.get("year")
            if not year or not isinstance(period, str) or not re.match(r"^M(0[1-9]|1[0-2])$", period):
                continue
            reference_period = "%s-%s" % (year, period[1:])
            value = row.get("value")
            unavailable = value in (None, "", "-")
            record = _base_record(
                source,
                "%s.%s" % (source["source_id"], series_id),
                reference_period,
                None if unavailable else str(value),
                details["unit"],
                retrieved_at,
            )
            record["label"] = details["label"]
            latest_marker = row.get("latest")
            if latest_marker is None:
                latest = False
            elif type(latest_marker) is str and latest_marker == "true":
                latest = True
            else:
                raise SourceUnavailable(
                    "BLS latest marker was outside the publisher token domain"
                )
            footnotes = row.get("footnotes", [])
            if not isinstance(footnotes, list):
                raise SourceUnavailable("BLS footnotes were not a list")
            for footnote in footnotes:
                if footnote is not None and not isinstance(footnote, dict):
                    raise SourceUnavailable(
                        "BLS footnote entries must be objects or null"
                    )
                if footnote is not None:
                    for field in ("code", "text"):
                        value = footnote.get(field)
                        if value is not None and type(value) is not str:
                            raise SourceUnavailable(
                                "BLS footnote %s must be a string or null" %
                                field
                            )
            record["latest_observation"] = latest
            record["preliminary"] = any(
                (footnote or {}).get("code") == "P"
                for footnote in footnotes
            )
            record["publisher_footnotes"] = [
                {
                    "code": (footnote or {}).get("code") or "",
                    "text": (footnote or {}).get("text") or "",
                }
                for footnote in footnotes
                if (footnote or {}).get("code") or (footnote or {}).get("text")
            ]
            if unavailable:
                record["value_status"] = "unavailable"
            records.append(record)
    if not records:
        raise SourceUnavailable("BLS response contained no monthly observations")
    return records


def _publisher_date(value):
    value = (value or "").strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%m%d%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def parse_dol_eta539_csv(source, body, retrieved_at):
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("DOL ETA-539 CSV was not valid UTF-8: %s" % exc)
    reader = csv.DictReader(io.StringIO(text))
    expected = {
        "st",
        "rptdate",
        "c2",
        "c3",
        "c8",
        "c17",
        "c18",
        "c19",
        "c20",
        "c21",
        "c22",
        "c23",
    }
    if reader.fieldnames is None or not expected.issubset(set(reader.fieldnames)):
        raise SourceUnavailable("DOL ETA-539 CSV header was incomplete")
    grouped = {}
    for row in reader:
        state = (row.get("st") or "").strip().upper()
        report_date = _publisher_date(row.get("rptdate"))
        reflected_week = _publisher_date(row.get("c2"))
        if not state or not report_date or not reflected_week:
            continue
        item = {
            "report_date": report_date,
            "reflected_week": reflected_week,
            "row": row,
            "state": state,
        }
        grouped.setdefault(state, []).append(item)
    keep = int(source["series"].get("retention_rows_per_state", 160))
    count_measurements = {
        "c3": ("initial_claims", "claims"),
        "c8": ("continued_weeks_claimed", "continued weeks"),
        "c17": (
            "average_adjusted_total_continued_weeks_claimed",
            "continued weeks",
        ),
        "c18": ("covered_employment", "persons"),
    }
    rate_measurements = {
        "c19": ("insured_unemployment_rate_current_13_week", "percent"),
        "c20": (
            "insured_unemployment_rate_prior_year_average",
            "percent",
        ),
        "c21": (
            "current_rate_as_percent_of_prior_year_average",
            "percent",
        ),
    }
    measurements = dict(count_measurements)
    measurements.update(rate_measurements)
    records = []
    for state, items in sorted(grouped.items()):
        items.sort(key=lambda item: (item["report_date"], item["reflected_week"]))
        for item in items[-keep:]:
            row = item["row"]
            for field, (label, unit) in sorted(measurements.items()):
                raw_value = (row.get(field) or "").strip()
                unavailable = not raw_value or raw_value in ("-", ".")
                if not unavailable:
                    if field in count_measurements:
                        valid = re.match(r"^\d+$", raw_value)
                        error = "non-integer count"
                    else:
                        valid = re.match(r"^\d+(?:\.\d+)?$", raw_value)
                        error = "non-canonical rate"
                    if not valid:
                        raise SourceUnavailable(
                            "DOL ETA-539 contained a %s in %s" %
                            (error, field)
                        )
                record = _base_record(
                    source,
                    "%s.%s.%s" % (source["source_id"], state, label),
                    item["reflected_week"],
                    None if unavailable else raw_value,
                    unit,
                    retrieved_at,
                )
                record["publisher_report_date"] = item["report_date"]
                record["publisher_field"] = field
                record["publisher_status"] = (row.get("c22") or "").strip()
                record["publisher_status_change_date"] = _publisher_date(row.get("c23"))
                record["state"] = state
                if unavailable:
                    record["value_status"] = "unavailable"
                records.append(record)
    if not records:
        raise SourceUnavailable("DOL ETA-539 CSV contained no usable state rows")
    return records


def parse_fred_graph_csv(source, body, retrieved_at):
    """Parse one exact FRED graph series without implying first-release proof."""
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("FRED graph CSV was not valid UTF-8: %s" % exc)

    series = source.get("series")
    expected_series_fields = frozenset(("label", "series_id", "unit"))
    if (
        not isinstance(series, dict) or
        frozenset(series) != expected_series_fields
    ):
        raise SourceUnavailable("FRED graph series metadata was not exact")
    series_id = series["series_id"]
    if (
        not isinstance(series_id, str) or
        not re.match(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$", series_id)
    ):
        raise SourceUnavailable("FRED graph series_id was invalid")
    if (
        not isinstance(series["label"], str) or not series["label"] or
        not isinstance(series["unit"], str) or not series["unit"]
    ):
        raise SourceUnavailable("FRED graph series label or unit was invalid")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != ["observation_date", series_id]:
        raise SourceUnavailable("FRED graph CSV header was not exact")

    records = []
    seen_dates = set()
    available_count = 0
    for row in reader:
        if row.get(None):
            raise SourceUnavailable("FRED graph CSV row contained extra fields")
        reference_period = row.get("observation_date")
        if not isinstance(reference_period, str):
            raise SourceUnavailable("FRED graph CSV date was missing")
        try:
            parsed_date = datetime.strptime(reference_period, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("FRED graph CSV date was invalid")
        if parsed_date.strftime("%Y-%m-%d") != reference_period:
            raise SourceUnavailable("FRED graph CSV date was not canonical")
        if reference_period in seen_dates:
            raise SourceUnavailable("FRED graph CSV contained a duplicate date")
        seen_dates.add(reference_period)

        raw_value = row.get(series_id)
        if not isinstance(raw_value, str):
            raise SourceUnavailable("FRED graph CSV value was missing")
        raw_value = raw_value.strip()
        unavailable = raw_value in ("", ".")
        if not unavailable and not re.match(r"^-?\d+(?:\.\d+)?$", raw_value):
            raise SourceUnavailable("FRED graph CSV value was not canonical decimal")

        record = _base_record(
            source,
            series_id,
            reference_period,
            None if unavailable else raw_value,
            series["unit"],
            retrieved_at,
        )
        record["label"] = series["label"]
        record["provider_vintage_kind"] = "current_revised"
        record["strict_publisher_first_release_proven"] = False
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("FRED graph CSV contained no available observations")
    return records


# Census missing-data sentinels: null, empty, and the large-negative family.
_CENSUS_MISSING_SENTINELS = frozenset((
    "-666666666", "-888888888", "-999999999",
    "-222222222", "-333333333", "-555555555",
    # "Z" is a Census EITS availability flag ("less than half the unit shown"):
    # not a numeric cell_value. Present in marts/mtis/m3, absent from resconst.
    # Treated as unavailable rather than fabricating a rounded-to-zero value.
    "Z",
))


def parse_census_eits(source, body, retrieved_at):
    """Parse a Census EITS timeseries 2-D JSON array (row 0 = header names).

    One record per data row: series identity =
    CENSUS.EITS.<DATASET>.<category_code>.<data_type_code>.<SA|NSA>
    where <DATASET> comes from config (source.series.dataset), NOT the payload.
    Period is the required `time` column (YYYY-MM or YYYY). cell_value is the value;
    null / "" / a Census large-negative sentinel -> value_status unavailable.
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, list) or len(payload) < 2:
        raise SourceUnavailable("Census EITS payload was not a 2-D array")
    header = payload[0]
    if not isinstance(header, list) or not all(isinstance(h, str) for h in header):
        raise SourceUnavailable("Census EITS header row was not a list of names")

    series = source.get("series")
    if not isinstance(series, dict):
        raise SourceUnavailable("Census EITS source.series was not an object")
    dataset = series.get("dataset")
    if not isinstance(dataset, str) or not dataset:
        raise SourceUnavailable("Census EITS source.series.dataset was invalid")
    dataset_token = dataset.upper()

    idx = {name: i for i, name in enumerate(header)}
    required_cols = (
        "cell_value", "category_code", "data_type_code",
        "seasonally_adj", "geo_level_code",
    )
    for col in required_cols:
        if col not in idx:
            raise SourceUnavailable("Census EITS header missing %s" % col)
    time_col = "time" if "time" in idx else (
        "time_slot_date" if "time_slot_date" in idx else None
    )
    if time_col is None:
        raise SourceUnavailable("Census EITS header missing a time column")

    declared = None
    items = series.get("items")
    if isinstance(items, list):
        declared = {it.get("series_id") for it in items if isinstance(it, dict)}

    records = []
    seen = set()
    available_count = 0
    for row in payload[1:]:
        if not isinstance(row, list) or len(row) != len(header):
            raise SourceUnavailable("Census EITS data row shape was not exact")
        category = row[idx["category_code"]]
        data_type = row[idx["data_type_code"]]
        geo = row[idx["geo_level_code"]]
        sa_raw = row[idx["seasonally_adj"]]
        period_raw = row[idx[time_col]]
        cell = row[idx["cell_value"]]
        if not isinstance(category, str) or not category:
            raise SourceUnavailable("Census EITS row missing category_code")
        if not isinstance(data_type, str) or not data_type:
            raise SourceUnavailable("Census EITS row missing data_type_code")
        if not isinstance(geo, str) or not geo:
            raise SourceUnavailable("Census EITS row missing geo_level_code")
        if not isinstance(sa_raw, str) or sa_raw.lower() not in ("yes", "no"):
            raise SourceUnavailable("Census EITS seasonally_adj was not yes/no")
        sa_token = "SA" if sa_raw.lower() == "yes" else "NSA"
        if not isinstance(period_raw, str) or not period_raw:
            raise SourceUnavailable("Census EITS row missing time")
        if re.match(r"^\d{4}$", period_raw):
            reference_period = period_raw
        elif re.match(r"^\d{4}-\d{2}$", period_raw):
            try:
                datetime.strptime(period_raw, "%Y-%m")
            except ValueError:
                raise SourceUnavailable("Census EITS time was invalid")
            reference_period = period_raw
        else:
            raise SourceUnavailable("Census EITS time was not YYYY or YYYY-MM")

        series_id = "CENSUS.EITS.%s.%s.%s.G%s.%s" % (
            dataset_token, category, data_type, geo, sa_token,
        )
        if declared is not None and series_id not in declared:
            raise SourceUnavailable(
                "Census EITS returned an undeclared series identity %s" % series_id
            )
        key = (series_id, reference_period)
        if key in seen:
            raise SourceUnavailable("Census EITS contained a duplicate observation")
        seen.add(key)

        unavailable = (
            cell is None or
            (isinstance(cell, str) and (
                cell.strip() == "" or cell.strip() in _CENSUS_MISSING_SENTINELS
            ))
        )
        value = None
        if not unavailable:
            value = str(cell).strip()
            if not _CANONICAL_DECIMAL_RE.match(value):
                raise SourceUnavailable("Census EITS cell_value was not canonical decimal")

        record = _base_record(
            source, series_id, reference_period,
            None if unavailable else value,
            series.get("unit", "index_or_count"),
            retrieved_at,
        )
        record["category_code"] = category
        record["data_type_code"] = data_type
        record["geo_level_code"] = geo
        record["seasonally_adjusted"] = (sa_token == "SA")
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("Census EITS contained no available observations")
    return records


_BEA_MISSING_TOKENS = frozenset((
    "", "(NA)", "NA", "(D)", "(NM)", "(L)", "(T)", "...", "n.a.",
))


def parse_bea_api(source, body, retrieved_at):
    """Parse a BEA API GetData JSON payload (NIPA / NIUnderlyingDetail).

    One record per (SeriesCode, TimePeriod). Series identity =
    BEA.<DATASET>.<TableName>.<SeriesCode> where <DATASET> is from config
    (source.series.dataset, e.g. NIPA), and TableName + SeriesCode come from the
    authoritative row. DataValue carries thousands commas -> stripped; BEA
    suppression / not-available tokens map to value_status unavailable rather
    than fabricating a number. TimePeriod is canonicalized to YYYY (annual),
    YYYY-Qn (quarterly) or YYYY-MM (monthly) without inventing a day.
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict):
        raise SourceUnavailable("BEA payload was not an object")
    envelope = payload.get("BEAAPI")
    if not isinstance(envelope, dict):
        raise SourceUnavailable("BEA payload missing BEAAPI envelope")
    if envelope.get("Error") is not None:
        raise SourceUnavailable("BEA API returned an envelope error")
    results = envelope.get("Results")
    if isinstance(results, list):
        results = results[0] if results else None
    if not isinstance(results, dict):
        raise SourceUnavailable("BEA Results block was not an object")
    if results.get("Error") is not None:
        raise SourceUnavailable("BEA Results returned an error")
    rows = results.get("Data")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("BEA Results carried no Data rows")

    series = source.get("series")
    if not isinstance(series, dict):
        raise SourceUnavailable("BEA source.series was not an object")
    dataset = series.get("dataset")
    if not isinstance(dataset, str) or not dataset:
        raise SourceUnavailable("BEA source.series.dataset was invalid")
    dataset_token = dataset.upper()

    declared = None
    items = series.get("items")
    if isinstance(items, list):
        declared = {it.get("series_id") for it in items if isinstance(it, dict)}

    records = []
    seen = {}
    available_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise SourceUnavailable("BEA Data row was not an object")
        table = row.get("TableName")
        code = row.get("SeriesCode")
        period_raw = row.get("TimePeriod")
        cell = row.get("DataValue")
        if not isinstance(table, str) or not table:
            raise SourceUnavailable("BEA row missing TableName")
        if not isinstance(code, str) or not code:
            raise SourceUnavailable("BEA row missing SeriesCode")
        if not isinstance(period_raw, str) or not period_raw:
            raise SourceUnavailable("BEA row missing TimePeriod")
        if re.match(r"^\d{4}$", period_raw):
            reference_period = period_raw
        elif re.match(r"^\d{4}Q[1-4]$", period_raw):
            reference_period = "%s-Q%s" % (period_raw[:4], period_raw[5])
        elif re.match(r"^\d{4}M\d{2}$", period_raw):
            month = period_raw[5:]
            if not ("01" <= month <= "12"):
                raise SourceUnavailable("BEA monthly TimePeriod was invalid")
            reference_period = "%s-%s" % (period_raw[:4], month)
        else:
            raise SourceUnavailable("BEA TimePeriod was not YYYY / YYYYQn / YYYYMmm")

        series_id = "BEA.%s.%s.%s" % (dataset_token, table, code)
        if declared is not None and series_id not in declared:
            raise SourceUnavailable(
                "BEA returned an undeclared series identity %s" % series_id
            )

        raw_value = "" if cell is None else str(cell).strip()
        stripped = raw_value.replace(",", "")
        unavailable = (
            raw_value in _BEA_MISSING_TOKENS or
            not _CANONICAL_DECIMAL_RE.match(stripped)
        )
        value = None
        if not unavailable:
            value = stripped

        # BEA repeats a SeriesCode across presentation lines (subtotals shown in
        # more than one place). Identical repeats collapse; only a genuine value
        # conflict for the same (series, period) is an error.
        key = (series_id, reference_period)
        if key in seen:
            if seen[key] != (value, unavailable):
                raise SourceUnavailable(
                    "BEA gave conflicting values for %s %s"
                    % (series_id, reference_period)
                )
            continue
        seen[key] = (value, unavailable)

        record = _base_record(
            source, series_id, reference_period,
            value, series.get("unit", "current_dollars_or_index"),
            retrieved_at,
        )
        record["bea_table"] = table
        record["bea_series_code"] = code
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("BEA payload contained no available observations")
    return records


_EIA_MISSING_TOKENS = frozenset((
    "", "NA", "N/A", "null", "w", "W", "--",
))


def parse_eia_v2_json(source, body, retrieved_at):
    """Parse an EIA API v2 GetData JSON payload (`response.data[]`).

    EIA v2 returns `{"response": {"data": [ {<facets>, <period>, <value>}, ... ]}}`.
    One record per (identity, period). The series identity is built ONLY from
    reviewed config, never from free payload text:

        <identity_prefix>.<facet_1>.<facet_2>...<facet_n>.<lane>

    where `identity_prefix`, the ordered `identity_facets` payload keys, and the
    `lane` token all come from `source.series`. The `lane` token keeps the
    raw / Imputed / Adjusted value lanes DISTINCT — an Adjusted daily-region
    source and a raw one carry different lane tokens and therefore never
    collapse onto one identity. Period is canonicalized to YYYY / YYYY-MM /
    YYYY-MM-DD / YYYY-Qn / YYYY-MM-DDTHH without inventing missing components.
    Missing / withheld values map to value_status unavailable rather than
    fabricating a number. Any returned identity outside the declared set raises.
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict):
        raise SourceUnavailable("EIA payload was not an object")
    response = payload.get("response")
    if not isinstance(response, dict):
        raise SourceUnavailable("EIA payload missing response envelope")
    if payload.get("error") is not None or response.get("error") is not None:
        raise SourceUnavailable("EIA API returned an error envelope")
    rows = response.get("data")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("EIA response carried no data rows")

    series = source.get("series")
    if not isinstance(series, dict):
        raise SourceUnavailable("EIA source.series was not an object")
    prefix = series.get("identity_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise SourceUnavailable("EIA source.series.identity_prefix was invalid")
    facets = series.get("identity_facets")
    if (
        not isinstance(facets, list) or not facets or
        any(not isinstance(f, str) or not f for f in facets)
    ):
        raise SourceUnavailable("EIA source.series.identity_facets was invalid")
    lane = series.get("lane")
    if not isinstance(lane, str) or not lane:
        raise SourceUnavailable("EIA source.series.lane was invalid")
    period_key = series.get("period_key", "period")
    value_key = series.get("value_key", "value")
    if not isinstance(period_key, str) or not period_key:
        raise SourceUnavailable("EIA source.series.period_key was invalid")
    if not isinstance(value_key, str) or not value_key:
        raise SourceUnavailable("EIA source.series.value_key was invalid")

    declared = None
    items = series.get("items")
    if isinstance(items, list):
        declared = {it.get("series_id") for it in items if isinstance(it, dict)}

    records = []
    seen = {}
    available_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise SourceUnavailable("EIA data row was not an object")
        facet_values = []
        for key in facets:
            token = row.get(key)
            if not isinstance(token, str) or not token or "." in token:
                raise SourceUnavailable(
                    "EIA row facet %s was missing or contained a dot" % key
                )
            facet_values.append(token)
        period_raw = row.get(period_key)
        if not isinstance(period_raw, str) or not period_raw:
            raise SourceUnavailable("EIA row missing %s" % period_key)
        reference_period = _canonicalize_eia_period(period_raw)

        series_id = "%s.%s.%s" % (prefix, ".".join(facet_values), lane)
        if declared is not None and series_id not in declared:
            raise SourceUnavailable(
                "EIA returned an undeclared series identity %s" % series_id
            )

        cell = row.get(value_key)
        raw_value = "" if cell is None else str(cell).strip()
        unavailable = (
            raw_value in _EIA_MISSING_TOKENS or
            not _CANONICAL_DECIMAL_RE.match(raw_value)
        )
        value = None if unavailable else raw_value

        key = (series_id, reference_period)
        if key in seen:
            if seen[key] != (value, unavailable):
                raise SourceUnavailable(
                    "EIA gave conflicting values for %s %s"
                    % (series_id, reference_period)
                )
            continue
        seen[key] = (value, unavailable)

        record = _base_record(
            source, series_id, reference_period,
            value, series.get("unit", "megawatthours"),
            retrieved_at,
        )
        record["eia_lane"] = lane
        for key_name, token in zip(facets, facet_values):
            record["eia_facet_%s" % key_name] = token
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("EIA payload contained no available observations")
    return records


def _canonicalize_eia_period(period_raw):
    """Canonicalize an EIA v2 period token without inventing missing parts."""
    if re.match(r"^\d{4}$", period_raw):
        return period_raw
    if re.match(r"^\d{4}-Q[1-4]$", period_raw):
        return period_raw
    if re.match(r"^\d{4}-\d{2}$", period_raw):
        try:
            datetime.strptime(period_raw, "%Y-%m")
        except ValueError:
            raise SourceUnavailable("EIA period month was invalid")
        return period_raw
    if re.match(r"^\d{4}-\d{2}-\d{2}$", period_raw):
        try:
            datetime.strptime(period_raw, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("EIA period date was invalid")
        return period_raw
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}$", period_raw):
        try:
            datetime.strptime(period_raw, "%Y-%m-%dT%H")
        except ValueError:
            raise SourceUnavailable("EIA hourly period was invalid")
        return period_raw
    raise SourceUnavailable("EIA period was not a recognized granularity")


def parse_fred_json_api(source, body, retrieved_at):
    """Parse the keyed FRED series/observations JSON, current-vintage lane only.

    The current lane requires a single collapsed vintage (realtime_start ==
    realtime_end == the envelope realtime for every observation). If the payload
    carries multiple distinct vintages this raises rather than splicing them —
    ALFRED vintage reconstruction is a separately typed lane, never mixed in here.
    Values are byte-identical to the fredgraph.csv download for the same series.
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict):
        raise SourceUnavailable("FRED JSON payload was not an object")
    if payload.get("file_type") != "json":
        raise SourceUnavailable("FRED JSON file_type was not json")
    if str(payload.get("output_type")) != "1":
        raise SourceUnavailable("FRED JSON current lane requires output_type 1")

    envelope_start = payload.get("realtime_start")
    envelope_end = payload.get("realtime_end")
    if (
        not isinstance(envelope_start, str) or
        not isinstance(envelope_end, str) or
        envelope_start != envelope_end
    ):
        raise SourceUnavailable("FRED JSON current lane requires a single vintage")

    series = source.get("series")
    expected_series_fields = frozenset(("label", "series_id", "unit"))
    if (
        not isinstance(series, dict) or
        frozenset(series) != expected_series_fields
    ):
        raise SourceUnavailable("FRED JSON series metadata was not exact")
    series_id = series["series_id"]
    if (
        not isinstance(series_id, str) or
        not _SERIES_ID_RE.match(series_id)
    ):
        raise SourceUnavailable("FRED JSON series_id was invalid")
    if (
        not isinstance(series["label"], str) or not series["label"] or
        not isinstance(series["unit"], str) or not series["unit"]
    ):
        raise SourceUnavailable("FRED JSON series label or unit was invalid")

    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SourceUnavailable("FRED JSON payload contained no observations")

    records = []
    seen_dates = set()
    available_count = 0
    expected_obs_fields = frozenset(
        ("date", "realtime_start", "realtime_end", "value")
    )
    for row in observations:
        if not isinstance(row, dict) or frozenset(row) != expected_obs_fields:
            raise SourceUnavailable("FRED JSON observation shape was not exact")
        if (
            row["realtime_start"] != envelope_start or
            row["realtime_end"] != envelope_end
        ):
            raise SourceUnavailable(
                "FRED JSON current lane saw a divergent observation vintage"
            )
        reference_period = row["date"]
        if not isinstance(reference_period, str):
            raise SourceUnavailable("FRED JSON observation date was missing")
        try:
            parsed_date = datetime.strptime(reference_period, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("FRED JSON observation date was invalid")
        if parsed_date.strftime("%Y-%m-%d") != reference_period:
            raise SourceUnavailable("FRED JSON observation date was not canonical")
        if reference_period in seen_dates:
            raise SourceUnavailable("FRED JSON contained a duplicate date")
        seen_dates.add(reference_period)

        raw_value = row["value"]
        if not isinstance(raw_value, str):
            raise SourceUnavailable("FRED JSON value was not a string")
        raw_value = raw_value.strip()
        unavailable = raw_value in ("", ".")
        if not unavailable and not _CANONICAL_DECIMAL_RE.match(raw_value):
            raise SourceUnavailable("FRED JSON value was not canonical decimal")

        record = _base_record(
            source,
            series_id,
            reference_period,
            None if unavailable else raw_value,
            series["unit"],
            retrieved_at,
        )
        record["label"] = series["label"]
        record["provider_vintage_kind"] = "current_revised"
        record["strict_publisher_first_release_proven"] = False
        record["provider_realtime_window"] = envelope_start
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("FRED JSON contained no available observations")
    return records


def parse_fred_json_api_vintages(source, body, retrieved_at):
    """Parse the keyed FRED ALFRED vintage matrix (output_type=2), never spliced.

    output_type=2 returns a WIDE matrix: each observation row carries "date" plus
    one "<BASE>_<YYYYMMDD>" column per vintage date. This lane emits one record per
    (observation_period, vintage), with the vintage encoded into the record series_id
    as "<BASE>.ASOF<YYYYMMDD>" so every as-of snapshot is a distinct output identity.
    A "." cell means the observation did not yet exist as-of that vintage -> it is
    SKIPPED (absence is not a hole; emitting "unavailable" would be a false negative).
    The current lane (parse_fred_json_api) refuses this payload; this lane refuses the
    current-lane payload — the two are never mixed. information_set_mode is the source's
    (archive_snapshot_asof); this parser never fabricates a first-release stitch.
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict):
        raise SourceUnavailable("FRED vintage payload was not an object")
    if payload.get("file_type") != "json":
        raise SourceUnavailable("FRED vintage file_type was not json")
    if str(payload.get("output_type")) != "2":
        raise SourceUnavailable("FRED vintage lane requires output_type 2")

    series = source.get("series")
    expected_series_fields = frozenset(("label", "series_id", "unit"))
    if not isinstance(series, dict) or frozenset(series) != expected_series_fields:
        raise SourceUnavailable("FRED vintage series metadata was not exact")
    base = series["series_id"]
    if not isinstance(base, str) or not _SERIES_ID_RE.match(base):
        raise SourceUnavailable("FRED vintage base series_id was invalid")
    if (
        not isinstance(series["label"], str) or not series["label"] or
        not isinstance(series["unit"], str) or not series["unit"]
    ):
        raise SourceUnavailable("FRED vintage series label or unit was invalid")

    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SourceUnavailable("FRED vintage payload contained no observations")

    column_re = re.compile(r"^" + re.escape(base) + r"_(\d{8})$")
    records = []
    seen = set()
    available_count = 0
    for row in observations:
        if not isinstance(row, dict) or "date" not in row:
            raise SourceUnavailable("FRED vintage observation shape was not exact")
        reference_period = row["date"]
        if not isinstance(reference_period, str):
            raise SourceUnavailable("FRED vintage observation date was missing")
        try:
            parsed_date = datetime.strptime(reference_period, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("FRED vintage observation date was invalid")
        if parsed_date.strftime("%Y-%m-%d") != reference_period:
            raise SourceUnavailable("FRED vintage observation date was not canonical")

        for column, raw_value in row.items():
            if column == "date":
                continue
            match = column_re.match(column)
            if not match:
                raise SourceUnavailable(
                    "FRED vintage column did not match the base series"
                )
            vintage = match.group(1)
            try:
                datetime.strptime(vintage, "%Y%m%d")
            except ValueError:
                raise SourceUnavailable("FRED vintage date column was invalid")
            if not isinstance(raw_value, str):
                raise SourceUnavailable("FRED vintage value was not a string")
            value = raw_value.strip()
            if value in ("", "."):
                continue
            if not _CANONICAL_DECIMAL_RE.match(value):
                raise SourceUnavailable("FRED vintage value was not canonical decimal")
            vintage_series_id = "%s.ASOF%s" % (base, vintage)
            identity = (vintage_series_id, reference_period)
            if identity in seen:
                raise SourceUnavailable("FRED vintage contained a duplicate cell")
            seen.add(identity)
            record = _base_record(
                source,
                vintage_series_id,
                reference_period,
                value,
                series["unit"],
                retrieved_at,
            )
            record["label"] = series["label"]
            record["provider_vintage_kind"] = source["information_set_mode"]
            record["strict_publisher_first_release_proven"] = False
            records.append(record)
            available_count += 1

    if not records or not available_count:
        raise SourceUnavailable("FRED vintage contained no available observations")
    return records


# Deep as-of window: the deep lane keeps vintages in [MIN, MAX]; MAX+1 on is the
# shallow ".ASOF" lane's territory, so the two lanes are disjoint by
# construction. MIN/MAX and the per-source growth cap are DECLARED,
# provenance-tagged parameters (B-LAND-5-R2, owner-ruled 2026-08-06) — not
# module-level scientific constants, so they live in a live_data config file,
# not model_authority/parameters/parameter_registry.v1.json (see that file's
# and deep_vintage_window.v1.json's `not_the_parameter_registry` notes).
def _load_deep_vintage_window():
    cfg_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.pardir, "config", "deep_vintage_window.v1.json",
    )
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return (
        cfg["deep_vintage_min"],
        cfg["deep_vintage_max"],
        cfg.get("per_source_vintage_cap"),
    )


DEEP_VINTAGE_MIN, DEEP_VINTAGE_MAX, DEEP_VINTAGE_CAP = _load_deep_vintage_window()


def parse_fred_json_api_vintages_deep(source, body, retrieved_at):
    """Deep ALFRED vintage lane: pre-2020 as-of snapshots only.

    Identical wide-matrix (output_type=2) parsing as
    parse_fred_json_api_vintages, but emits "<BASE>.DEEPASOF<YYYYMMDD>" and
    keeps ONLY vintages whose as-of date is in [2000-01-01, 2019-12-31]. The
    shallow ".ASOF" lane owns 2020-01-01 on, so the two lanes never overlap.
    ".DEEPASOF" (not ".ASOFDEEP") is mandatory: ".ASOFDEEP" starts with ".ASOF"
    and would collide with the append-only .ASOF family prefix gate in
    feed_factory._validate_source_candidate. A "." cell means the observation
    did not yet exist as-of that vintage -> SKIP (absence is not a hole).
    """
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict):
        raise SourceUnavailable("FRED vintage payload was not an object")
    if payload.get("file_type") != "json":
        raise SourceUnavailable("FRED vintage file_type was not json")
    if str(payload.get("output_type")) != "2":
        raise SourceUnavailable("FRED vintage lane requires output_type 2")

    series = source.get("series")
    expected_series_fields = frozenset(("label", "series_id", "unit"))
    if not isinstance(series, dict) or frozenset(series) != expected_series_fields:
        raise SourceUnavailable("FRED vintage series metadata was not exact")
    base = series["series_id"]
    if not isinstance(base, str) or not _SERIES_ID_RE.match(base):
        raise SourceUnavailable("FRED vintage base series_id was invalid")
    if (
        not isinstance(series["label"], str) or not series["label"] or
        not isinstance(series["unit"], str) or not series["unit"]
    ):
        raise SourceUnavailable("FRED vintage series label or unit was invalid")

    observations = payload.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SourceUnavailable("FRED vintage payload contained no observations")

    # B-LAND-3D: a non-primary provider tags its deep family so the append-only
    # gate is per-(base, provider). The tag is inserted BEFORE ".DEEPASOF":
    # <BASE>.<TAG>.DEEPASOF<vintage>, disjoint in both directions from the primary
    # <BASE>.DEEPASOF family. Untagged sources are byte-identical to before.
    provider_tag = source.get("vintage_provider_tag")
    deep_family = (
        "%s.%s.DEEPASOF" % (base, provider_tag)
        if provider_tag else "%s.DEEPASOF" % base
    )

    column_re = re.compile(r"^" + re.escape(base) + r"_(\d{8})$")

    # Per-source growth cap (B-LAND-5-R2, owner-ruled): when the in-window
    # vintages exceed the cap, keep only the EARLIEST `cap` of them (depth beats
    # density pre-2000; the [2000,2019] density already exists). Per-source
    # override falls back to the declared global default; None -> no cap.
    # Vintage strings are YYYYMMDD, so lexical order is chronological.
    cap = source.get("deep_vintage_cap", DEEP_VINTAGE_CAP)
    allowed_vintages = None
    if cap is not None:
        in_window = set()
        for row in observations:
            if not isinstance(row, dict):
                continue
            for column in row:
                if column == "date":
                    continue
                cap_match = column_re.match(column)
                if cap_match and (
                    DEEP_VINTAGE_MIN <= cap_match.group(1) <= DEEP_VINTAGE_MAX
                ):
                    in_window.add(cap_match.group(1))
        allowed_vintages = set(sorted(in_window)[:cap])

    records = []
    seen = set()
    available_count = 0
    for row in observations:
        if not isinstance(row, dict) or "date" not in row:
            raise SourceUnavailable("FRED vintage observation shape was not exact")
        reference_period = row["date"]
        if not isinstance(reference_period, str):
            raise SourceUnavailable("FRED vintage observation date was missing")
        try:
            parsed_date = datetime.strptime(reference_period, "%Y-%m-%d")
        except ValueError:
            raise SourceUnavailable("FRED vintage observation date was invalid")
        if parsed_date.strftime("%Y-%m-%d") != reference_period:
            raise SourceUnavailable("FRED vintage observation date was not canonical")

        for column, raw_value in row.items():
            if column == "date":
                continue
            match = column_re.match(column)
            if not match:
                raise SourceUnavailable(
                    "FRED vintage column did not match the base series"
                )
            vintage = match.group(1)
            try:
                datetime.strptime(vintage, "%Y%m%d")
            except ValueError:
                raise SourceUnavailable("FRED vintage date column was invalid")
            # Deep window gate: keep ONLY pre-2020 as-of snapshots. Out-of-window
            # vintages belong to the shallow ".ASOF" lane and are skipped here so
            # the two lanes stay disjoint. This is an identity boundary between
            # two lanes, not a data hole.
            if not (DEEP_VINTAGE_MIN <= vintage <= DEEP_VINTAGE_MAX):
                continue
            # Growth cap (earliest-prioritized): drop vintages outside the
            # earliest-`cap` in-window set. Absence here is a scaling guard, not
            # a data hole (recorded in deep_vintage_window.v1.json provenance).
            if allowed_vintages is not None and vintage not in allowed_vintages:
                continue
            if not isinstance(raw_value, str):
                raise SourceUnavailable("FRED vintage value was not a string")
            value = raw_value.strip()
            if value in ("", "."):
                continue
            if not _CANONICAL_DECIMAL_RE.match(value):
                raise SourceUnavailable("FRED vintage value was not canonical decimal")
            vintage_series_id = "%s%s" % (deep_family, vintage)
            identity = (vintage_series_id, reference_period)
            if identity in seen:
                raise SourceUnavailable("FRED vintage contained a duplicate cell")
            seen.add(identity)
            record = _base_record(
                source,
                vintage_series_id,
                reference_period,
                value,
                series["unit"],
                retrieved_at,
            )
            record["label"] = series["label"]
            record["provider_vintage_kind"] = source["information_set_mode"]
            record["strict_publisher_first_release_proven"] = False
            records.append(record)
            available_count += 1

    if not records or not available_count:
        raise SourceUnavailable("FRED vintage contained no available observations")
    return records


_TABULAR_VALUE_STATUSES = frozenset((
    "actual",
    "forecast",
    "model_estimate",
    "nowcast",
    "substituted",
))
_CANONICAL_DECIMAL_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_STRICT_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_SCIENTIFIC_DECIMAL_RE = re.compile(
    r"^-?(?:0|[1-9]\d*)(?:\.\d+)?[eE][+-]?\d+$"
)
_SERIES_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


def _validate_projected_items(items, field_key):
    expected_fields = frozenset((
        field_key,
        "forecast_horizon",
        "label",
        "series_id",
        "unit",
        "value_status",
    ))
    if not isinstance(items, list) or not items:
        raise SourceUnavailable("projected series items must be a nonempty list")
    seen_fields = set()
    seen_series = set()
    for item in items:
        if not isinstance(item, dict) or frozenset(item) != expected_fields:
            raise SourceUnavailable("projected series item metadata was not exact")
        publisher_field = item[field_key]
        series_id = item["series_id"]
        if (
            not isinstance(publisher_field, str) or not publisher_field or
            publisher_field in seen_fields
        ):
            raise SourceUnavailable("projected publisher field was invalid or duplicated")
        if (
            not isinstance(series_id, str) or
            not _SERIES_ID_RE.match(series_id) or
            series_id in seen_series
        ):
            raise SourceUnavailable("projected series identity was invalid or duplicated")
        if (
            not isinstance(item["label"], str) or not item["label"] or
            not isinstance(item["unit"], str) or not item["unit"]
        ):
            raise SourceUnavailable("projected series label or unit was invalid")
        value_status = item["value_status"]
        if value_status not in _TABULAR_VALUE_STATUSES:
            raise SourceUnavailable("projected series value_status was invalid")
        horizon = item["forecast_horizon"]
        if (
            horizon is not None and
            (not isinstance(horizon, str) or not horizon)
        ):
            raise SourceUnavailable("projected series forecast_horizon was invalid")
        if (value_status == "forecast") != (horizon is not None):
            raise SourceUnavailable(
                "only forecast series may carry a forecast_horizon"
            )
        seen_fields.add(publisher_field)
        seen_series.add(series_id)
    return items


def _parse_exact_date(raw_value, date_format):
    if not isinstance(raw_value, str) or not raw_value:
        raise SourceUnavailable("publisher row date was missing")
    if date_format == "month_abbrev_two_digit_year_pivot_1968":
        match = re.match(
            r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2})$",
            raw_value,
        )
        if not match:
            raise SourceUnavailable("publisher row date was invalid")
        month = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }[match.group(1)]
        short_year = int(match.group(2))
        year = 1900 + short_year if short_year >= 68 else 2000 + short_year
        return "%04d-%02d-01" % (year, month)
    try:
        parsed = datetime.strptime(raw_value, date_format)
    except (TypeError, ValueError):
        raise SourceUnavailable("publisher row date was invalid")
    if parsed.strftime(date_format) != raw_value:
        raise SourceUnavailable("publisher row date was not canonical")
    return parsed.date().isoformat()


def _project_tabular_record(
    source,
    item,
    publisher_field,
    reference_period,
    raw_value,
    retrieved_at,
):
    unavailable = raw_value is None
    if not unavailable:
        if not isinstance(raw_value, str):
            raw_value = str(raw_value)
        if not _CANONICAL_DECIMAL_RE.match(raw_value):
            raise SourceUnavailable(
                "publisher field %s was not a canonical decimal" %
                publisher_field
            )
    record = _base_record(
        source,
        item["series_id"],
        reference_period,
        None if unavailable else raw_value,
        item["unit"],
        retrieved_at,
    )
    record["label"] = item["label"]
    record["provider_vintage_kind"] = source["information_set_mode"]
    record["publisher_field"] = publisher_field
    record["strict_publisher_first_release_proven"] = False
    if unavailable:
        record["value_status"] = "unavailable"
    else:
        record["value_status"] = item["value_status"]
        if item["value_status"] == "forecast":
            record["forecast_horizon"] = item["forecast_horizon"]
            record["forecast_origin"] = None
    return record


def parse_tabular_csv(source, body, retrieved_at):
    """Project an exact official CSV schema without inferring missing values."""
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("publisher CSV was not valid UTF-8: %s" % exc)
    series = source.get("series")
    compact_series_fields = frozenset((
        "date_column",
        "date_format",
        "items",
        "missing_tokens",
    ))
    wide_series_fields = frozenset(tuple(compact_series_fields) + (
        "expected_header",
    ))
    if (
        not isinstance(series, dict) or
        frozenset(series) not in (compact_series_fields, wide_series_fields) or
        not isinstance(series["date_column"], str) or
        not series["date_column"] or
        not isinstance(series["date_format"], str) or
        not series["date_format"] or
        not isinstance(series["missing_tokens"], list) or
        not series["missing_tokens"] or
        any(not isinstance(item, str) for item in series["missing_tokens"]) or
        len(series["missing_tokens"]) != len(set(series["missing_tokens"]))
    ):
        raise SourceUnavailable("publisher CSV series metadata was not exact")
    items = _validate_projected_items(series["items"], "column")
    if frozenset(series) == compact_series_fields:
        expected_header = [series["date_column"]] + [
            item["column"] for item in items
        ]
    else:
        expected_header = series["expected_header"]
        if (
            not isinstance(expected_header, list) or
            not expected_header or
            any(not isinstance(field, str) or not field for field in expected_header) or
            len(expected_header) != len(set(expected_header)) or
            expected_header[0] != series["date_column"] or
            any(item["column"] not in expected_header[1:] for item in items)
        ):
            raise SourceUnavailable("publisher CSV expected header was invalid")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != expected_header:
        raise SourceUnavailable("publisher CSV header was not exact")

    records = []
    seen_dates = set()
    available_count = 0
    missing_tokens = frozenset(series["missing_tokens"])
    for row in reader:
        if row.get(None) or set(row) != set(expected_header):
            raise SourceUnavailable("publisher CSV row width was not exact")
        reference_period = _parse_exact_date(
            row.get(series["date_column"]),
            series["date_format"],
        )
        if reference_period in seen_dates:
            raise SourceUnavailable("publisher CSV contained a duplicate date")
        seen_dates.add(reference_period)
        for item in items:
            raw_value = row.get(item["column"])
            if not isinstance(raw_value, str):
                raise SourceUnavailable("publisher CSV value was missing")
            raw_value = raw_value.strip()
            if raw_value in missing_tokens:
                raw_value = None
            else:
                available_count += 1
            records.append(_project_tabular_record(
                source,
                item,
                item["column"],
                reference_period,
                raw_value,
                retrieved_at,
            ))
    if not records or not available_count:
        raise SourceUnavailable("publisher CSV contained no available observations")
    return records


def parse_regional_survey_xlsx(source, body, retrieved_at):
    """Normalize exact selected indexes from a reviewed regional workbook."""
    try:
        observations = parse_regional_survey_source_xlsx(
            source.get("series"),
            body,
        )
    except RegionalSurveyDataError as exc:
        raise SourceUnavailable(
            "regional survey workbook contract failed: %s" % exc
        )
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_field": observation["publisher_field"],
            "strict_publisher_first_release_proven": False,
            "value_status": (
                "unavailable"
                if observation["value"] is None
                else observation["value_status"]
            ),
        })
        if observation["value_status"] == "forecast":
            record["forecast_horizon"] = observation["forecast_horizon"]
            record["forecast_origin"] = None
        records.append(record)
    return records


# Currency DDP packages (e.g. H.8) must not inherit the rate-family "percent"
# unit. The unit is derived from the schema-validated Unit/Multiplier/Currency
# metadata the DDP contract already pins. Every historical fed_ddp_csv source is
# a rate/ratio/diffusion measure (expected_unit != "Currency"), so those keep
# emitting "percent" byte-for-byte; only the currency branch is new.
_FED_DDP_CURRENCY_UNIT_TOKENS = {
    ("USD", "1000000"): "USD_millions",
}


def _fed_ddp_unit(series):
    if (series or {}).get("expected_unit") != "Currency":
        return "percent"
    key = (series.get("expected_currency"), series.get("expected_multiplier"))
    token = _FED_DDP_CURRENCY_UNIT_TOKENS.get(key)
    if token is None:
        raise SourceUnavailable(
            "fed_ddp_csv currency unit contract unsupported: %r" % (key,)
        )
    return token


def parse_fed_ddp_csv(source, body, retrieved_at):
    """Normalize a schema-bound Federal Reserve DDP CSV package."""
    try:
        observations = parse_fed_ddp_source_csv(source.get("series"), body)
    except FedDdpDataError as exc:
        raise SourceUnavailable("Federal Reserve DDP contract failed: %s" % exc)
    unit = _fed_ddp_unit(source.get("series"))
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            unit,
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_field": observation["publisher_field"],
            "publisher_identifier": observation["publisher_identifier"],
            "publisher_period": observation["publisher_period"],
            "strict_publisher_first_release_proven": False,
        })
        if observation["value"] is None:
            record["value_status"] = "unavailable"
        records.append(record)
    return records


def parse_cfpb_credit_trends_csv(source, body, retrieved_at):
    """Normalize CFPB's reviewed national Consumer Credit Trends projection."""
    try:
        observations = parse_cfpb_credit_trends_source_csv(
            source.get("series"),
            body,
        )
    except CfpbCreditTrendsDataError as exc:
        raise SourceUnavailable("CFPB credit-trends contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_field": observation["publisher_field"],
            "publisher_identity": observation["publisher_identity"],
            "publisher_month_index": observation["publisher_month_index"],
            "publisher_period": observation["publisher_period"],
            "publisher_revision_status": (
                observation["publisher_revision_status"]
            ),
            "strict_publisher_first_release_proven": False,
        })
        if observation["value"] is None:
            record["value_status"] = "unavailable"
        records.append(record)
    return records


def parse_census_btos_xlsx(source, body, retrieved_at):
    """Normalize Census BTOS national estimates and their uncertainty."""
    try:
        observations = parse_census_btos_source_xlsx(
            source.get("series"),
            body,
        )
    except CensusBtosDataError as exc:
        raise SourceUnavailable("Census BTOS contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "collection_end": observation["collection_end"],
            "collection_start": observation["collection_start"],
            "forecast_horizon": observation["forecast_horizon"],
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_cycle": observation["publisher_cycle"],
            "publisher_measure_kind": observation[
                "publisher_measure_kind"
            ],
            "publisher_missing_reason": observation[
                "publisher_missing_reason"
            ],
            "publisher_publication_date": observation[
                "publisher_publication_date"
            ],
            "publisher_revision_status": (
                "publisher_states_no_revisions_current_workbook_capture"
            ),
            "publisher_structural_gap": observation[
                "publisher_structural_gap"
            ],
            "reference_period_start": observation[
                "reference_period_start"
            ],
            "strict_publisher_first_release_proven": False,
            "value_status": observation["value_status"],
        })
        for optional in (
            "publisher_answer",
            "publisher_answer_id",
            "publisher_index_horizon",
            "publisher_index_label",
            "publisher_question",
            "publisher_question_id",
        ):
            if optional in observation:
                record[optional] = observation[optional]
        if observation["value_status"] == "forecast":
            record["forecast_origin"] = None
        records.append(record)
    return records


def parse_census_qss_zip(source, body, retrieved_at):
    """Normalize the current Census QSS bulk time-series generation."""
    try:
        observations = parse_census_qss_source_zip(
            source.get("series"),
            body,
        )
    except CensusQssDataError as exc:
        raise SourceUnavailable("Census QSS contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "data_updated_on": observation["data_updated_on"],
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_adjustment": observation["publisher_adjustment"],
            "publisher_category_code": observation[
                "publisher_category_code"
            ],
            "publisher_category_description": observation[
                "publisher_category_description"
            ],
            "publisher_category_indent": observation[
                "publisher_category_indent"
            ],
            "publisher_estimate_status": observation[
                "publisher_estimate_status"
            ],
            "publisher_measure_code": observation["publisher_measure_code"],
            "publisher_measure_kind": observation["publisher_measure_kind"],
            "publisher_missing_reason": observation[
                "publisher_missing_reason"
            ],
            "publisher_token": observation["publisher_token"],
            "reference_quarter": observation["reference_quarter"],
            "strict_publisher_first_release_proven": False,
            "value_status": observation["value_status"],
        })
        records.append(record)
    return records


def parse_cfpb_mortgage_performance_state_csv(source, body, retrieved_at):
    """Normalize one exact CFPB state-plus-national delinquency member."""
    try:
        observations = parse_cfpb_mortgage_source_csv(
            source.get("series"),
            body,
        )
    except CfpbMortgageDataError as exc:
        raise SourceUnavailable("CFPB mortgage contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "atomic_bundle_id": observation["atomic_bundle_id"],
            "bundle_member_metric": observation["bundle_member_metric"],
            "data_through": observation["data_through"],
            "label": observation["label"],
            "measurement_basis": observation["measurement_basis"],
            "provider_vintage_kind": observation["provider_vintage_kind"],
            "publisher_fips": observation["publisher_fips"],
            "publisher_fips_token": observation["publisher_fips_token"],
            "publisher_geography_name": observation[
                "publisher_geography_name"
            ],
            "publisher_geography_type": observation[
                "publisher_geography_type"
            ],
            "publisher_imputation_present": observation[
                "publisher_imputation_present"
            ],
            "strict_publisher_first_release_proven": False,
            "value_status": observation["value_status"],
        })
        records.append(record)
    return records


def parse_fema_disaster_declarations_json(source, body, retrieved_at):
    """Normalize strict OpenFEMA v2 administrative declaration counts."""
    try:
        observations = parse_fema_disaster_declarations_source_json(
            source.get("series"),
            body,
        )
    except FemaDisasterDataError as exc:
        raise SourceUnavailable("OpenFEMA v2 contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_declaration_ids": observation[
                "publisher_declaration_ids"
            ],
            "publisher_declaration_titles": observation[
                "publisher_declaration_titles"
            ],
            "publisher_declaration_type": observation[
                "publisher_declaration_type"
            ],
            "publisher_disaster_numbers": observation[
                "publisher_disaster_numbers"
            ],
            "publisher_geography": observation["publisher_geography"],
            "publisher_incident_begin_dates": observation[
                "publisher_incident_begin_dates"
            ],
            "publisher_incident_end_dates": observation[
                "publisher_incident_end_dates"
            ],
            "publisher_incident_types": observation[
                "publisher_incident_types"
            ],
            "publisher_last_refresh_max": observation[
                "publisher_last_refresh_max"
            ],
            "publisher_open_incident_count": observation[
                "publisher_open_incident_count"
            ],
            "publisher_record_hashes": observation[
                "publisher_record_hashes"
            ],
            "publisher_record_ids": observation["publisher_record_ids"],
            "publisher_semantic_guard": observation[
                "publisher_semantic_guard"
            ],
            "strict_publisher_first_release_proven": False,
        })
        records.append(record)
    return records


def parse_cleveland_nowcast_json(source, body, retrieved_at):
    """Normalize the reviewed Cleveland quarterly-nowcast chart projection."""
    try:
        observations = parse_cleveland_nowcast_source_json(
            source.get("series"),
            body,
        )
    except ClevelandNowcastDataError as exc:
        raise SourceUnavailable(
            "Cleveland inflation-nowcast contract failed: %s" % exc
        )
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["reference_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "forecast_target_end": observation["forecast_target_end"],
            "forecast_target_start": observation["forecast_target_start"],
            "label": observation["label"],
            "provider_vintage_kind": source["information_set_mode"],
            "publisher_as_of_label": observation["publisher_as_of_label"],
            "publisher_last_path_index": (
                observation["publisher_last_path_index"]
            ),
            "publisher_last_tooltext": (
                observation["publisher_last_tooltext"]
            ),
            "publisher_nonempty_observation_count": (
                observation["publisher_nonempty_observation_count"]
            ),
            "publisher_target_quarter": (
                observation["publisher_target_quarter"]
            ),
            "strict_publisher_first_release_proven": False,
            "value_status": observation["value_status"],
        })
        if observation["value_status"] == "nowcast":
            record["forecast_horizon"] = "target_quarter_inflation"
            record["forecast_origin"] = None
            record["observed_at"] = None
        records.append(record)
    return records


def parse_socrata_json(source, body, retrieved_at):
    """Project configured numeric fields from an official Socrata row set."""
    rows = strict_publisher_json_loads(body)
    series = source.get("series")
    expected_series_fields = frozenset((
        "date_field",
        "date_format",
        "identity_field",
        "items",
    ))
    if (
        not isinstance(series, dict) or
        frozenset(series) != expected_series_fields or
        not isinstance(series["date_field"], str) or
        not series["date_field"] or
        not isinstance(series["date_format"], str) or
        not series["date_format"] or
        not isinstance(series["identity_field"], str) or
        not series["identity_field"]
    ):
        raise SourceUnavailable("Socrata series metadata was not exact")
    items = _validate_projected_items(series["items"], "field")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("Socrata response contained no rows")

    records = []
    seen_ids = set()
    seen_dates = set()
    available_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise SourceUnavailable("Socrata rows must be objects")
        identity = row.get(series["identity_field"])
        if (
            not isinstance(identity, str) or not identity or
            "\r" in identity or "\n" in identity or
            identity in seen_ids
        ):
            raise SourceUnavailable("Socrata row identity was invalid or duplicated")
        seen_ids.add(identity)
        reference_period = _parse_exact_date(
            row.get(series["date_field"]),
            series["date_format"],
        )
        if reference_period in seen_dates:
            raise SourceUnavailable("Socrata response contained a duplicate date")
        seen_dates.add(reference_period)
        for item in items:
            raw_value = row.get(item["field"])
            if raw_value is None or raw_value == "":
                raw_value = None
            else:
                if not isinstance(raw_value, str):
                    raw_value = str(raw_value)
                available_count += 1
            record = _project_tabular_record(
                source,
                item,
                item["field"],
                reference_period,
                raw_value,
                retrieved_at,
            )
            record["publisher_row_identity"] = identity
            records.append(record)
    if not records or not available_count:
        raise SourceUnavailable("Socrata response contained no available observations")
    return records


def _validate_fiscaldata_items(items, date_fields):
    expected_fields = frozenset((
        "event_date_field",
        "field",
        "forecast_horizon",
        "label",
        "series_id",
        "unit",
        "value_status",
    ))
    if not isinstance(items, list) or not items:
        raise SourceUnavailable("FiscalData items must be a nonempty list")
    projected = []
    for item in items:
        if not isinstance(item, dict) or frozenset(item) != expected_fields:
            raise SourceUnavailable("FiscalData item metadata was not exact")
        if item["event_date_field"] not in date_fields:
            raise SourceUnavailable(
                "FiscalData item event_date_field was not declared"
            )
        projected.append({
            "field": item["field"],
            "forecast_horizon": item["forecast_horizon"],
            "label": item["label"],
            "series_id": item["series_id"],
            "unit": item["unit"],
            "value_status": item["value_status"],
        })
    _validate_projected_items(projected, "field")
    return items


def _validate_fiscaldata_field_list(value, label, allow_empty=False):
    if (
        not isinstance(value, list) or
        (not allow_empty and not value) or
        any(not isinstance(item, str) or not item for item in value) or
        len(value) != len(set(value))
    ):
        raise SourceUnavailable("FiscalData %s was not exact" % label)
    return value


def _fiscaldata_integer(value, label):
    if not isinstance(value, str) or not re.match(r"^(?:0|[1-9]\d*)$", value):
        raise SourceUnavailable("FiscalData %s was not a canonical integer" % label)
    return int(value)


def parse_fiscaldata_json(source, body, retrieved_at):
    """Project one complete, exact Treasury FiscalData response page."""
    payload = strict_publisher_json_loads(body)
    if (
        not isinstance(payload, dict) or
        frozenset(payload) != frozenset(("data", "links", "meta"))
    ):
        raise SourceUnavailable("FiscalData envelope keys were not exact")
    rows = payload["data"]
    links = payload["links"]
    meta = payload["meta"]
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("FiscalData response contained no rows")
    if (
        not isinstance(links, dict) or
        frozenset(links) !=
        frozenset(("self", "first", "prev", "next", "last"))
    ):
        raise SourceUnavailable("FiscalData links metadata was not exact")
    if (
        not isinstance(meta, dict) or
        frozenset(meta) != frozenset((
            "count",
            "dataFormats",
            "dataTypes",
            "labels",
            "total-count",
            "total-pages",
        ))
    ):
        raise SourceUnavailable("FiscalData meta keys were not exact")

    series = source.get("series")
    expected_series_fields = frozenset((
        "date_fields",
        "dimension_fields",
        "expected_data_types",
        "identity_fields",
        "items",
        "missing_tokens",
    ))
    if not isinstance(series, dict) or frozenset(series) != expected_series_fields:
        raise SourceUnavailable("FiscalData series metadata was not exact")
    date_fields = _validate_fiscaldata_field_list(
        series["date_fields"],
        "date_fields",
    )
    dimension_fields = _validate_fiscaldata_field_list(
        series["dimension_fields"],
        "dimension_fields",
        allow_empty=True,
    )
    identity_fields = _validate_fiscaldata_field_list(
        series["identity_fields"],
        "identity_fields",
    )
    if not set(date_fields).intersection(identity_fields):
        raise SourceUnavailable("FiscalData identity omitted every date field")
    expected_data_types = series["expected_data_types"]
    if (
        not isinstance(expected_data_types, dict) or
        not expected_data_types or
        any(
            not isinstance(field, str) or not field or
            not isinstance(data_type, str) or not data_type
            for field, data_type in expected_data_types.items()
        )
    ):
        raise SourceUnavailable("FiscalData expected data types were not exact")
    missing_tokens = series["missing_tokens"]
    if missing_tokens != ["null"]:
        raise SourceUnavailable("FiscalData missing token contract was not exact")
    items = _validate_fiscaldata_items(series["items"], date_fields)
    required_fields = (
        set(date_fields) |
        set(dimension_fields) |
        set(identity_fields) |
        {item["field"] for item in items}
    )
    if not required_fields.issubset(expected_data_types):
        raise SourceUnavailable(
            "FiscalData configured fields were absent from expected data types"
        )
    context_fields = sorted(set(expected_data_types) - required_fields)
    for key in ("dataTypes", "dataFormats", "labels"):
        value = meta[key]
        if (
            not isinstance(value, dict) or
            set(value) != set(expected_data_types)
        ):
            raise SourceUnavailable(
                "FiscalData %s field set was not exact" % key
            )
    if meta["dataTypes"] != expected_data_types:
        raise SourceUnavailable("FiscalData data types differed from the contract")
    count = _fiscaldata_integer(meta["count"], "count")
    total_count = _fiscaldata_integer(meta["total-count"], "total-count")
    total_pages = _fiscaldata_integer(meta["total-pages"], "total-pages")
    if (
        count != len(rows) or
        total_count != count or
        total_pages != 1 or
        links["next"] is not None
    ):
        raise SourceUnavailable("FiscalData response was a partial page")

    records = []
    row_identities = set()
    projection_identities = set()
    dimension_digest_values = {}
    available_count = 0
    for row in rows:
        if (
            not isinstance(row, dict) or
            set(row) != set(expected_data_types)
        ):
            raise SourceUnavailable("FiscalData row field set was not exact")
        if any(not isinstance(value, str) for value in row.values()):
            raise SourceUnavailable("FiscalData row cells must be strings")

        clocks = {}
        for field in date_fields:
            clocks[field] = _parse_exact_date(row[field], "%Y-%m-%d")
        identity_values = []
        identity_mapping = {}
        for field in identity_fields:
            value = row[field]
            if not value or value == "null" or "\r" in value or "\n" in value:
                raise SourceUnavailable("FiscalData row identity was invalid")
            identity_values.append(value)
            identity_mapping[field] = value
        identity_bytes = json.dumps(
            identity_values,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        row_identity = hashlib.sha256(identity_bytes).hexdigest()
        if row_identity in row_identities:
            raise SourceUnavailable("FiscalData row identity was duplicated")
        row_identities.add(row_identity)

        dimensions = {}
        dimension_values = []
        for field in dimension_fields:
            value = row[field]
            if not value or value == "null" or "\r" in value or "\n" in value:
                raise SourceUnavailable("FiscalData dimension was invalid")
            dimensions[field] = value
            dimension_values.append([field, value])
        dimension_suffix = None
        if dimension_values:
            dimension_bytes = json.dumps(
                dimension_values,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            dimension_suffix = hashlib.sha256(dimension_bytes).hexdigest()
            prior_values = dimension_digest_values.setdefault(
                dimension_suffix,
                tuple(tuple(item) for item in dimension_values),
            )
            if prior_values != tuple(tuple(item) for item in dimension_values):
                raise SourceUnavailable("FiscalData dimension hash collision")

        for item in items:
            raw_value = row[item["field"]]
            if raw_value == "null":
                raw_value = None
            elif not _CANONICAL_DECIMAL_RE.match(raw_value):
                raise SourceUnavailable(
                    "FiscalData field %s was not a canonical decimal" %
                    item["field"]
                )
            else:
                available_count += 1
            series_id = item["series_id"]
            if dimension_suffix is not None:
                series_id = "%s.%s" % (series_id, dimension_suffix)
            if not _SERIES_ID_RE.match(series_id):
                raise SourceUnavailable(
                    "FiscalData derived series identity was invalid"
                )
            projection_identity = (row_identity, series_id)
            if projection_identity in projection_identities:
                raise SourceUnavailable(
                    "FiscalData row/series projection was duplicated"
                )
            projection_identities.add(projection_identity)
            projected_item = dict(item)
            projected_item["series_id"] = series_id
            record = _project_tabular_record(
                source,
                projected_item,
                item["field"],
                clocks[item["event_date_field"]],
                raw_value,
                retrieved_at,
            )
            record["publisher_clocks"] = dict(clocks)
            record["publisher_context"] = {
                field: row[field]
                for field in context_fields
            }
            record["publisher_dimensions"] = dict(dimensions)
            record["publisher_identity"] = dict(identity_mapping)
            record["publisher_row_identity"] = row_identity
            records.append(record)
    if not records or not available_count:
        raise SourceUnavailable(
            "FiscalData response contained no available observations"
        )
    return records


def parse_treasury_mts_totals_json(source, body, retrieved_at):
    """Validate and project exact Treasury MTS Table 2 national totals."""
    if (
        source.get("source_id") != "treasury_mts_summary_totals" or
        source.get("adapter") != "treasury_mts_totals_json" or
        source.get("method_version") != "treasury_mts_table_2_totals.v1" or
        source.get("information_set_mode") != "current_revised"
    ):
        raise SourceUnavailable("Treasury MTS source contract identity differs")

    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict) or set(payload) != {"data", "links", "meta"}:
        raise SourceUnavailable("Treasury MTS envelope was not exact")
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("Treasury MTS contained no rows")

    expected_fields = {
        "classification_desc",
        "current_fytd_budget_amt",
        "current_month_budget_amt",
        "data_type_cd",
        "line_code_nbr",
        "prior_fytd_budget_amt",
        "record_calendar_day",
        "record_calendar_month",
        "record_calendar_quarter",
        "record_calendar_year",
        "record_date",
        "record_fiscal_quarter",
        "record_fiscal_year",
        "record_type_cd",
        "src_line_nbr",
        "table_nbr",
    }
    line_contract = {
        "20": ("2", "Total Receipts", "RECEIPTS"),
        "50": ("5", "Total Outlays", "OUTLAYS"),
        "80": (
            "8",
            "Total Surplus (+) or Deficit (-)",
            "DEFICIT_SURPLUS",
        ),
    }
    amount_fields = (
        "current_month_budget_amt",
        "current_fytd_budget_amt",
        "prior_fytd_budget_amt",
    )
    groups = {}
    observed_order = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise SourceUnavailable("Treasury MTS row field set was not exact")
        if any(not isinstance(value, str) for value in row.values()):
            raise SourceUnavailable("Treasury MTS row cells must be strings")
        try:
            stamp = datetime.strptime(row["record_date"], "%Y-%m-%d")
        except ValueError as exc:
            raise SourceUnavailable("Treasury MTS date was invalid") from exc
        if stamp.day != calendar.monthrange(stamp.year, stamp.month)[1]:
            raise SourceUnavailable("Treasury MTS date was not month end")
        expected_calendar = {
            "record_calendar_year": str(stamp.year),
            "record_calendar_quarter": str((stamp.month - 1) // 3 + 1),
            "record_calendar_month": "%02d" % stamp.month,
            "record_calendar_day": "%02d" % stamp.day,
        }
        if any(row[field] != value for field, value in expected_calendar.items()):
            raise SourceUnavailable("Treasury MTS calendar identity differed")
        fiscal_year = stamp.year + 1 if stamp.month >= 10 else stamp.year
        fiscal_quarter = ((stamp.month - 10) % 12) // 3 + 1
        if (
            row["record_fiscal_year"] != str(fiscal_year) or
            row["record_fiscal_quarter"] != str(fiscal_quarter)
        ):
            raise SourceUnavailable("Treasury MTS fiscal identity differed")
        line_code = row["line_code_nbr"]
        if line_code not in line_contract:
            raise SourceUnavailable("Treasury MTS line code was not admitted")
        source_line, classification, _ = line_contract[line_code]
        if (
            row["src_line_nbr"] != source_line or
            row["classification_desc"] != classification or
            row["table_nbr"] != "2" or
            row["data_type_cd"] != "T" or
            row["record_type_cd"] != "SL"
        ):
            raise SourceUnavailable("Treasury MTS line contract differed")
        for field in amount_fields:
            if not _CANONICAL_DECIMAL_RE.match(row[field]):
                raise SourceUnavailable(
                    "Treasury MTS amount was not a canonical decimal"
                )
        period_rows = groups.setdefault(row["record_date"], {})
        if line_code in period_rows:
            raise SourceUnavailable("Treasury MTS total line was duplicated")
        period_rows[line_code] = row
        observed_order.append((row["record_date"], int(line_code)))

    if observed_order != sorted(observed_order):
        raise SourceUnavailable("Treasury MTS rows were not canonically ordered")
    periods = sorted(groups)
    for index, period in enumerate(periods):
        if set(groups[period]) != set(line_contract):
            raise SourceUnavailable("Treasury MTS period total set was incomplete")
        if index:
            previous = datetime.strptime(periods[index - 1], "%Y-%m-%d")
            current = datetime.strptime(period, "%Y-%m-%d")
            next_year = previous.year + (1 if previous.month == 12 else 0)
            next_month = 1 if previous.month == 12 else previous.month + 1
            if (current.year, current.month) != (next_year, next_month):
                raise SourceUnavailable("Treasury MTS monthly history had a gap")
        receipts = groups[period]["20"]
        outlays = groups[period]["50"]
        balance = groups[period]["80"]
        for field in amount_fields:
            if Decimal(receipts[field]) - Decimal(outlays[field]) != Decimal(
                balance[field]
            ):
                raise SourceUnavailable(
                    "Treasury MTS accounting identity did not reconcile"
                )

    records = parse_fiscaldata_json(source, body, retrieved_at)
    measure_names = {
        "current_month_budget_amt": "CURRENT_MONTH",
        "current_fytd_budget_amt": "CURRENT_FYTD",
        "prior_fytd_budget_amt": "PRIOR_FYTD",
    }
    measure_labels = {
        "current_month_budget_amt": "current month",
        "current_fytd_budget_amt": "current fiscal year to date",
        "prior_fytd_budget_amt": "prior fiscal year to date",
    }
    for record in records:
        line_code = record["publisher_dimensions"].get("line_code_nbr")
        if line_code not in line_contract or record["publisher_field"] not in measure_names:
            raise SourceUnavailable("Treasury MTS projection identity differed")
        _, _, line_name = line_contract[line_code]
        record["series_id"] = "TREASURY.MTS.%s.%s" % (
            line_name,
            measure_names[record["publisher_field"]],
        )
        record["label"] = "%s, %s" % (
            line_contract[line_code][1],
            measure_labels[record["publisher_field"]],
        )
        record["measurement_basis"] = (
            "Treasury Monthly Statement Table 2 national accounting total"
        )
    return records


def _exact_decimal_or_none(value, field, allow_scientific=False):
    if value in ("", None):
        return None
    if not isinstance(value, str):
        raise SourceUnavailable("%s was not a string" % field)
    if _STRICT_DECIMAL_RE.match(value):
        return value
    if allow_scientific and _SCIENTIFIC_DECIMAL_RE.match(value):
        try:
            normalized = format(Decimal(value), "f")
        except InvalidOperation:
            raise SourceUnavailable("%s was not an exact decimal" % field)
        if not _STRICT_DECIMAL_RE.match(normalized):
            raise SourceUnavailable(
                "%s did not normalize to a canonical decimal" % field
            )
        return normalized
    raise SourceUnavailable("%s was not a canonical decimal" % field)


def parse_fhfa_hpi_csv(source, body, retrieved_at):
    """Project the exact national monthly purchase-only FHFA HPI rows."""
    if source.get("series") != {}:
        raise SourceUnavailable("FHFA HPI series metadata must be empty")
    expected = [
        "hpi_type",
        "hpi_flavor",
        "frequency",
        "level",
        "place_name",
        "place_id",
        "yr",
        "period",
        "index_nsa",
        "index_sa",
        "rstderr",
        "note",
    ]
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("FHFA HPI CSV was not valid UTF-8: %s" % exc)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != expected:
        raise SourceUnavailable("FHFA HPI CSV header was not exact")

    rows = []
    seen_periods = set()
    for row in reader:
        if row.get(None) or set(row) != set(expected):
            raise SourceUnavailable("FHFA HPI row width was not exact")
        if any(value is None for value in row.values()):
            raise SourceUnavailable("FHFA HPI row contained a missing cell")
        if (
            row["hpi_type"] != "traditional" or
            row["hpi_flavor"] != "purchase-only" or
            row["frequency"] != "monthly" or
            row["level"] != "USA or Census Division" or
            row["place_name"] != "United States" or
            row["place_id"] != "USA"
        ):
            continue
        year = row["yr"]
        month = row["period"]
        if (
            not re.match(r"^\d{4}$", year) or
            not re.match(r"^\d{1,2}$", month)
        ):
            raise SourceUnavailable("FHFA HPI observation period was malformed")
        month_number = int(month)
        if month_number < 1 or month_number > 12:
            raise SourceUnavailable("FHFA HPI month was outside 1..12")
        reference_period = "%s-%02d-01" % (year, month_number)
        if reference_period in seen_periods:
            raise SourceUnavailable(
                "FHFA HPI national monthly period was duplicated"
            )
        seen_periods.add(reference_period)
        nsa = _exact_decimal_or_none(row["index_nsa"], "FHFA index_nsa")
        sa = _exact_decimal_or_none(row["index_sa"], "FHFA index_sa")
        rstderr = _exact_decimal_or_none(row["rstderr"], "FHFA rstderr")
        if nsa is None and sa is None:
            raise SourceUnavailable("FHFA HPI row had no index value")
        rows.append((
            reference_period,
            nsa,
            sa,
            rstderr,
            row["note"] or None,
        ))
    if not rows:
        raise SourceUnavailable(
            "FHFA HPI CSV contained no national monthly purchase-only rows"
        )

    records = []
    items = (
        (
            "index_nsa",
            "FHFA.HPI.PO.USA.NSA",
            "FHFA national purchase-only HPI, not seasonally adjusted",
            "index",
        ),
        (
            "index_sa",
            "FHFA.HPI.PO.USA.SA",
            "FHFA national purchase-only HPI, seasonally adjusted",
            "index",
        ),
        (
            "rstderr",
            "FHFA.HPI.PO.USA.RSTDERR",
            "FHFA national purchase-only HPI relative standard error",
            "relative standard error",
        ),
    )
    for reference_period, nsa, sa, rstderr, note in sorted(rows):
        values = (nsa, sa, rstderr)
        for item, value in zip(items, values):
            field, series_id, label, unit = item
            record = _project_tabular_record(
                source,
                {
                    "forecast_horizon": None,
                    "label": label,
                    "series_id": series_id,
                    "unit": unit,
                    "value_status": source["value_status"],
                },
                field,
                reference_period,
                value,
                retrieved_at,
            )
            record["publisher_context"] = {
                "frequency": "monthly",
                "hpi_flavor": "purchase-only",
                "hpi_type": "traditional",
                "level": "USA or Census Division",
                "note": note,
                "place_id": "USA",
                "place_name": "United States",
            }
            records.append(record)
    return records


_FHFA_AT_QUARTER_MONTH = {"1": 1, "2": 4, "3": 7, "4": 10}


def parse_fhfa_hpi_at_geo_csv(source, body, retrieved_at):
    """Project FHFA all-transactions HPI, headerless state or metro quarterly.

    Publisher-direct quarterly datasets. Two headerless layouts, selected by the
    spec's ``series.layout``:
      * ``state`` -- 4 columns: place_abbr, yr, quarter, index.
      * ``metro`` -- 6 columns: place_name, cbsa_id, yr, quarter, index,
        standard_error (formatted ``( n.nn)``).
    Each geography is its own series (section 3.1); the file is one source id
    (state and metro are distinct geo cross-sections). ``-`` is the publisher's
    missing token and lands as ``unavailable``, never dropped. Derives NOTHING
    (section 22.4): the all-transactions index is publisher output landed raw.
    """
    series = source.get("series")
    required = frozenset((
        "layout",
        "geography_type",
        "index_semantics",
        "series_id_prefix",
        "index_unit",
    ))
    if not isinstance(series, dict) or not required.issubset(series):
        raise SourceUnavailable("FHFA AT geo series metadata was not exact")
    layout = series["layout"]
    if layout not in ("state", "metro"):
        raise SourceUnavailable("FHFA AT geo layout was not state or metro")
    if layout == "metro" and "stderr_unit" not in series:
        raise SourceUnavailable("FHFA AT metro requires a stderr_unit")
    width = 4 if layout == "state" else 6
    prefix = series["series_id_prefix"]
    index_semantics = series["index_semantics"]

    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("FHFA AT geo CSV was not valid UTF-8: %s" % exc)
    reader = csv.reader(io.StringIO(text, newline=""))

    records = []
    seen = set()
    available = 0
    for row in reader:
        if not row:
            continue
        if len(row) != width:
            raise SourceUnavailable("FHFA AT geo row width was not exact")
        if layout == "state":
            place_id, place_name = row[0], row[0]
            year, quarter, raw_index = row[1], row[2], row[3]
            raw_stderr = None
        else:
            place_name, place_id = row[0], row[1]
            year, quarter, raw_index, raw_stderr = row[2], row[3], row[4], row[5]
        if not place_id or "\r" in place_id or "\n" in place_id:
            raise SourceUnavailable("FHFA AT geo place id was invalid")
        if not re.match(r"^\d{4}$", year):
            raise SourceUnavailable("FHFA AT geo year was malformed")
        if quarter not in _FHFA_AT_QUARTER_MONTH:
            raise SourceUnavailable("FHFA AT geo quarter was outside 1..4")
        reference_period = "%s-%02d-01" % (
            year, _FHFA_AT_QUARTER_MONTH[quarter])

        items = [(
            "index",
            "%s.%s" % (prefix, place_id),
            "FHFA all-transactions HPI (%s), %s" % (
                index_semantics, place_name),
            series["index_unit"],
            raw_index,
        )]
        if layout == "metro":
            stderr_value = raw_stderr
            if stderr_value not in ("-", "", None):
                stripped = stderr_value.strip()
                if not re.match(r"^\(\s*-?\d+(?:\.\d+)?\)$", stripped):
                    raise SourceUnavailable(
                        "FHFA AT metro standard error was malformed")
                stderr_value = stripped[1:-1].strip()
            items.append((
                "standard_error",
                "%s.%s.RSTDERR" % (prefix, place_id),
                "FHFA all-transactions HPI standard error, %s" % place_name,
                series["stderr_unit"],
                stderr_value,
            ))

        for field, series_id, label, unit, raw_value in items:
            key = (series_id, reference_period)
            if key in seen:
                raise SourceUnavailable(
                    "FHFA AT geo period was duplicated for a series")
            seen.add(key)
            value = None if raw_value in ("-", "", None) else raw_value
            if value is not None:
                available += 1
            record = _project_tabular_record(
                source,
                {
                    "forecast_horizon": None,
                    "label": label,
                    "series_id": series_id,
                    "unit": unit,
                    "value_status": source["value_status"],
                },
                field,
                reference_period,
                value,
                retrieved_at,
            )
            record["publisher_context"] = {
                "geography_type": series["geography_type"],
                "hpi_type": "all_transactions",
                "index_semantics": index_semantics,
                "place_id": place_id,
                "place_name": place_name,
                "quarter": quarter,
            }
            records.append(record)
    if not records or not available:
        raise SourceUnavailable(
            "FHFA AT geo CSV contained no available observations")
    return records


_BEA_CAINC_META_COLS = 8  # GeoFIPS..Unit precede the annual value columns.
_BEA_CAINC_MISSING = frozenset(("(NA)", "(D)", "(L)", "(NM)", "(T)", ""))


def _bea_cainc_geography_type(geo_fips):
    """Classify a BEA regional GeoFIPS into a distinct geo cross-section.

    ``00000`` is the U.S. aggregate; ``9x000`` are the eight BEA regions;
    other codes ending in ``000`` are states or DC; everything else is a
    county (or county-equivalent). Each class is landed as its own source id
    (section 3.1) — the ALL_AREAS file is never collapsed across geographies.
    """
    if geo_fips == "00000":
        return "national_us"
    if re.match(r"^9\d000$", geo_fips):
        return "bea_region"
    if geo_fips.endswith("000"):
        return "state_or_dc"
    return "county"


def parse_bea_regional_cainc_zip(source, body, retrieved_at):
    """Project one geography cross-section of a BEA Regional ALL_AREAS zip.

    Serves any BEA Regional bulk zip built on the ``TABLE__ALL_AREAS`` shape —
    the CAINC personal-income family and the SAGDP state-GDP family alike.
    A zip may ship one such table (CAINC1.zip) or several (SAGDP.zip carries
    SAGDP1 + SAGDP2); the requested ``series.table`` selects the member.

    The publisher ships one ``TABLE__ALL_AREAS_YYYY_YYYY.csv`` inside the zip
    mixing the U.S. aggregate, BEA regions, states/DC, and counties, each with
    several LineCodes (personal income, population, per capita income) across
    annual columns. The spec's ``series.geography_type`` selects exactly one
    cross-section; each ``{prefix}.{GeoFIPS}.L{LineCode}`` is its own series
    (section 3.1) and each annual column its own observation. The publisher's
    ``(NA)`` / ``(D)`` tokens land as ``unavailable`` and are never dropped
    (section 19.4). Derives NOTHING (section 22.4): personal income,
    population, and BEA's own per-capita line are landed raw as published.
    """
    series = source.get("series")
    required = frozenset(("geography_type", "series_id_prefix", "table"))
    if not isinstance(series, dict) or not required.issubset(series):
        raise SourceUnavailable("BEA CAINC series metadata was not exact")
    want_geo = series["geography_type"]
    if want_geo not in (
            "national_us", "bea_region", "state_or_dc", "county"):
        raise SourceUnavailable("BEA CAINC geography_type was not recognized")
    prefix = series["series_id_prefix"]
    table = series["table"]

    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as exc:
        raise SourceUnavailable("BEA CAINC body was not a zip: %s" % exc)
    # A BEA Regional zip may carry MORE THAN ONE ALL_AREAS table (SAGDP.zip
    # ships SAGDP1 + SAGDP2); select the member whose ``TABLE__`` prefix matches
    # the requested table rather than the first ALL_AREAS member, so the shared
    # adapter is honest on multi-table zips as well as the single-table CAINC
    # family.
    member = None
    saw_all_areas = False
    for name in archive.namelist():
        if not re.search(r"__ALL_AREAS_\d{4}_\d{4}\.csv$", name):
            continue
        saw_all_areas = True
        if name.split("__", 1)[0].endswith(table):
            member = name
            break
    if member is None:
        if saw_all_areas:
            raise SourceUnavailable(
                "BEA CAINC ALL_AREAS member was not %s" % table)
        raise SourceUnavailable("BEA CAINC zip had no ALL_AREAS csv member")

    text = archive.read(member).decode("latin-1")
    reader = csv.reader(io.StringIO(text, newline=""), skipinitialspace=True)
    header = next(reader, None)
    if not header or header[0] != "GeoFIPS" or header[3] != "TableName":
        raise SourceUnavailable("BEA CAINC ALL_AREAS header was not exact")
    # Value columns are either annual ("YYYY", CAINC/SAGDP/SAINC) or quarterly
    # ("YYYY:Qn", SQINC/SQGDP). Canonicalize once from the header: annual lands
    # the ISO first-of-year day this adapter has always used; quarterly lands the
    # project "YYYY-Qn" convention (parse_bea_api, §24.7) without inventing a day.
    # A header that mixes the two is a schema failure, not a silent coercion.
    period_cols = header[_BEA_CAINC_META_COLS:]
    if period_cols and all(re.match(r"^\d{4}$", p) for p in period_cols):
        reference_periods = ["%s-01-01" % p for p in period_cols]
    elif period_cols and all(re.match(r"^\d{4}:Q[1-4]$", p) for p in period_cols):
        reference_periods = ["%s-Q%s" % (p[:4], p[6]) for p in period_cols]
    else:
        raise SourceUnavailable("BEA CAINC period columns were malformed")
    ncol = len(header)

    records = []
    seen = set()
    available = 0
    for row in reader:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) != ncol:
            # Trailing publisher note lines are shorter; a same-width drift is
            # a schema failure. Notes carry no GeoFIPS digits.
            if row and re.match(r"^\d{5}$", row[0].strip()):
                raise SourceUnavailable("BEA CAINC row width was not exact")
            continue
        geo_fips = row[0].strip()
        if not re.match(r"^\d{5}$", geo_fips):
            continue
        if _bea_cainc_geography_type(geo_fips) != want_geo:
            continue
        if row[3].strip() != table:
            raise SourceUnavailable("BEA CAINC TableName drifted from %s" % table)
        geo_name = row[1].strip()
        line_code = row[4].strip()
        description = row[6].strip()
        unit = row[7].strip()
        if not line_code or not unit:
            raise SourceUnavailable("BEA CAINC LineCode or Unit was empty")
        series_id = "%s.%s.L%s" % (prefix, geo_fips, line_code)
        for reference_period, raw in zip(
                reference_periods, row[_BEA_CAINC_META_COLS:]):
            key = (series_id, reference_period)
            if key in seen:
                raise SourceUnavailable(
                    "BEA CAINC period was duplicated for a series")
            seen.add(key)
            token = raw.strip()
            value = None if token in _BEA_CAINC_MISSING else token
            if value is not None:
                available += 1
            record = _project_tabular_record(
                source,
                {
                    "forecast_horizon": None,
                    "label": "BEA %s %s, %s" % (table, description, geo_name),
                    "series_id": series_id,
                    "unit": unit,
                    "value_status": source["value_status"],
                },
                "line_%s" % line_code,
                reference_period,
                value,
                retrieved_at,
            )
            record["publisher_context"] = {
                "table": table,
                "geography_type": want_geo,
                "geo_fips": geo_fips,
                "geo_name": geo_name,
                "line_code": line_code,
                "description": description,
            }
            records.append(record)
    if not records or not available:
        raise SourceUnavailable(
            "BEA CAINC cross-section contained no available observations")
    return records


def parse_ofr_fsi_csv(source, body, retrieved_at):
    """Project OFR's published daily aggregate and contribution series."""
    if source.get("series") != {}:
        raise SourceUnavailable("OFR FSI series metadata must be empty")
    expected = [
        "Date",
        "OFR FSI",
        "Credit",
        "Equity valuation",
        "Safe assets",
        "Funding",
        "Volatility",
        "United States",
        "Other advanced economies",
        "Emerging markets",
    ]
    mapping = (
        ("OFR FSI", "OFR.FSI.TOTAL", "OFR Financial Stress Index"),
        ("Credit", "OFR.FSI.CREDIT", "OFR FSI credit contribution"),
        (
            "Equity valuation",
            "OFR.FSI.EQUITY_VALUATION",
            "OFR FSI equity-valuation contribution",
        ),
        (
            "Safe assets",
            "OFR.FSI.SAFE_ASSETS",
            "OFR FSI safe-assets contribution",
        ),
        ("Funding", "OFR.FSI.FUNDING", "OFR FSI funding contribution"),
        (
            "Volatility",
            "OFR.FSI.VOLATILITY",
            "OFR FSI volatility contribution",
        ),
        (
            "United States",
            "OFR.FSI.UNITED_STATES",
            "OFR FSI United States contribution",
        ),
        (
            "Other advanced economies",
            "OFR.FSI.OTHER_ADVANCED_ECONOMIES",
            "OFR FSI other-advanced-economies contribution",
        ),
        (
            "Emerging markets",
            "OFR.FSI.EMERGING_MARKETS",
            "OFR FSI emerging-markets contribution",
        ),
    )
    try:
        text = body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("OFR FSI CSV was not valid UTF-8: %s" % exc)
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != expected:
        raise SourceUnavailable("OFR FSI CSV header was not exact")

    records = []
    seen_dates = set()
    for row in reader:
        if row.get(None) or set(row) != set(expected):
            raise SourceUnavailable("OFR FSI row width was not exact")
        if any(value is None for value in row.values()):
            raise SourceUnavailable("OFR FSI row contained a missing cell")
        reference_period = _parse_exact_date(row["Date"], "%Y-%m-%d")
        if reference_period in seen_dates:
            raise SourceUnavailable("OFR FSI date was duplicated")
        seen_dates.add(reference_period)
        projected = []
        for field, series_id, label in mapping:
            value = _exact_decimal_or_none(
                row[field],
                "OFR %s" % field,
                allow_scientific=True,
            )
            if field == "OFR FSI" and value is None:
                raise SourceUnavailable("OFR FSI total was missing")
            projected.append((field, series_id, label, value))
        for field, series_id, label, value in projected:
            record = _project_tabular_record(
                source,
                {
                    "forecast_horizon": None,
                    "label": label,
                    "series_id": series_id,
                    "unit": "index contribution",
                    "value_status": source["value_status"],
                },
                field,
                reference_period,
                value,
                retrieved_at,
            )
            record["publisher_context"] = {
                "published_output_only": True,
                "underlying_component_rights": "mixed",
            }
            records.append(record)
    if not records:
        raise SourceUnavailable("OFR FSI CSV contained no observations")
    return records


def _exact_integer_string(value, field):
    if not isinstance(value, str) or not re.match(
        r"^-?(?:0|[1-9]\d*)$",
        value,
    ):
        raise SourceUnavailable("%s was not a canonical integer" % field)
    return value


def parse_fdic_aggregate_json(source, body, retrieved_at):
    """Project quarterly FDIC aggregate banking-system observations."""
    if source.get("series") != {}:
        raise SourceUnavailable("FDIC aggregate series metadata must be empty")
    payload = strict_publisher_json_loads(body)
    if not isinstance(payload, dict) or set(payload) != {"data", "meta", "totals"}:
        raise SourceUnavailable("FDIC aggregate top-level schema was not exact")
    if not isinstance(payload["meta"], dict) or not isinstance(payload["totals"], dict):
        raise SourceUnavailable("FDIC aggregate metadata shape was invalid")
    rows = payload["data"]
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("FDIC aggregate response contained no rows")

    required = {
        "REPDTE",
        "count",
        "sum_ASSET",
        "sum_DEP",
        "sum_LNLSNET",
        "sum_NETINC",
    }
    projected_rows = []
    seen_dates = set()
    for wrapper in rows:
        if (
            not isinstance(wrapper, dict) or
            set(wrapper) != {"data"} or
            not isinstance(wrapper["data"], dict)
        ):
            raise SourceUnavailable("FDIC aggregate row shape was invalid")
        row = wrapper["data"]
        if set(row) != required:
            raise SourceUnavailable("FDIC aggregate row fields were not exact")
        raw_date = row["REPDTE"]
        if not isinstance(raw_date, str) or not re.match(r"^\d{8}$", raw_date):
            raise SourceUnavailable("FDIC aggregate report date was malformed")
        try:
            parsed = datetime.strptime(raw_date, "%Y%m%d")
        except ValueError:
            raise SourceUnavailable("FDIC aggregate report date was invalid")
        if (parsed.month, parsed.day) not in (
            (3, 31),
            (6, 30),
            (9, 30),
            (12, 31),
        ):
            raise SourceUnavailable(
                "FDIC aggregate report date was not a quarter end"
            )
        reference_period = parsed.date().isoformat()
        if reference_period in seen_dates:
            raise SourceUnavailable("FDIC aggregate report date was duplicated")
        seen_dates.add(reference_period)
        projected_rows.append((
            reference_period,
            _exact_integer_string(row["count"], "FDIC count"),
            _exact_integer_string(row["sum_ASSET"], "FDIC sum_ASSET"),
            _exact_integer_string(row["sum_DEP"], "FDIC sum_DEP"),
            _exact_integer_string(row["sum_LNLSNET"], "FDIC sum_LNLSNET"),
            _exact_integer_string(row["sum_NETINC"], "FDIC sum_NETINC"),
        ))

    items = (
        (
            "count",
            "FDIC.BANKS.REPORTING_INSTITUTIONS",
            "FDIC reporting institution count",
            "institutions",
            "stock",
        ),
        (
            "sum_ASSET",
            "FDIC.BANKS.ASSETS",
            "FDIC aggregate bank assets",
            "USD thousands",
            "quarter_end_stock",
        ),
        (
            "sum_DEP",
            "FDIC.BANKS.DEPOSITS",
            "FDIC aggregate bank deposits",
            "USD thousands",
            "quarter_end_stock",
        ),
        (
            "sum_LNLSNET",
            "FDIC.BANKS.NET_LOANS_LEASES",
            "FDIC aggregate net loans and leases",
            "USD thousands",
            "quarter_end_stock",
        ),
        (
            "sum_NETINC",
            "FDIC.BANKS.NET_INCOME_YTD",
            "FDIC aggregate net income year-to-date",
            "USD thousands year-to-date",
            "year_to_date_not_single_quarter",
        ),
    )
    records = []
    for projected_row in sorted(projected_rows):
        reference_period = projected_row[0]
        for item, value in zip(items, projected_row[1:]):
            field, series_id, label, unit, flow_semantics = item
            record = _project_tabular_record(
                source,
                {
                    "forecast_horizon": None,
                    "label": label,
                    "series_id": series_id,
                    "unit": unit,
                    "value_status": source["value_status"],
                },
                field,
                reference_period,
                value,
                retrieved_at,
            )
            record["publisher_context"] = {
                "aggregation": "all_reporting_institutions",
                "flow_semantics": flow_semantics,
            }
            records.append(record)
    return records


class _TsaTableParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.tables = []
        self.invalid = False
        self._table = None
        self._table_depth = 0
        self._row = None
        self._cell_tag = None
        self._cell_text = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            if self._table_depth:
                self.invalid = True
            self._table_depth += 1
            if self._table_depth == 1:
                classes = dict(attrs).get("class", "").split()
                self._table = {
                    "classes": classes,
                    "rows": [],
                }
            return
        if self._table_depth != 1:
            return
        if tag == "tr":
            if self._row is not None:
                self.invalid = True
            self._row = []
        elif tag in ("th", "td"):
            if self._row is None or self._cell_tag is not None:
                self.invalid = True
            self._cell_tag = tag
            self._cell_text = []

    def handle_data(self, data):
        if self._cell_text is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("th", "td") and self._table_depth == 1:
            if self._cell_tag != tag or self._cell_text is None:
                self.invalid = True
                return
            text = " ".join("".join(self._cell_text).split())
            self._row.append((tag, text))
            self._cell_tag = None
            self._cell_text = None
        elif tag == "tr" and self._table_depth == 1:
            if self._row is None or self._cell_tag is not None:
                self.invalid = True
                return
            if self._row:
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table":
            if self._table_depth <= 0:
                self.invalid = True
                return
            if self._table_depth == 1:
                if self._row is not None or self._cell_tag is not None:
                    self.invalid = True
                self.tables.append(self._table)
                self._table = None
            self._table_depth -= 1


def parse_tsa_passenger_html(source, body, retrieved_at):
    """Extract TSA's exact current-year Date/Numbers table."""
    if source.get("series") != {}:
        raise SourceUnavailable("TSA passenger series metadata must be empty")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceUnavailable("TSA webpage was not valid UTF-8: %s" % exc)
    parser = _TsaTableParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise SourceUnavailable("TSA webpage HTML could not be parsed: %s" % exc)
    if (
        parser.invalid or
        parser._table_depth or
        parser._row is not None or
        parser._cell_tag is not None
    ):
        raise SourceUnavailable("TSA webpage table structure was invalid")
    matches = [
        table
        for table in parser.tables
        if (
            "table" in table["classes"] and
            table["rows"] and
            table["rows"][0] == [("th", "Date"), ("th", "Numbers")]
        )
    ]
    if len(matches) != 1:
        raise SourceUnavailable("TSA webpage lacked one exact passenger table")

    records = []
    seen_dates = set()
    date_re = re.compile(
        r"^(?P<month>[1-9]|1[0-2])/"
        r"(?P<day>[1-9]|[12]\d|3[01])/"
        r"(?P<year>\d{4})$"
    )
    count_re = re.compile(r"^(?:0|[1-9]\d{0,2}(?:,\d{3})*)$")
    for cells in matches[0]["rows"][1:]:
        if len(cells) != 2 or any(tag != "td" for tag, value in cells):
            raise SourceUnavailable("TSA passenger row shape was invalid")
        raw_date = cells[0][1]
        raw_count = cells[1][1]
        match = date_re.match(raw_date)
        if not match:
            raise SourceUnavailable("TSA passenger date was not canonical")
        try:
            parsed = datetime(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        except ValueError:
            raise SourceUnavailable("TSA passenger date was invalid")
        reference_period = parsed.date().isoformat()
        if reference_period in seen_dates:
            raise SourceUnavailable("TSA passenger date was duplicated")
        seen_dates.add(reference_period)
        if not count_re.match(raw_count):
            raise SourceUnavailable("TSA passenger count was not canonical")
        value = raw_count.replace(",", "")
        record = _base_record(
            source,
            "TSA.CHECKPOINT_THROUGHPUT",
            reference_period,
            value,
            "persons",
            retrieved_at,
        )
        record["label"] = "TSA checkpoint traveler throughput"
        record["provider_vintage_kind"] = source["information_set_mode"]
        record["publisher_field"] = "Numbers"
        record["publisher_row_identity"] = reference_period
        record["strict_publisher_first_release_proven"] = False
        records.append(record)
    if not records:
        raise SourceUnavailable("TSA passenger table contained no observations")
    return records


def parse_raw_capture(source, body, retrieved_at):
    """Record acquisition without pretending to understand unpublished schema."""
    return [{
        "available_at": retrieved_at,
        "forecast_horizon": None,
        "forecast_origin": None,
        "information_set_mode": source["information_set_mode"],
        "method_version": source["method_version"],
        "observation_period": None,
        "observed_at": None,
        "provenance_url": source["endpoint"],
        "publisher_release_clock": source["publisher_release_clock"],
        "release_at": None,
        "revision_sequence": None,
        "rights_status": source["rights_status"],
        "series_id": "%s.raw_capture" % source["source_id"],
        "source_id": source["source_id"],
        "unit": "publisher bytes",
        "value": None,
        "value_status": "unavailable",
    }]


def parse_treasury_dts_json(source, body, retrieved_at):
    """Project reviewed DTS rows onto three explicit amount series."""
    if (
        source["source_id"] != TREASURY_DTS_SOURCE_ID or
        source["method_version"] != TREASURY_DTS_METHOD_VERSION or
        not source["endpoint"].startswith(TREASURY_DTS_ENDPOINT + "?") or
        source["information_set_mode"] != "current_revised"
    ):
        raise SourceUnavailable("Treasury DTS source contract identity differs")
    try:
        rows = parse_treasury_dts_current_json(body, retrieved_at)
    except TreasuryDtsDataError as exc:
        raise SourceUnavailable("Treasury DTS contract failed: %s" % exc)
    result = []
    amount_fields = (
        ("today_amt", "daily"),
        ("mtd_amt", "month_to_date"),
        ("fytd_amt", "fiscal_year_to_date"),
    )
    for row in rows:
        for amount_field, suffix in amount_fields:
            record = dict(row)
            record.update({
                "forecast_horizon": None,
                "forecast_origin": None,
                "provenance_url": source["endpoint"],
                "publisher_release_clock": source["publisher_release_clock"],
                "release_at": None,
                "revision_sequence": None,
                "series_id": "%s.%s" % (source["source_id"], suffix),
                "source_id": source["source_id"],
                "unit": "USD millions",
                "value": row[amount_field],
                "value_status": source["value_status"],
            })
            result.append(record)
    return result


_DOL_UI_MEASURES = frozenset((
    "nsa_initial_claims",
    "sf_initial_claims",
    "sa_initial_claims",
    "sa_4_week_initial_claims",
    "nsa_continued_claims",
    "sf_continued_claims",
    "sa_continued_claims",
    "sa_4_week_continued_claims",
    "nsa_iur",
    "sa_iur",
    "cov_employment",
))
_DOL_UI_HEADER_RE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+([a-z0-9_]+)$")


class _DolUiReportParser(HTMLParser):
    """Collect (week_ending, measure, value) from report.asp <td headers=...> cells."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.cells = []
        self._current = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        if tag != "td":
            return
        header = dict(attrs).get("headers")
        if not header:
            return
        match = _DOL_UI_HEADER_RE.match(header.strip())
        if match:
            self._current = (match.group(1), match.group(2))
            self._buffer = []

    def handle_data(self, data):
        if self._current is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self._current is not None:
            week, measure = self._current
            self.cells.append((week, measure, "".join(self._buffer).strip()))
            self._current = None


def parse_dol_ui_weekly_claims_report_html(source, body, retrieved_at):
    """Parse the KEYLESS DOL/UI national weekly-claims report.asp HTML table.

    One record per (week-ending date, measure column). The report is keyed by
    week-ending date (the <th id="MM/DD/YYYY">, carried on each cell's headers=
    attribute), NOT by release date. Values are comma-formatted -> commas stripped.
    Any headered measure outside the fixed 11-column set raises (fail-closed).
    series_id = "DOL.UI.<COLID uppercased>"; information_set_mode from the source.
    """
    if isinstance(body, (bytes, bytearray)):
        text = body.decode("utf-8", "strict")
    else:
        text = body
    parser = _DolUiReportParser()
    parser.feed(text)
    parser.close()
    if not parser.cells:
        raise SourceUnavailable("DOL UI report contained no headered cells")

    unit = "count"
    series = source.get("series")
    if isinstance(series, dict) and isinstance(series.get("unit"), str) and series["unit"]:
        unit = series["unit"]

    records = []
    seen = set()
    available_count = 0
    for week, measure, raw_value in parser.cells:
        if measure not in _DOL_UI_MEASURES:
            raise SourceUnavailable(
                "DOL UI report had an unexpected measure column: %s" % measure
            )
        try:
            parsed_week = datetime.strptime(week, "%m/%d/%Y")
        except ValueError:
            raise SourceUnavailable("DOL UI report week-ending date was invalid")
        reference_period = parsed_week.strftime("%Y-%m-%d")
        series_id = "DOL.UI.%s" % measure.upper()
        identity = (series_id, reference_period)
        if identity in seen:
            raise SourceUnavailable("DOL UI report contained a duplicate cell")
        seen.add(identity)

        value = raw_value.replace(",", "").strip()
        unavailable = value in ("", "N/A", "-", "--")
        if not unavailable and not _CANONICAL_DECIMAL_RE.match(value):
            raise SourceUnavailable("DOL UI report value was not canonical decimal")
        record = _base_record(
            source,
            series_id,
            reference_period,
            None if unavailable else value,
            unit,
            retrieved_at,
        )
        record["provider_vintage_kind"] = source["information_set_mode"]
        if unavailable:
            record["value_status"] = "unavailable"
        else:
            available_count += 1
        records.append(record)

    if not records or not available_count:
        raise SourceUnavailable("DOL UI report contained no available observations")
    return records


def parse_dallas_wei_xlsx(source, body, retrieved_at):
    """Normalize the Dallas Fed WEI native workbook (evidence lane).

    B-OFFLINE-3 item 1. The workbook's current + embedded as-of columns land as a
    single flat offline-current EVIDENCE lane under one declared information-set
    mode (``substituted_diagnostic``); each as-of column keeps its snapshot date
    in the series_id AND as the additive per-record ``provider_asof_date``. These
    are NOT store-native archive_snapshot_asof vintages (see dallas_wei.py).
    """
    try:
        observations = parse_dallas_wei_workbook(source.get("series"), body)
    except DallasWeiDataError as exc:
        raise SourceUnavailable("Dallas WEI workbook contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["observation_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_asof_date": observation["provider_asof_date"],
            "provider_vintage_kind": observation["column_kind"],
            "strict_publisher_first_release_proven": False,
        })
        records.append(record)
    return records


def parse_philadelphia_ads_xlsx(source, body, retrieved_at):
    """Normalize the Philadelphia Fed ADS Business Conditions Index workbook.

    B-UNBLOCK-3 item 1. COMPARATOR lane, never a channel member (§10, §22.4).
    Only the ADS_Index column lands; the RECBARS NBER recession-shading column is
    an external recession LABEL and is dropped by the parser. The single
    current-vintage column lands as one flat offline-current EVIDENCE series
    under ``current_revised`` (there is no as-of / real-time claim on this lane).
    """
    try:
        observations = parse_philadelphia_ads_workbook(source.get("series"), body)
    except PhiladelphiaAdsDataError as exc:
        raise SourceUnavailable("ADS workbook contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["observation_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record["label"] = observation["label"]
        records.append(record)
    return records


def parse_forecast_xlsx(source, body, retrieved_at):
    """Normalize one Philadelphia Fed SPF / Anxious Index xlsx (B-LAND-8).

    FORECAST class. openpyxl is unblocked by an IN-MEMORY docProps/core.xml repair
    (CH-R49 defect); the offline-current binder stores the ORIGINAL cache bytes, so
    the bound bytes still match the cache-manifest sha. Each aggregate value column
    lands as its own SPF_<VARCODE>_<MEAN|MEDIAN> series keyed by survey quarter; the
    Anxious Index lands under its own id keyed by target quarter. #N/A aggregate
    cells emit value=None / value_status=unavailable. Firewall: probabilities are
    GDP-decline probabilities, never NBER recession-label products.
    """
    try:
        observations = parse_forecast_xlsx_bytes(source.get("series"), body)
    except ForecastXlsxDataError as exc:
        raise SourceUnavailable("SPF/Anxious xlsx contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["observation_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "provider_vintage_kind": "forecast_named_vintage",
            "strict_publisher_first_release_proven": False,
        })
        # Each forecast shape carries its own additive dimension keys; copy
        # through only the ones the observation actually declares so an spf
        # varcode never leaks onto a nyfed record and vice versa.
        for dimension in ("spf_target_code", "nyfed_reference_quarter",
                          "nyfed_horizon", "spf_forecaster_id", "spf_industry",
                          "spf_horizon"):
            if dimension in observation:
                record[dimension] = observation[dimension]
        if observation["value_status"] == "unavailable":
            record["value_status"] = "unavailable"
        records.append(record)
    return records


def parse_atsix_termstructure_xlsx(source, body, retrieved_at):
    """Normalize the Philadelphia Fed ATSIX (Aruoba Term Structure of Inflation
    Expectations) workbook's InfExp sheet into a FORECAST-COMPARATOR lane
    (B-ACQ-REALTIME-EXPECTATIONS item 4; owner ruling 20260806T162209Z Option 1).

    ATSIX is a Nelson-Siegel MODEL OUTPUT: one expected-inflation value per
    (reference month x horizon), with NO vintage-date axis (CH-R39 "forecast-class,
    not real-time realized data"; sheet measurement research/_bland12_sheets.json).
    It therefore joins the SPF / GDPNow / Livingston ``forecast_comparator``
    firewall and is NEVER an instrumentable construction input (moving it in is
    owner-only Option 2, not exercised). Only the owner-specified horizons in
    ``source["series"]["members"]`` (infexp12/24/60/120) land; the ``Real`` and
    ``Factors`` sheets are model-internal and are present-but-not-landed (catalog
    note). Information-set mode ``substituted_diagnostic`` (single latest snapshot);
    the temporal boundary (model production date vs reference row date) is
    UNRESOLVED offline and is stated in the catalog note, not assumed. Each record
    carries ``forecast_horizon`` (months) and ``forecast_origin`` (the reference
    month). Values copy the published cell text verbatim (no re-derivation).
    """
    series = source.get("series") or {}
    members = series.get("members") or []
    by_column = {}
    for member in members:
        by_column[member["horizon_column"]] = member
    try:
        rows, _sha, _meta = parse_atsix_sheet(body, "InfExp")
    except AtsixShapeError as exc:
        raise SourceUnavailable("ATSIX InfExp contract failed: %s" % exc)
    unit = series.get("unit")
    records = []
    for row in rows:
        member = by_column.get(row["series"])
        if member is None:
            continue
        # ATSIX ``_date_`` canonicalises to first-of-month; the reference MONTH is
        # both the observation period and the forecast origin (expectation formed
        # at that month over the next ``horizon_months``).
        period = row["date"][:7]
        record = _base_record(
            source,
            member["series_id"],
            period,
            row["value"],
            unit,
            retrieved_at,
        )
        record.update({
            "label": member.get("label"),
            "forecast_horizon": member["horizon_months"],
            "forecast_origin": period,
            "provider_vintage_kind": "atsix_model_expectation",
            "strict_publisher_first_release_proven": False,
        })
        records.append(record)
    if not records:
        raise SourceUnavailable(
            "ATSIX InfExp yielded no records for the configured horizons"
        )
    return records


def parse_greenbook_row_xlsx(source, body, retrieved_at):
    """Normalize one half of the Phil Fed Greenbook Row Format workbook (B-ACQ-GREENBOOK).

    ``source["series"]["half"]`` selects ``hist`` (GB_<VAR>_HIST, real-time historical
    values, archive_snapshot_asof) or ``proj`` (GB_<VAR>_PROJ, staff projections,
    substituted_diagnostic). The two halves are NEVER mixed in one series (§3.1/§3.6).
    Each record carries the ``greenbook_vintage`` publication date; PROJ records also
    carry ``forecast_origin`` + ``forecast_horizon``. ``#N/A`` cells emit
    value=None / value_status='unavailable'. Nothing here classifies against members.
    """
    try:
        observations = parse_greenbook_row_workbook(source.get("series"), body)
    except GreenbookRowDataError as exc:
        raise SourceUnavailable("Greenbook Row Format contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["observation_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "greenbook_vintage": observation["greenbook_vintage"],
            "variable_code": observation["variable_code"],
            "provider_vintage_kind": (
                "greenbook_realtime_historical"
                if source["series"]["half"] == "hist" else "greenbook_projection"
            ),
            "strict_publisher_first_release_proven": False,
        })
        if "forecast_horizon" in observation:
            record["forecast_horizon"] = observation["forecast_horizon"]
            record["forecast_origin"] = observation["forecast_origin"]
        if observation["value_status"] == "unavailable":
            record["value_status"] = "unavailable"
        records.append(record)
    return records


def parse_forecast_sep_pdf(source, body, retrieved_at):
    """Normalize one FOMC SEP compilation PDF's projection Table 1 (B-REG-FORECAST-PDFS-R2).

    ``source["series"]["meeting_date"]`` is the meeting-end (knowledge) publication date;
    it is encoded into every series id (SEP.<YYYYMMDD>.<VAR>.<STAT>.<BOUND>) and carried in
    ``forecast_origin`` + the label, so the row is self-dating. MODE substituted_diagnostic:
    external forecast comparator, family fomc_sep, NEVER a member and never fitted (CLAUDE.md
    forecast firewall). Parse is ALL-OR-NOTHING behind the strict anti-fabrication validators
    in forecast_sep_pdf.parse_sep_compilation; a document that fails yields no records and is
    a recorded failure upstream, never a silent skip.
    """
    from . import forecast_sep_pdf as sep_mod
    meeting_date = source["series"]["meeting_date"]
    res = sep_mod.parse_sep_compilation(body, meeting_date)
    if not res["ok"]:
        raise SourceUnavailable(
            "FOMC SEP Table 1 parse failed (%s): %s" % (meeting_date, res["reason"]))
    records = []
    for sid, yr, stat, bound, val, var, unit in sep_mod.sep_records(
            meeting_date, res["cells"]):
        record = _base_record(source, sid, str(yr), val, unit, retrieved_at)
        record.update({
            "forecast_origin": meeting_date,
            "forecast_horizon": str(yr),
            "label": ("FOMC SEP %s projection: %s %s %s for %s [participant views, "
                      "not staff or official forecast; substituted_diagnostic comparator, "
                      "family fomc_sep; B-REG-FORECAST-PDFS-R2]"
                      % (meeting_date, var, stat, bound, yr)),
            "provider_vintage_kind": "fomc_sep_projection",
            "sep_variable": var,
            "sep_statistic": stat,
            "sep_bound": bound,
            "strict_publisher_first_release_proven": False,
        })
        records.append(record)
    return records


def parse_nber_macrohistory_dat(source, body, retrieved_at):
    """Normalize one NBER Macrohistory fixed-layout .dat series (B-OFFLINE-4).

    Each series lands under its OWN NBER_* id, NEVER aliased to a modern twin,
    class RESEARCH/NEAR, validation-scope only (owner ruling carried by the
    batch). Missing cells are emitted as value=None / value_status=unavailable so
    the record count equals the file's row count (FRED current-lane convention);
    the annual-summary blank-period row (m03030) is preserved at annual
    granularity. Values are copied verbatim as the shortest round-tripping
    decimal — never merged, spliced, or re-based.
    """
    try:
        observations = parse_nber_macrohistory_dat_bytes(source.get("series"), body)
    except NberMacrohistoryDataError as exc:
        raise SourceUnavailable("NBER Macrohistory .dat contract failed: %s" % exc)
    records = []
    for observation in observations:
        record = _base_record(
            source,
            observation["series_id"],
            observation["observation_period"],
            observation["value"],
            observation["unit"],
            retrieved_at,
        )
        record.update({
            "label": observation["label"],
            "nber_file_period": observation["nber_file_period"],
            "period_granularity": observation["period_granularity"],
            "provider_vintage_kind": "never_revised",
            "strict_publisher_first_release_proven": False,
        })
        if observation["value_status"] == "unavailable":
            record["value_status"] = "unavailable"
        records.append(record)
    return records


def parse_treasury_dts_operating_cash(source, body, retrieved_at):
    """Normalize the merged Treasury DTS Table-I "Operating Cash Balance" body.

    B-OFFLINE-3-R2 item 2, per director ruling 20260806T084233Z (A=Option 2 single
    manifest, B=Option 1 ten clean literal series, SPLICE NOTHING). ``body`` is the
    ONE canonical merged body produced by ``merge_operating_cash_pages`` and
    serialized by ``serialize_merged_body`` (16,498 rows, all table_nbr='I'); the
    offline binder stored exactly those bytes, so re-parsing them here is
    byte-faithful.

    Each of the 10 declared clean ``account_type`` strings lands as its OWN literal
    series. No aliasing, no splice across the 2021/2022 Federal Reserve Account ->
    TGA rename or the structural split (owner territory). The 6 truncation / field-
    shift variants are simply NOT in the member map, so they are not emitted; they
    are enumerated in the committed provenance sidecar, not merged into a sibling.

    The value column is declared PER MEMBER (``value_field``): the post-2022 "Cash
    Balance Details" lines report their figure in ``open_today_bal`` with
    ``close_today_bal`` literally "null", while the legacy "Type of account" lines
    report it in ``close_today_bal``. This is a per-line measurement, disclosed in
    each member label, never a cross-line identity claim. A "null" / missing value
    emits value=None / value_status=unavailable so the landed record count equals
    the sum of the 10 lines' row counts.
    """
    try:
        merged = json.loads(body)
    except ValueError as exc:
        raise SourceUnavailable("DTS merged body was not valid JSON: %s" % exc)
    if not isinstance(merged, dict):
        raise SourceUnavailable("DTS merged body was not a JSON object")
    if merged.get("schema_version") != TREASURY_DTS_OC_MERGE_SCHEMA:
        raise SourceUnavailable(
            "DTS merged body schema_version %r != %r"
            % (merged.get("schema_version"), TREASURY_DTS_OC_MERGE_SCHEMA)
        )
    if (merged.get("table_nbr") != TREASURY_DTS_OC_TABLE_NBR or
            merged.get("table_nm") != TREASURY_DTS_OC_TABLE_NM):
        raise SourceUnavailable(
            "DTS merged body is not Table I 'Operating Cash Balance'"
        )
    rows = merged.get("data")
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("DTS merged body lacked a non-empty data array")

    series = source.get("series") or {}
    unit = series.get("unit")
    by_account = {}
    for member in series.get("members", []):
        account_type = member["account_type"]
        if account_type in by_account:
            raise SourceUnavailable(
                "DTS member map declares account_type %r twice" % account_type
            )
        by_account[account_type] = member

    records = []
    for row in rows:
        member = by_account.get(row.get("account_type"))
        if member is None:
            # A truncation / field-shift variant or non-clean line: not landed.
            continue
        _enforce_dts_value_column(row, member)
        raw = row.get(member["value_field"])
        if raw is None or str(raw).strip() in ("", "null"):
            value = None
            value_status = "unavailable"
        else:
            value = _shortest_round_trip_decimal(raw)
            value_status = source["value_status"]
        record = _base_record(
            source,
            member["series_id"],
            row["record_date"],
            value,
            unit,
            retrieved_at,
        )
        record.update({
            "label": member["label"],
            "dts_account_type": row["account_type"],
            "dts_value_field": member["value_field"],
            "dts_src_line_nbr": row.get("src_line_nbr"),
            "dts_sub_table_name": row.get("sub_table_name"),
            "provider_vintage_kind": "never_revised",
            "strict_publisher_first_release_proven": False,
        })
        if value_status == "unavailable":
            record["value_status"] = "unavailable"
        records.append(record)
    return records


# The 2022-04-18 DTS restructure moved each TGA line's figure out of
# close_today_bal (left literally "null") and into open_today_bal. The value
# column is a fixed function of sub_table_name; the adapter enforces it so a future
# restructure BREAKS loudly instead of silently landing empty or wrong-column data
# (director ruling 20260806T153123Z, binding condition 2). This is a feed-structure
# rule, distinct from the still-open Federal Reserve Account -> TGA account-identity
# question.
_DTS_SUBTABLE_VALUE_FIELD = {
    "Type of account": "close_today_bal",
    "Cash Balance Details": "open_today_bal",
}
# The column that MUST stay null for a given sub_table; a populated value there is
# the restructure signal that must fail rather than be silently taken.
_DTS_SUBTABLE_EXPECTED_NULL = {
    "Cash Balance Details": "close_today_bal",
}


def _enforce_dts_value_column(row, member):
    """Fail loudly if the DTS feed's value-column layout no longer matches the rule.

    Ties ``member["value_field"]`` to the row's ``sub_table_name`` by the fixed
    2022-restructure rule, and rejects a row whose expected-null column is
    populated (the restructure detector required by the ruling). Any violation is a
    hard contract failure that aborts the whole normalize, so an unnoticed feed
    change cannot land silently.
    """
    sub_table = row.get("sub_table_name")
    expected_field = _DTS_SUBTABLE_VALUE_FIELD.get(sub_table)
    if expected_field is None:
        raise SourceUnavailable(
            "DTS row for %r has unrecognized sub_table_name %r (feed restructure?)"
            % (row.get("account_type"), sub_table)
        )
    if member["value_field"] != expected_field:
        raise SourceUnavailable(
            "DTS member %r declares value_field %r but sub_table_name %r requires "
            "%r (column-selection rule violated)"
            % (member.get("series_id"), member["value_field"], sub_table,
               expected_field)
        )
    null_field = _DTS_SUBTABLE_EXPECTED_NULL.get(sub_table)
    if null_field is not None:
        off = row.get(null_field)
        if not (off is None or str(off).strip() in ("", "null")):
            raise SourceUnavailable(
                "DTS %r row on %s has a populated %s=%r that the rule expects null "
                "-- feed restructured; refusing to silently take the wrong column"
                % (row.get("account_type"), row.get("record_date"), null_field, off)
            )


def _shortest_round_trip_decimal(raw):
    """Return the DTS millions figure verbatim, never re-scaled or rounded.

    DTS operating-cash figures are integer-millions strings (some negative). Parse
    as int when integral, else as float, so the stored value round-trips the feed.
    """
    text = str(raw).strip()
    try:
        return int(text)
    except ValueError:
        return float(text)


def _geo_panel_period(offset, freq, index):
    """Dense reference period `index` steps after `offset`, ISO period-start.

    freq 'm' offset 'YYYY-MM' -> 'YYYY-MM-01'; freq 'q' offset 'YYYY-QN' ->
    quarter-start 'YYYY-{01,04,07,10}-01'; freq 'a' offset year -> 'YYYY-01-01'.
    """
    if freq == "a":
        return "%04d-01-01" % (int(str(offset).strip()) + int(index))
    if freq == "m":
        year_s, month_s = str(offset).strip().split("-")
        base = (int(year_s) * 12 + (int(month_s) - 1)) + int(index)
        return "%04d-%02d-01" % (base // 12, base % 12 + 1)
    if freq == "q":
        year_s, quarter_s = str(offset).strip().upper().split("-Q")
        base = (int(year_s) * 4 + (int(quarter_s) - 1)) + int(index)
        return "%04d-%02d-01" % (base // 4, (base % 4) * 3 + 1)
    raise CanonicalDataError("geo_panel: unknown frequency %r" % freq)


def parse_geo_panel_json(source, body, retrieved_at):
    """Generic offline geo cross-section parser (B-REG-GEO, ONE new shape §6.1).

    Shape (CH-R101 measurement of record): a top-level ``container`` maps each
    explicit geo unit id (USPS / FIPS / CBSA) to a map of metric -> a dense
    ``{<offset_key>, "v": [...]}`` block. ``offset_key`` is ``m0``/``q0``/``y0``
    and fixes the frequency. Emits one record per non-null observation as series
    ``<id_prefix>.<unit>.<metric>``. Numbers are decoded verbatim as strings
    (``parse_int``/``parse_float`` = str) so decimal bytes survive (B-FIX-1).
    Scalar (non-block) unit fields listed in ``skip_scalar_keys`` are ignored.
    """
    spec = source["series"]
    container_key = spec["container_key"]
    id_prefix = spec["id_prefix"]
    metrics = spec["metrics"]
    skip = set(spec.get("skip_scalar_keys", []))
    data = json.loads(body, parse_int=str, parse_float=str)
    container = data.get(container_key)
    if not isinstance(container, dict):
        raise CanonicalDataError(
            "geo_panel: container %r absent for %s"
            % (container_key, source["source_id"])
        )
    records = []
    for unit in sorted(container):
        umap = container[unit]
        if not isinstance(umap, dict):
            continue
        for metric, mspec in metrics.items():
            block = umap.get(metric)
            if block is None or metric in skip:
                continue
            if not isinstance(block, dict):
                continue
            offset_key = mspec["offset_key"]
            freq = mspec["freq"]
            unit_label = mspec["unit"]
            offset = block.get(offset_key)
            values = block.get("v")
            if offset is None or not isinstance(values, list):
                continue
            series_id = "%s.%s.%s" % (id_prefix, unit, metric)
            for index, value in enumerate(values):
                if value is None or value == "":
                    continue
                period = _geo_panel_period(offset, freq, index)
                record = _base_record(
                    source, series_id, period, str(value), unit_label,
                    retrieved_at,
                )
                records.append(record)
    return records


def _geo_axis_period(label):
    """ISO period-start for an EXPLICIT axis label.

    int / 4-digit year -> 'YYYY-01-01'; 'YYYY-MM' -> 'YYYY-MM-01';
    'YYYY-QN' -> quarter-start 'YYYY-{01,04,07,10}-01'.
    """
    text = str(label).strip().upper()
    if "-Q" in text:
        year_s, quarter_s = text.split("-Q")
        return "%04d-%02d-01" % (int(year_s), (int(quarter_s) - 1) * 3 + 1)
    if "-" in text:
        year_s, month_s = text.split("-")[:2]
        return "%04d-%02d-01" % (int(year_s), int(month_s))
    return "%04d-01-01" % int(text)


def parse_geo_grid_json(source, body, retrieved_at):
    """Generic offline geo cross-section parser for the EXPLICIT-AXIS shape
    (B-REG-GEO, ONE new shape §6.1; distinct from geo_panel_json's offset+values).

    Each ``block`` carries ``axis_key`` (a top-level list of period labels) and a
    ``container_key`` mapping each explicit geo unit id to aligned value lists,
    zipped positionally with the axis (overlap only on length mismatch). With
    ``metric_level`` the unit maps metric -> values (``metrics[code].unit`` names
    each), and series are ``<id_prefix>.<unit>.<code>``; without it the unit maps
    directly to values under ``metric_suffix``/``unit``, series
    ``<id_prefix>.<unit>.<metric_suffix>``. Numbers decoded verbatim as strings
    (B-FIX-1); null / empty holes are dropped.
    """
    spec = source["series"]
    id_prefix = spec["id_prefix"]
    blocks = spec["blocks"]
    data = json.loads(body, parse_int=str, parse_float=str)
    records = []
    for block in blocks:
        axis = data.get(block["axis_key"])
        container = data.get(block["container_key"])
        if not isinstance(axis, list) or not isinstance(container, dict):
            continue
        periods = [_geo_axis_period(label) for label in axis]
        metric_level = bool(block.get("metric_level"))
        for unit in sorted(container):
            umap = container[unit]
            if metric_level:
                if not isinstance(umap, dict):
                    continue
                pairs = [
                    (code, mspec["unit"], umap.get(code))
                    for code, mspec in block["metrics"].items()
                ]
            else:
                pairs = [
                    (block["metric_suffix"], block["unit"], umap),
                ]
            for code, unit_label, values in pairs:
                if not isinstance(values, list):
                    continue
                series_id = "%s.%s.%s" % (id_prefix, unit, code)
                for period, value in zip(periods, values):
                    if value is None or value == "":
                        continue
                    records.append(_base_record(
                        source, series_id, period, str(value), unit_label,
                        retrieved_at,
                    ))
    return records


def parse_dbnomics_json(source, body, retrieved_at):
    """DBnomics aggregator series JSON (Web API v22, one series doc per body).

    Aggregator tier (§3.1): the aggregator's copy is NOT the publisher's series
    until proven identical, and the lineage back to the original publisher must
    survive verbatim. Each record therefore carries the provider/dataset/series
    triple. §5.6: the aggregator's own doc identity is a CROSS-CHECK on the
    configured identity -- a mismatch REFUSES rather than silently relabels.
    """
    payload = strict_publisher_json_loads(body)
    if payload.get("errors"):
        raise SourceUnavailable("DBnomics response carried errors")
    series = payload.get("series")
    docs = series.get("docs") if isinstance(series, dict) else None
    if not isinstance(docs, list) or len(docs) != 1:
        raise SourceUnavailable("DBnomics payload must carry exactly one series doc")
    doc = docs[0]
    members = source["series"]["members"]
    if len(members) != 1:
        raise SourceUnavailable("dbnomics_json source must configure exactly one member")
    member = members[0]
    for field in ("provider_code", "dataset_code", "series_code"):
        if str(doc.get(field)) != str(member[field]):
            raise SourceUnavailable(
                "DBnomics %s mismatch: doc %r != configured %r"
                % (field, doc.get(field), member[field]))
    periods = doc.get("period")
    values = doc.get("value")
    if (not isinstance(periods, list) or not isinstance(values, list) or
            len(periods) != len(values)):
        raise SourceUnavailable("DBnomics period/value arrays malformed")
    ref = "%s/%s/%s" % (member["provider_code"], member["dataset_code"],
                        member["series_code"])
    unit = source["series"]["unit"]
    upstream = member.get("upstream_publisher", "")
    records = []
    for period, value in zip(periods, values):
        if value is None:
            continue  # DBnomics missing observation -> absence, not a hole
        if isinstance(value, str) and value.strip().upper() in ("", "NA", "NAN"):
            continue
        record = _base_record(
            source, member["series_id"], period, str(value), unit, retrieved_at)
        record["provider_vintage_kind"] = "dbnomics_aggregator_mirror"
        record["aggregator_provider"] = "DBnomics"
        record["dbnomics_series_ref"] = ref
        record["upstream_publisher"] = upstream
        records.append(record)
    if not records:
        raise SourceUnavailable("DBnomics series carried no observations")
    return records


def normalize(source, body, retrieved_at):
    adapter = source["adapter"]
    if adapter == "dbnomics_json":
        return parse_dbnomics_json(source, body, retrieved_at)
    if adapter == "geo_panel_json":
        return parse_geo_panel_json(source, body, retrieved_at)
    if adapter == "geo_grid_json":
        return parse_geo_grid_json(source, body, retrieved_at)
    if adapter == "dallas_wei_xlsx":
        return parse_dallas_wei_xlsx(source, body, retrieved_at)
    if adapter == "philadelphia_ads_xlsx":
        return parse_philadelphia_ads_xlsx(source, body, retrieved_at)
    if adapter == "treasury_dts_operating_cash":
        return parse_treasury_dts_operating_cash(source, body, retrieved_at)
    if adapter == "nber_macrohistory_dat":
        return parse_nber_macrohistory_dat(source, body, retrieved_at)
    if adapter == "forecast_sep_pdf":
        return parse_forecast_sep_pdf(source, body, retrieved_at)
    if adapter == "forecast_xlsx":
        return parse_forecast_xlsx(source, body, retrieved_at)
    if adapter == "atsix_termstructure_xlsx":
        return parse_atsix_termstructure_xlsx(source, body, retrieved_at)
    if adapter == "greenbook_row_xlsx":
        return parse_greenbook_row_xlsx(source, body, retrieved_at)
    if adapter == "treasury_yield_xml":
        return parse_treasury_yield_xml(source, body, retrieved_at)
    if adapter == "nyfed_reference_rate_json":
        return parse_nyfed_reference_rate_json(source, body, retrieved_at)
    if adapter == "bls_json":
        return parse_bls_json(source, body, retrieved_at)
    if adapter == "dol_eta539_csv":
        return parse_dol_eta539_csv(source, body, retrieved_at)
    if adapter == "fred_graph_csv":
        return parse_fred_graph_csv(source, body, retrieved_at)
    if adapter == "fred_json_api":
        return parse_fred_json_api(source, body, retrieved_at)
    if adapter == "fred_json_api_vintages":
        return parse_fred_json_api_vintages(source, body, retrieved_at)
    if adapter == "fred_json_api_vintages_deep":
        return parse_fred_json_api_vintages_deep(source, body, retrieved_at)
    if adapter == "census_api":
        return parse_census_eits(source, body, retrieved_at)
    if adapter == "bea_api":
        return parse_bea_api(source, body, retrieved_at)
    if adapter == "eia_v2_json":
        return parse_eia_v2_json(source, body, retrieved_at)
    if adapter == "dol_ui_weekly_claims_report_html":
        return parse_dol_ui_weekly_claims_report_html(source, body, retrieved_at)
    if adapter == "tabular_csv":
        return parse_tabular_csv(source, body, retrieved_at)
    if adapter == "regional_survey_xlsx":
        return parse_regional_survey_xlsx(source, body, retrieved_at)
    if adapter == "fed_ddp_csv":
        return parse_fed_ddp_csv(source, body, retrieved_at)
    if adapter == "census_btos_xlsx":
        return parse_census_btos_xlsx(source, body, retrieved_at)
    if adapter == "census_qss_timeseries_zip":
        return parse_census_qss_zip(source, body, retrieved_at)
    if adapter == "openfema_disaster_declarations_json":
        return parse_fema_disaster_declarations_json(
            source,
            body,
            retrieved_at,
        )
    if adapter == "cfpb_credit_trends_csv":
        return parse_cfpb_credit_trends_csv(source, body, retrieved_at)
    if adapter == "cfpb_mortgage_performance_state_csv":
        return parse_cfpb_mortgage_performance_state_csv(
            source,
            body,
            retrieved_at,
        )
    if adapter == "cleveland_nowcast_json":
        return parse_cleveland_nowcast_json(source, body, retrieved_at)
    if adapter == "socrata_json":
        return parse_socrata_json(source, body, retrieved_at)
    if adapter == "fiscaldata_json":
        return parse_fiscaldata_json(source, body, retrieved_at)
    if adapter == "treasury_mts_totals_json":
        return parse_treasury_mts_totals_json(source, body, retrieved_at)
    if adapter == "fhfa_hpi_csv":
        return parse_fhfa_hpi_csv(source, body, retrieved_at)
    if adapter == "fhfa_hpi_at_geo_csv":
        return parse_fhfa_hpi_at_geo_csv(source, body, retrieved_at)
    if adapter == "bea_regional_cainc_zip":
        return parse_bea_regional_cainc_zip(source, body, retrieved_at)
    if adapter == "ofr_fsi_csv":
        return parse_ofr_fsi_csv(source, body, retrieved_at)
    if adapter == "fdic_aggregate_json":
        return parse_fdic_aggregate_json(source, body, retrieved_at)
    if adapter == "tsa_passenger_html":
        return parse_tsa_passenger_html(source, body, retrieved_at)
    if adapter == "treasury_dts_json":
        return parse_treasury_dts_json(source, body, retrieved_at)
    if adapter == "raw_capture":
        return parse_raw_capture(source, body, retrieved_at)
    raise CanonicalDataError("no normalizer for adapter %s" % adapter)
