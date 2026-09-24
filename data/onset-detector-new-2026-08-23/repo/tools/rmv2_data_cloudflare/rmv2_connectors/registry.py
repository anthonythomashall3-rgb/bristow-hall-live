"""Legacy-to-canonical connector registry.

Each spec records the explicit legacy->canonical identity transition proven on
2026-08-01. Credentials are NEVER stored here: FRED/BLS URLs carry a
``{key}`` placeholder the engine fills from the environment at fetch time and
strips from every emitted candidate.

A466RX1Q020SBEA is deliberately ABSENT: its exact identity could not be proven
against official BEA/FRED sources, so per instruction it stays unresolved rather
than being substituted.
"""
from __future__ import annotations

import dataclasses
from typing import List, Sequence


@dataclasses.dataclass(frozen=True)
class ConnectorSpec:
    connector_id: str
    legacy_id: str
    canonical_id: str
    originating_publisher: str
    survey: str
    provider_code: str
    publisher_kind: str            # parser dispatch key
    url_template: str              # may contain {key}
    allowed_hosts: Sequence[str]
    expected_content_types: Sequence[str]
    title: str
    units: str
    frequency: str
    seasonal_adjustment: str
    rights_status: str
    publisher_release_clock: str
    information_set_mode: str
    identity_confidence: str
    identity_evidence: Sequence[str]
    raw_destination: str
    credential_env: str = ""       # env var to substitute into {key}, if any
    history_start_year: int = 0    # BLS: first year to acquire (enables windowed full-history fetch)


CONNECTORS: List[ConnectorSpec] = [
    ConnectorSpec(
        connector_id="oecd_cli_nor_usa",
        legacy_id="USALOLITONOSTSAMEI",
        canonical_id="USA_OECD_CLI_NOR",
        originating_publisher="OECD (SDD, Short-Term Economic Statistics)",
        survey="OECD Composite Leading Indicators",
        provider_code="OECD.SDD.STES,DSD_STES@DF_CLI,4.1/USA.M.LI.IX._Z.NOR.IX._Z.H",
        publisher_kind="oecd_sdmx_json",
        url_template=("https://sdmx.oecd.org/public/rest/data/"
                      "OECD.SDD.STES,DSD_STES@DF_CLI,4.1/USA.M.LI.IX._Z.NOR.IX._Z.H"),
        allowed_hosts=["sdmx.oecd.org"],
        expected_content_types=["application/vnd.sdmx.data+json", "application/json"],
        title="Composite Leading Indicator (CLI), Normalised, United States",
        units="index", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="oecd_terms_review_pending_confirmation",
        publisher_release_clock="OECD CLI released about mid-month for the prior reference month; confirm exact calendar",
        information_set_mode="current_revised",
        identity_confidence="exact_official_remap",
        identity_evidence=[
            "Legacy FRED id token 'NO' = Normalised (FRED legacy title 'CLI: Normalised for the United States').",
            "OECD DF_CLI 4.1 enumerated US-monthly series; adjustment=NOR selected per instruction (not AA).",
            "Dimension key derived deterministically from the DSD, not guessed.",
        ],
        raw_destination="raw/oecd/USA_OECD_CLI_NOR.sdmx.json",
    ),
    ConnectorSpec(
        connector_id="bls_uemplt5",
        legacy_id="LNS13008396",
        canonical_id="UEMPLT5",
        originating_publisher="U.S. Bureau of Labor Statistics",
        survey="Current Population Survey",
        provider_code="LNS13008396",
        publisher_kind="bls_v2_json",
        url_template="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        history_start_year=1948,
        allowed_hosts=["api.bls.gov"],
        expected_content_types=["application/json"],
        title="Number Unemployed for Less Than 5 Weeks",
        units="thousands_of_persons", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="BLS Employment Situation, monthly, ~first Friday 08:30 America/New_York",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_value_verified",
        identity_evidence=[
            "BLS API returned LNS13008396 2025-M12 = 2289, equal to FRED canonical UEMPLT5 (value parity).",
            "Originating publisher BLS/CPS; canonical display id UEMPLT5.",
        ],
        raw_destination="raw/bls/UEMPLT5.json",
    ),
    ConnectorSpec(
        connector_id="bls_ahetpi",
        legacy_id="CES0500000008",
        canonical_id="AHETPI",
        originating_publisher="U.S. Bureau of Labor Statistics",
        survey="Current Employment Statistics",
        provider_code="CES0500000008",
        publisher_kind="bls_v2_json",
        url_template="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        history_start_year=1964,
        allowed_hosts=["api.bls.gov"],
        expected_content_types=["application/json"],
        title="Average Hourly Earnings of Production and Nonsupervisory Employees, Total Private",
        units="dollars_per_hour", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="BLS Employment Situation, monthly, ~first Friday 08:30 America/New_York",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_value_verified",
        identity_evidence=[
            "BLS API returned CES0500000008 2025-M12 = 31.83, equal to FRED canonical AHETPI (value parity).",
            "CES data-type 08 = production & nonsupervisory; originating publisher BLS/CES.",
        ],
        raw_destination="raw/bls/AHETPI.json",
    ),
    ConnectorSpec(
        connector_id="bls_ce16ov",
        legacy_id="LNS12000000",
        canonical_id="CE16OV",
        originating_publisher="U.S. Bureau of Labor Statistics",
        survey="Current Population Survey",
        provider_code="LNS12000000",
        publisher_kind="bls_v2_json",
        url_template="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        history_start_year=1948,
        allowed_hosts=["api.bls.gov"],
        expected_content_types=["application/json"],
        title="Employment Level",
        units="thousands_of_persons", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="BLS Employment Situation, monthly, ~first Friday 08:30 America/New_York",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_high_confidence",
        identity_evidence=[
            "Legacy LNS12000000 is the BLS/CPS Civilian Employment Level code; canonical FRED display id CE16OV.",
            "FRED CE16OV verified: monthly, 1948-01.., 'Employment Level', thousands of persons, SA.",
        ],
        raw_destination="raw/bls/CE16OV.json",
    ),
    ConnectorSpec(
        connector_id="fred_cprofit",
        legacy_id="CORPPROFIT",
        canonical_id="CPROFIT",
        originating_publisher="U.S. Bureau of Economic Analysis (via FRED official API)",
        survey="NIPA (Corporate Profits)",
        provider_code="CPROFIT",
        publisher_kind="fred_api_json",
        url_template=("https://api.stlouisfed.org/fred/series/observations?series_id=CPROFIT"
                      "&api_key={key}&file_type=json"),
        allowed_hosts=["api.stlouisfed.org"],
        expected_content_types=["application/json"],
        title="Corporate Profits with Inventory Valuation Adjustment (IVA) and Capital Consumption Adjustment (CCAdj)",
        units="billions_of_dollars", frequency="quarterly", seasonal_adjustment="seasonally_adjusted_annual_rate",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="BEA NIPA quarterly GDP releases; FRED mirrors on publication",
        information_set_mode="current_revised",
        identity_confidence="mnemonic_derived_leading_candidate",
        identity_evidence=[
            "Legacy bytes were html_masquerading_as_csv (no held values); only the mnemonic 'CORPPROFIT' survives.",
            "Mnemonic supports the general corporate-profits-with-adjustments concept; no legacy evidence says 'after tax'.",
            "Per instruction: CPROFIT (with IVA & CCAdj), NOT the narrower after-tax CP. BEA-native SeriesCode resolution deferred.",
        ],
        raw_destination="raw/fred/CPROFIT.json",
        credential_env="FRED_API_KEY",
    ),
    ConnectorSpec(
        connector_id="fred_lautosa",
        legacy_id="AUTOSTOTALSA",
        canonical_id="LAUTOSA",
        originating_publisher="U.S. Bureau of Economic Analysis (via FRED official API)",
        survey="Motor Vehicle Retail Sales",
        provider_code="LAUTOSA",
        publisher_kind="fred_api_json",
        url_template=("https://api.stlouisfed.org/fred/series/observations?series_id=LAUTOSA"
                      "&api_key={key}&file_type=json"),
        allowed_hosts=["api.stlouisfed.org"],
        expected_content_types=["application/json"],
        title="Motor Vehicle Retail Sales: Domestic and Foreign Autos",
        units="millions_of_units", frequency="monthly", seasonal_adjustment="seasonally_adjusted_annual_rate",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="BEA motor vehicle sales, monthly; FRED mirrors on publication",
        information_set_mode="current_revised",
        identity_confidence="mnemonic_derived_leading_candidate",
        identity_evidence=[
            "Legacy bytes were html_masquerading_as_csv (no held values); only the mnemonic 'AUTOSTOTALSA' survives.",
            "Mnemonic reads 'autos, total, SA' -> autos specifically (LAUTOSA), not all-vehicles (TOTALSA) or autos+light-trucks (ALTSALES).",
            "FRED LAUTOSA metadata verified: monthly, millions of units, SAAR, 'Domestic and Foreign Autos'.",
        ],
        raw_destination="raw/fred/LAUTOSA.json",
        credential_env="FRED_API_KEY",
    ),
    ConnectorSpec(
        connector_id="fred_ipg3361t3s",
        legacy_id="IPN3361T3S",
        canonical_id="IPG3361T3S",
        originating_publisher="Federal Reserve Board G.17 (via FRED official API)",
        survey="Industrial Production",
        provider_code="IPG3361T3S",
        publisher_kind="fred_api_json",
        url_template=("https://api.stlouisfed.org/fred/series/observations?series_id=IPG3361T3S"
                      "&api_key={key}&file_type=json"),
        allowed_hosts=["api.stlouisfed.org"],
        expected_content_types=["application/json"],
        title="Industrial Production: Manufacturing: Durable Goods: Motor Vehicles and Parts",
        units="index_2017_100", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="FRB G.17 monthly, mid-month for prior month",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_high_confidence",
        identity_evidence=[
            "Legacy IPN3361T3S is a G.17 IP identifier; the 'N'->'G' prefix is the current FRED series (IPG = index, SA).",
            "FRED IPG3361T3S verified: monthly, 1972-01.., 'IP: Manufacturing: Durable: Motor Vehicles and Parts'.",
        ],
        raw_destination="raw/fred/IPG3361T3S.json",
        credential_env="FRED_API_KEY",
    ),
    ConnectorSpec(
        connector_id="fred_cmrmtspl",
        legacy_id="CMRMTSPLM",
        canonical_id="CMRMTSPL",
        originating_publisher="U.S. Census Bureau / BEA (via FRED official API)",
        survey="Manufacturing and Trade Inventories and Sales",
        provider_code="CMRMTSPL",
        publisher_kind="fred_api_json",
        url_template=("https://api.stlouisfed.org/fred/series/observations?series_id=CMRMTSPL"
                      "&api_key={key}&file_type=json"),
        allowed_hosts=["api.stlouisfed.org"],
        expected_content_types=["application/json"],
        title="Real Manufacturing and Trade Industries Sales",
        units="millions_of_chained_2017_dollars", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="monthly, high-lag (~2 months)",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_donor_confirmed",
        identity_evidence=[
            "Predecessor DATA_REGISTRY: malformed monthly twin CMRMTSPLM; valid series is CMRMTSPL (used by index_v1).",
            "FRED CMRMTSPL verified: monthly, 1967-01.., 'Real Manufacturing and Trade Industries Sales'.",
        ],
        raw_destination="raw/fred/CMRMTSPL.json",
        credential_env="FRED_API_KEY",
    ),
    ConnectorSpec(
        connector_id="fred_gacdfsa066msfrbphi",
        legacy_id="GACDISA066MSFRBPHI",
        canonical_id="GACDFSA066MSFRBPHI",
        originating_publisher="Federal Reserve Bank of Philadelphia (via FRED official API)",
        survey="Manufacturing Business Outlook Survey",
        provider_code="GACDFSA066MSFRBPHI",
        publisher_kind="fred_api_json",
        url_template=("https://api.stlouisfed.org/fred/series/observations?series_id=GACDFSA066MSFRBPHI"
                      "&api_key={key}&file_type=json"),
        allowed_hosts=["api.stlouisfed.org"],
        expected_content_types=["application/json"],
        title="Current General Activity Diffusion Index for Federal Reserve District 3: Philadelphia",
        units="diffusion_index", frequency="monthly", seasonal_adjustment="seasonally_adjusted",
        rights_status="public_government_data_with_attribution",
        publisher_release_clock="FRB Philadelphia MBOS monthly",
        information_set_mode="current_revised",
        identity_confidence="exact_remap_id_trap_fixed",
        identity_evidence=[
            "Legacy GACDISA066MSFRBPHI and the dead alias PHIL both resolve to the working id GACDFSA066MSFRBPHI (single-letter I->F trap).",
            "FRED GACDFSA066MSFRBPHI verified: monthly, 1968-05.., 'Current General Activity; Diffusion Index'.",
            "Supersedes TWO legacy ids: GACDISA066MSFRBPHI and PHIL.",
        ],
        raw_destination="raw/fred/GACDFSA066MSFRBPHI.json",
        credential_env="FRED_API_KEY",
    ),
]

_BY_ID = {c.connector_id: c for c in CONNECTORS}


def get(connector_id: str) -> ConnectorSpec:
    return _BY_ID[connector_id]
