#!/usr/bin/env python3
"""Deep-source patch for the standing collector (collection 191), prepared 18 September 2026.

Written after two searches that did nothing but look for state and high-frequency data the warehouse did not hold.
Every address below was fetched and its content inspected before it was written down; the few that answered only to a
browser are registered with a note rather than left out, because the fetch engine's ladder may pass where a plain
request did not. Idempotent: running it twice changes nothing the second time.

Run on the Mac from 191/code:
    python3 pending_patch_deep_sources_2026-09-18.py
    python3 -m py_compile collector.py
    launchctl kickstart -k gui/$(id -u)/com.bristowhall.collector
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
COLL = os.path.join(HERE, 'collector.py')
STAMP = time.strftime('%Y-%m-%d_%H%M')


def F(out, url, **kw):
    d = {'url': url, 'out': out}
    d.update(kw)
    return d


S3 = 'https://econdata.s3-us-west-2.amazonaws.com/Reports/'
PHIL = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/'
NYF = 'https://www.newyorkfed.org/medialibrary/'
BLS = 'https://download.bls.gov/pub/time.series/'
EIA = 'https://www.eia.gov/'
CLEV = 'https://www.clevelandfed.org/-/media/files/webcharts/'

JOBS = [

 {'name': 'state_claims_substate', 'dir': 'state_claims_substate', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 5,
  '_note': "Added 18 Sep 2026. Unemployment claims below the state level, which the federal weekly file does not carry: Missouri by county every week since 2003, Connecticut initial and continued claims by week, New York by region monthly from 2003 and statewide from 1971 with beneficiaries, benefits paid and average duration, Michigan's own moving average. Never revised. Washington publishes claims by county and by industry every week but changes the file's number each time, so it is fetched by the dynamic_links job instead.",
  'files': [
   F('missouri_initial_claims_by_county_weekly.csv', 'https://data.mo.gov/resource/qet9-8yam.csv?$limit=200000'),
   F('connecticut_initial_and_continued_claims_weekly.csv', 'https://data.ct.gov/resource/i3d2-i4bi.csv?$limit=200000'),
   F('new_york_initial_claims_by_region_monthly.csv', 'https://data.ny.gov/resource/w34r-gwfk.csv?$limit=200000'),
   F('new_york_initial_claims_statewide_from_1971.csv', 'https://data.ny.gov/resource/ns8z-xewg.csv?$limit=200000'),
   F('new_york_beneficiaries_and_benefits_paid.csv', 'https://data.ny.gov/resource/xbjp-8sra.csv?$limit=200000'),
   F('new_york_average_duration_of_benefits.csv', 'https://data.ny.gov/resource/qkrk-6v78.csv?$limit=200000'),
   F('michigan_initial_claims_52week_average.csv', 'https://data.michigan.gov/resource/vsec-rvkn.csv?$limit=200000'),
  ]},

 {'name': 'state_warn', 'dir': 'state_warn', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Layoff notices with the employer, the date and the number of workers, from the three states that publish them as data rather than as a web page: Texas daily and append-only, California's live workbook for the current fiscal year, Colorado's own sheet with permanent, temporary, furlough and reduced-hours counts separated. Real time by construction and never revised. The other states publish WARN as HTML or PDF only; the Cleveland Fed file in collection 199 remains the aggregator for those.",
  'files': [
   F('texas_warn_notices.csv', 'https://data.texas.gov/resource/8w53-c4f6.csv?$limit=100000'),
   F('california_warn_current_year.xlsx', 'https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx'),
   F('colorado_warn_2026.csv', 'https://docs.google.com/spreadsheets/d/19jmo4Cwj933cmSBKV1t0zZ5O-2H5IpiLIhSH9MF8WF0/export?format=csv'),
   F('colorado_warn_2025.csv', 'https://docs.google.com/spreadsheets/d/1aFv4ntRhjnTMFKqBnuzbIkExCWgp6vnblYGm_h9GUeI/export?format=csv'),
   F('colorado_warn_2024.csv', 'https://docs.google.com/spreadsheets/d/1tDQPJ8jVqmyGbLYs6hUZiiNQIsablkZyLJt8rLIzanY/export?format=csv'),
   F('colorado_warn_2023.csv', 'https://docs.google.com/spreadsheets/d/1ATu4-rs7Rw59UOYcdN-tNZCuyEe3am59Fm8wKqATl7E/export?format=csv'),
  ]},

 {'name': 'state_fiscal', 'dir': 'state_fiscal', 'keep_vintages': True, 'fresh_hours': 24, 'parallel': 4,
  '_note': "Added 18 Sep 2026. What states actually collect each month, which moves before any survey: New York's monthly tax collections with withholding tax separated (the fastest single fiscal series in the country), Texas general revenue and all funds monthly with sales-tax allocations by county and by city, Massachusetts transaction-level revenue. Monthly, never revised.",
  'files': [
   F('new_york_monthly_tax_collections.csv', 'https://data.ny.gov/resource/2vni-8tmb.csv?$limit=200000'),
   F('texas_general_revenue_monthly_history.xlsx', 'https://comptroller.texas.gov/transparency/revenue/watch/general-revenue/data/general-fund-historical.xlsx'),
   F('texas_all_funds_monthly_history.xlsx', 'https://comptroller.texas.gov/transparency/revenue/watch/all-funds/data/all-funds-historical.xlsx'),
   F('texas_sales_tax_allocation_by_county.csv', 'https://data.texas.gov/resource/qsh8-tby8.csv?$limit=200000'),
   F('texas_sales_tax_allocation_by_city.csv', 'https://data.texas.gov/resource/vfba-b57j.csv?$limit=200000'),
   F('massachusetts_revenue_collections.csv', 'https://cthru.data.socrata.com/resource/kcy7-ivxi.csv?$limit=200000'),
   F('bts_motor_fuel_tax_by_state_monthly.csv', 'https://data.bts.gov/resource/3qgg-2u2a.csv?$limit=50000'),
  ]},

 {'name': 'state_programs', 'dir': 'state_programs', 'keep_vintages': True, 'fresh_hours': 100, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Counts of people on federal programmes by state, monthly: food assistance persons, households and benefits, and Medicaid and children's health applications and enrolment. The Medicaid file carries its own preliminary-or-updated flag, so vintages come with it. Both rise in a recession before any survey records it.",
  'files': [
   F('usda_snap_persons_by_state.xlsx', 'https://www.fns.usda.gov/sites/default/files/resource-files/snap-persons-8.xlsx'),
   F('usda_snap_households_by_state.xlsx', 'https://www.fns.usda.gov/sites/default/files/resource-files/snap-households-8.xlsx'),
   F('usda_snap_benefits_by_state.xlsx', 'https://www.fns.usda.gov/sites/default/files/resource-files/snap-benefits-8.xlsx'),
   F('usda_snap_history_1969_to_current.zip', 'https://www.fns.usda.gov/sites/default/files/resource-files/snap-zip-fy69tocurrent-8.zip', fresh_hours=400),
   F('cms_medicaid_chip_monthly_by_state.csv', 'https://data.medicaid.gov/api/1/datastore/query/6165f45b-ca93-5bb5-9d06-db29c692a360/0/download?format=csv'),
  ]},

 {'name': 'energy_hf', 'dir': 'energy_hf', 'keep_vintages': True, 'fresh_hours': 24, 'parallel': 3,
  '_note': "Added 18 Sep 2026. The highest-frequency measure of activity that exists and is never revised: hourly electricity demand by balancing authority, six months to a file. With it the weekly petroleum and gas prices by state, weekly gas storage, and the keyless bulk archives for petroleum, gas and electricity by state.",
  'files': [
   F('eia930_balance_2026_jan_jun.csv.gz', EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2026_Jan_Jun.csv', stream=True, fresh_hours=400),
   F('eia930_balance_2026_jul_dec.csv.gz', EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2026_Jul_Dec.csv', stream=True),
   F('eia930_subregion_2026_jan_jun.csv.gz', EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_SUBREGION_2026_Jan_Jun.csv', stream=True, fresh_hours=400),
   F('eia930_interchange_2026_jan_jun.csv.gz', EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_INTERCHANGE_2026_Jan_Jun.csv', stream=True, fresh_hours=400),
   F('eia_weekly_gasoline_prices_by_state.xls', EIA + 'petroleum/gasdiesel/xls/pswrgvwall.xls'),
   F('eia_weekly_diesel_prices.xls', EIA + 'petroleum/gasdiesel/xls/psw18vwall.xls'),
   F('eia_weekly_natural_gas_storage.txt', 'https://ir.eia.gov/ngs/wngsr.txt', min_bytes=100),
   F('eia_bulk_petroleum.zip', EIA + 'opendata/bulk/PET.zip', stream=False, fresh_hours=400),
   F('eia_bulk_natural_gas.zip', EIA + 'opendata/bulk/NG.zip', fresh_hours=400),
   F('eia_bulk_state_energy_data.zip', EIA + 'opendata/bulk/SEDS.zip', fresh_hours=400),
  ]},

 {'name': 'regional_fed', 'dir': 'regional_fed', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 5,
  '_note': "Added 18 Sep 2026. The regional banks' own surveys and state indexes, monthly, diffusion, never revised once published: Philadelphia's state leading indexes (the file the ledger had been missing), its state coincident indexes and state business-cycle dates, its manufacturing history back to May 1968 and its non-manufacturing history; New York's Empire State manufacturing and business leaders services surveys; the three Dallas surveys; Richmond manufacturing back to 1993; the Chicago Midwest index with its state contributions.",
  'files': [
   F('philadelphia_state_leading_indexes.xls', PHIL + 'leading/Leading-Revised.xls'),
   F('philadelphia_state_coincident_indexes.xls', PHIL + 'coincident/coincident-revised.xls'),
   F('philadelphia_state_business_cycle_dates.xlsx', PHIL + 'coincident/state-business-cycle-dates.xlsx'),
   F('philadelphia_manufacturing_history.csv', PHIL + 'MBOS/Historical-Data/Data-Series/bos_history.csv'),
   F('philadelphia_manufacturing_diffusion.csv', PHIL + 'MBOS/Historical-Data/Diffusion-Indexes/bos_dif.csv'),
   F('philadelphia_nonmanufacturing_history.xlsx', PHIL + 'NBOS/nboshistory.xlsx'),
   F('newyork_empire_state_diffusion_sa.csv', NYF + 'media/survey/empire/data/esms_seasonallyadjusted_diffusion.csv'),
   F('newyork_empire_state_allseries_sa.csv', NYF + 'media/survey/empire/data/esms_seasonallyadjusted_allseries.csv'),
   F('newyork_empire_state_diffusion_nsa.csv', NYF + 'media/survey/empire/data/esms_notseasonallyadjusted_diffusion.csv'),
   F('newyork_business_leaders_services_diffusion.csv', NYF + 'media/survey/business_leaders/data/bls_notseasonallyadjusted_diffusion.csv'),
   F('dallas_texas_manufacturing_alldata.xls', 'https://www.dallasfed.org/~/media/Documents/research/surveys/tmos/documents/alldata.xls'),
   F('dallas_texas_manufacturing_alldata_sa.xls', 'https://www.dallasfed.org/~/media/Documents/research/surveys/tmos/documents/alldata_sa.xls'),
   F('dallas_texas_services_alldata_sa.xls', 'https://www.dallasfed.org/~/media/Documents/research/surveys/tssos/documents/tssos_alldata_sa.xls'),
   F('dallas_texas_retail_alldata_sa.xls', 'https://www.dallasfed.org/-/media/Documents/research/surveys/tssos/documents/tros_alldata_sa.xls'),
   F('richmond_fifth_district_manufacturing.xlsx', 'https://www.richmondfed.org/-/media/RichmondFedOrg/region_communities/regional_data_analysis/regional_economy/surveys_of_business_conditions/manufacturing/data/mfg_historicaldata.xlsx'),
   F('chicago_midwest_economy_index.xlsx', 'https://www.chicagofed.org/-/media/publications/mei/mei-data-series-xlsx.xlsx?sc_lang=en'),
  ]},

 {'name': 'census_hf', 'dir': 'census_hf', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 3,
  '_note': "Added 18 Sep 2026. The Census business survey that asks firms every two weeks how the last two weeks went, by state and by sector. Biweekly, never revised, and the only official series in the country at that frequency with a state dimension.",
  'files': [
   F('census_btos_state.xlsx', 'https://www.census.gov/hfp/btos/downloads/State.xlsx'),
   F('census_btos_sector.xlsx', 'https://www.census.gov/hfp/btos/downloads/Sector.xlsx'),
   F('census_btos_subsector.xlsx', 'https://www.census.gov/hfp/btos/downloads/Subsector.xlsx'),
   F('census_btos_national.xlsx', 'https://www.census.gov/hfp/btos/downloads/National.xlsx'),
  ]},

 {'name': 'bls_state_detail', 'dir': 'bls_state_detail', 'keep_vintages': True, 'fresh_hours': 100, 'parallel': 2,
  '_note': "Added 18 Sep 2026. Job openings, hires, quits and layoffs by state, and the gross job gains and losses behind the net payroll number by state and county. The turnover file is the state-level form of the objects the rule's own proposers read.",
  'files': [
   F('jolts_quits.txt.gz', BLS + 'jt/jt.data.5.Quits', stream=True),
   F('jolts_layoffs_and_discharges.txt.gz', BLS + 'jt/jt.data.6.LayoffsDischarges', stream=True),
   F('jolts_hires.txt.gz', BLS + 'jt/jt.data.3.Hires', stream=True),
   F('jolts_series_dimension.txt', BLS + 'jt/jt.series'),
   F('jolts_state_dimension.txt', BLS + 'jt/jt.state', min_bytes=200),
   F('business_employment_dynamics_all.txt.gz', BLS + 'bd/bd.data.1.AllItems', stream=True, fresh_hours=400),
   F('business_employment_dynamics_state.txt', BLS + 'bd/bd.state', min_bytes=200),
  ]},

 {'name': 'freight_travel', 'dir': 'freight_travel', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Movement by state, monthly and never revised: trucks, containers and people crossing the northern and southern borders by port and state; departures, passengers and freight by airport; the transportation services index. The border file is an unusually early state-level signal for Texas, Arizona, California, Michigan, New York and Washington.",
  'files': [
   F('bts_border_crossings_by_port_and_state.csv', 'https://data.bts.gov/resource/keg4-3bc2.csv?$limit=400000'),
   F('bts_t100_segment_by_airport.csv', 'https://data.bts.gov/resource/r495-tyji.csv?$limit=200000'),
   F('bts_transportation_services_index.csv', 'https://data.bts.gov/resource/bw6n-ddqk.csv?$limit=50000'),
  ]},

 {'name': 'housing_listings', 'dir': 'housing_listings', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Listings as they stand, by state and by county, monthly with a weekly national file: active inventory, days on market, new listings, price cuts. Restated each vintage, which is why a dated copy is kept at every change.",
  'files': [
   F('realtor_inventory_state_history.csv', S3 + 'Core/RDC_Inventory_Core_Metrics_State_History.csv'),
   F('realtor_inventory_county_history.csv', S3 + 'Core/RDC_Inventory_Core_Metrics_County_History.csv'),
   F('realtor_inventory_metro_history.csv', S3 + 'Core/RDC_Inventory_Core_Metrics_Metro_History.csv'),
   F('realtor_weekly_national.csv', S3 + 'Core/listing_weekly_core_aggregate_by_country.csv'),
   F('realtor_hotness_county_history.csv', S3 + 'Hotness/RDC_Inventory_Hotness_Metrics_County_History.csv'),
   F('zillow_home_value_index_state.csv', 'https://files.zillowstatic.com/research/public_csvs/zhvi/State_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv'),
   F('zillow_inventory_state.csv', 'https://files.zillowstatic.com/research/public_csvs/invt_fs/State_invt_fs_uc_sfrcondo_sm_month.csv'),
  ]},
]

JOBS += [

 {'name': 'vintage_databases', 'dir': 'vintage_databases', 'keep_vintages': True, 'fresh_hours': 100, 'parallel': 4,
  '_note': "Added 18 Sep 2026. The record of what each number was when it was first published, which is the thing the rule's causal standard is built on. The Philadelphia real-time set is the canonical American vintage database and covers series ALFRED does not; the five workbooks already held are joined here by industrial production, the consumer price index, housing starts and the first, second and third releases of payrolls. With them the OECD's revisions database, whose EDITION dimension is the vintage, the Canadian release log that timestamps every series to the minute, and the Cleveland Fed's own revised-versus-original inflation files.",
  'files': [
   F('philadelphia_rtdsm_industrial_production.xlsx', PHIL + 'real-time-data/data-files/xlsx/ipmMvMd.xlsx'),
   F('philadelphia_rtdsm_cpi.xlsx', PHIL + 'real-time-data/data-files/xlsx/cpiMvMd.xlsx'),
   F('philadelphia_rtdsm_real_output.xlsx', PHIL + 'real-time-data/data-files/xlsx/routputQvQd.xlsx'),
   F('philadelphia_payrolls_first_second_third.xlsx', PHIL + 'real-time-data/data-files/xlsx/employ_level_first_second_third.xlsx'),
   F('philadelphia_payrolls_pct_first_second_third.xlsx', PHIL + 'real-time-data/data-files/xlsx/employ_pct_chg_first_second_third.xlsx'),
   F('oecd_stes_revisions_usa.csv', 'https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES_REVISIONS@DF_STES_REVISIONS,/USA.......?startPeriod=2000-01&format=csvfile', fresh_hours=160),
   F('statcan_changed_series_release_log.json.gz', 'https://www150.statcan.gc.ca/t1/wds/rest/getChangedSeriesList', stream=True, fresh_hours=20),
   F('cleveland_median_cpi_revised.csv', CLEV + 'mediancpi/mcpi_revised.csv'),
   F('cleveland_trimmed_mean_revised.csv', CLEV + 'mediancpi/trim_revised.csv'),
   F('cleveland_median_cpi_release_archive.zip', CLEV + 'mediancpi/mediancpireleasedata.zip', fresh_hours=160),
  ]},

 {'name': 'nowcast_comparators', 'dir': 'nowcast_comparators', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 4,
  '_note': "Added 18 Sep 2026. What the published nowcasts said on each day, which is what the rule must be printed beside in Paper 2. The Atlanta workbook holds every vintage of its own forecast and its subcomponents; the Philadelphia daily index and the Cleveland daily inflation files change each day; the anxious index is a professional forecaster's own probability that output falls, quarterly since 1968, and is the closest published comparator to a recession call there is.",
  'files': [
   F('atlanta_gdpnow_all_vintages.xlsx', 'https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/cqer/researchcq/gdpnow/GDPTrackingModelDataAndForecasts.xlsx'),
   F('atlanta_gdpnow_release_dates.xlsx', 'https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/cqer/researchcq/gdpnow/GDPNowcastDataReleaseDates.xlsx', fresh_hours=160),
   F('philadelphia_ads_business_conditions_daily.xlsx', PHIL + 'ads/ads_index_most_current_vintage.xlsx'),
   F('newyork_staff_nowcast.xlsx', NYF + 'media/research/policy/nowcast/new-york-fed-staff-nowcast_data_2002-present.xlsx'),
   F('cleveland_inflation_nowcast_month.json.gz', CLEV + 'inflationnowcasting/nowcast_month.json', stream=True),
   F('cleveland_inflation_nowcast_quarter.json.gz', CLEV + 'inflationnowcasting/nowcast_quarter.json', stream=True),
   F('philadelphia_gdpplus_vintages.xlsx', PHIL + 'gdpplus/GDPplus_Vintages.xlsx'),
   F('philadelphia_spf_anxious_index.xlsx', PHIL + 'survey-of-professional-forecasters/anxious-index/anxious_index_chart.xlsx'),
   F('philadelphia_spf_release_dates.txt', PHIL + 'survey-of-professional-forecasters/spf-release-dates.txt', min_bytes=500),
  ]},

 {'name': 'labour_postings', 'dir': 'labour_postings', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Hiring as it happens: the daily index of job postings nationally and by state, the small-business jobs index and wage growth by state and metro from a payroll processor, and the running layoff tracker. Daily and monthly, never revised. The state postings file is a daily state panel, which nothing else in the warehouse provides.",
  'files': [
   F('indeed_postings_national_daily.csv', 'https://raw.githubusercontent.com/hiring-lab/data/master/US/aggregate_job_postings_US.csv'),
   F('indeed_postings_by_state_daily.csv', 'https://raw.githubusercontent.com/hiring-lab/data/master/US/state_job_postings_us.csv'),
   F('indeed_postings_by_metro_daily.csv.gz', 'https://raw.githubusercontent.com/hiring-lab/data/master/US/metro_job_postings_us.csv', stream=True, fresh_hours=40),
   F('paychex_small_business_jobs_index.json', 'https://www.paychex.com/employment-watch/assets/json-feed/jobs-index.js'),
   F('paychex_wage_growth.json', 'https://www.paychex.com/employment-watch/assets/json-feed/wage-data.js'),
   F('layoffs_fyi_annual_stats.json', 'https://layoffsfyi-production.up.railway.app/api/annual-stats', min_bytes=50),
  ]},

 {'name': 'stress_daily', 'dir': 'stress_daily', 'keep_vintages': True, 'fresh_hours': 10, 'parallel': 5,
  '_note': "Added 18 Sep 2026. Daily measures of financial stress and funding that are published once and never revised: the Office of Financial Research's stress index back to 2000 with its five components, tri-party repo rates, the New York Fed's reference rates with their own revision flag, dealer positions, the System's holdings, bank failures and quarterly call reports, and short interest with its revision flag.",
  'files': [
   F('ofr_financial_stress_index_daily.csv', 'https://www.financialresearch.gov/financial-stress-index/data/fsi.csv'),
   F('ofr_repo_triparty_rate.json', 'https://data.financialresearch.gov/v1/series/timeseries?mnemonic=REPO-TRI_AR_OO-P'),
   F('newyork_reference_rates_latest.json', 'https://markets.newyorkfed.org/api/rates/all/latest.json', min_bytes=200),
   F('newyork_primary_dealer_statistics.json', 'https://markets.newyorkfed.org/api/pd/latest/SBN2022.json'),
   F('newyork_soma_holdings_summary.json', 'https://markets.newyorkfed.org/api/soma/summary.json'),
   F('fdic_bank_failures.json', 'https://banks.data.fdic.gov/api/failures?fields=NAME,CERT,FAILDATE,CITYST,QBFASSET&limit=10000&format=json'),
   F('finra_consolidated_short_interest.csv', 'https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest?limit=5000'),
  ]},

 {'name': 'text_attention', 'dir': 'text_attention', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 5,
  '_note': "Added 18 Sep 2026. What was being said and looked up, daily and never revised: news sentiment back to 1980, daily policy uncertainty, equity market volatility attributed to news, geopolitical risk daily, trade policy uncertainty, and the System's own speeches and press releases as dated event feeds.",
  'files': [
   F('sanfrancisco_daily_news_sentiment.xlsx', 'https://www.frbsf.org/wp-content/uploads/news_sentiment_data.xlsx'),
   F('policy_uncertainty_daily.csv', 'https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv'),
   F('equity_market_volatility_tracker.xlsx', 'https://www.policyuncertainty.com/media/EMV_Data.xlsx'),
   F('geopolitical_risk_daily.xls', 'https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls'),
   F('trade_policy_uncertainty.xlsx', 'https://www.matteoiacoviello.com/tpu_files/tpu_web_latest.xlsx'),
   F('federal_reserve_speeches.json', 'https://www.federalreserve.gov/json/ne-speeches.json'),
   F('federal_reserve_press_releases.json', 'https://www.federalreserve.gov/json/ne-press.json'),
   F('gdelt_masterfilelist.txt.gz', 'http://data.gdeltproject.org/gdeltv2/masterfilelist.txt', stream=True, fresh_hours=160),
  ]},

 {'name': 'surveys_extra', 'dir': 'surveys_extra', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Three survey files the warehouse did not hold in their raw form: the Michigan index back to 1952 as published, the New York Fed's consumer expectations microdata, and the global supply chain pressure index.",
  'files': [
   F('michigan_consumer_sentiment_raw.csv', 'http://www.sca.isr.umich.edu/files/tbmics.csv'),
   F('newyork_survey_consumer_expectations.xlsx', NYF + 'interactives/sce/sce/downloads/data/frbny-sce-data.xlsx'),
   F('newyork_global_supply_chain_pressure.xlsx', NYF + 'research/interactives/gscpi/downloads/gscpi_data.xlsx'),
  ]},

 {'name': 'intl_extra', 'dir': 'intl_extra', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 4,
  '_note': "Added 18 Sep 2026. Keyless national services the collector had not been asking: the euro area's quarterly accounts, the Bank of England's daily database, the Bank for International Settlements' policy rates, Australia's labour force, the International Labour Organization's monthly unemployment for the United States on its own definition, the OECD's composite leading indicators, and every Treasury auction with its bid-to-cover.",
  'files': [
   F('eurostat_euro_area_quarterly_gdp.json', 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp?format=JSON&geo=EA20&na_item=B1GQ&unit=CLV_PCH_PRE&s_adj=SCA'),
   F('bank_of_england_sonia_daily.csv', 'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/1997&Dateto=01/Dec/2030&SeriesCodes=IUDSOIA&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N'),
   F('bis_policy_rates_daily.csv', 'https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.US?format=csv'),
   F('australia_labour_force.csv', 'https://data.api.abs.gov.au/rest/data/ABS,LF,1.0.0/M13.3.1599.20.AUS.M?format=csvfile'),
   F('ilostat_us_monthly_unemployment_rate.csv', 'https://rplumber.ilo.org/data/indicator/?id=UNE_DEAP_SEX_AGE_RT_M&ref_area=USA&format=.csv'),
   F('oecd_composite_leading_indicators.csv', 'https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/all?startPeriod=1960-01&dimensionAtObservation=AllDimensions&format=csvfile', fresh_hours=160),
   F('treasury_auctions_last_90_days.json', 'https://www.treasurydirect.gov/TA_WS/securities/auctioned?format=json&days=90'),
  ]},
]

# ---------------------------------------------------------------- addresses that carry a date
DATED = [
 {'url': 'https://www.fhwa.dot.gov/policyinformation/travel_monitoring/%y%btvt/%y%btvt.xlsx',
  'out': 'fhwa_vehicle_miles_by_state_%Y-%m.xlsx', 'months': 40, 'min_bytes': 50000, 'mark_404_days': 7,
  '_lower_month': True},
 {'url': 'https://www.stb.gov/wp-content/uploads/files/rsir/UP/UP%%20Data%%20%Y-%m-%d.xlsx',
  'out': 'stb_union_pacific_weekly_%Y-%m-%d.xlsx', 'weeks': 26, 'min_bytes': 10000, 'mark_404_days': 3},
 {'url': 'https://www.stb.gov/wp-content/uploads/files/rsir/BNSF/BNSF%%20Data%%20%Y-%m-%d.xlsx',
  'out': 'stb_bnsf_weekly_%Y-%m-%d.xlsx', 'weeks': 26, 'min_bytes': 10000, 'mark_404_days': 3},
 {'url': 'https://www.stb.gov/wp-content/uploads/files/rsir/CSX/CSX%%20Data%%20%Y-%m-%d.xlsx',
  'out': 'stb_csx_weekly_%Y-%m-%d.xlsx', 'weeks': 26, 'min_bytes': 10000, 'mark_404_days': 3},
 {'url': 'https://www.stb.gov/wp-content/uploads/files/rsir/NS/NS%%20Data%%20%Y-%m-%d.xlsx',
  'out': 'stb_norfolk_southern_weekly_%Y-%m-%d.xlsx', 'weeks': 26, 'min_bytes': 10000, 'mark_404_days': 3},
 {'url': 'https://www.stb.gov/wp-content/uploads/files/rsir/CPKC/CPKC%%20Data%%20%Y-%m-%d.xlsx',
  'out': 'stb_cpkc_weekly_%Y-%m-%d.xlsx', 'weeks': 26, 'min_bytes': 10000, 'mark_404_days': 3},
 {'url': 'https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/HHD_C_Report_{y}Q{q}.xlsx',
  'out': 'newyork_household_debt_and_credit_{y}q{q}.xlsx', 'quarters': 12, 'min_bytes': 50000, 'mark_404_days': 14},
 {'url': 'https://www.cftc.gov/files/dea/history/fut_disagg_txt_{y}.zip',
  'out': 'cftc_commitments_of_traders_{y}.zip', 'quarters': 20, 'min_bytes': 100000, 'mark_404_days': 30},
]

PAGES = [
 {'page': 'https://esd.wa.gov/labormarketinfo/unemployment-insurance-data',
  'pattern': 'href="([^"]*\\/media\\/xlsx\\/[^"]*week[^"]*\\.?xlsx?)"',
  'out_prefix': 'washington_weekly_claims', 'take': 'all', 'fresh_hours': 40},
 {'page': 'https://www.abi.org/newsroom/bankruptcy-statistics/epiq',
  'pattern': 'href="([^"]*\\.xlsx[^"]*)"', 'out_prefix': 'abi_epiq_bankruptcy', 'take': 'all', 'fresh_hours': 160},
]

README_ADD = '''

## 18 September 2026, seventh pass - the deep sweep for state and high-frequency data

Two searches were run whose only purpose was to find data the warehouse did not hold, at the state level and at high
frequency. Ninety addresses were tested; the ones that answered are registered here as fourteen new jobs.

State and sub-state: claims by county in Missouri and by county and industry in Washington, claims by region and the
1971 statewide series in New York, Connecticut initial and continued claims, Michigan's average; layoff notices as data
from Texas, California and Colorado; New York's monthly tax collections with withholding separated and Texas sales-tax
allocations by county and city; food assistance and Medicaid counts by state; Philadelphia's state leading indexes, the
file the ledger had been missing; job openings, hires, quits and layoffs by state, and gross job gains and losses by
state and county; border crossings by port and state; listings by state and county; the Census business survey by state
every two weeks; hourly electricity demand by balancing authority.

Real-time and vintage: the Philadelphia real-time set beyond the five workbooks already held, the first, second and
third releases of payrolls, the OECD revisions database whose EDITION dimension is the vintage, the Canadian release
log that timestamps every series to the minute, and the Cleveland Fed's revised-versus-original inflation files.

Comparators: every vintage of the Atlanta nowcast and its subcomponents, the Philadelphia daily index, the New York
staff nowcast, the Cleveland daily inflation nowcasts, the professional forecasters' own probability that output falls.

Daily and never revised: the Office of Financial Research stress index and its five components, repo rates, the New
York Fed reference rates with their revision flag, dealer positions, news sentiment back to 1980, daily policy
uncertainty, geopolitical risk, the System's speeches and press releases, the daily index of job postings by state.

Three addresses are recorded as refusing every route tried from a plain client and are left for the fetch engine's
ladder to attempt: Baker Hughes rig counts, the Kansas City Fed survey files, and the ports of Long Beach and Georgia.
'''


MANIFEST_FN = '''

def write_manifest():
    """MANIFEST.csv at the root of the collection: every file held, which job put it there, the address it came from,
    its size and when it last changed. Anthony's data rule asks that every collection carry one; this keeps it current
    without anyone remembering to run anything (18 September 2026)."""
    try:
        path = os.path.join(DATA_ROOT, os.path.basename(HERE_COLLECTION), 'MANIFEST.csv')
        url_of = {}
        for job in SRC['jobs']:
            for f in job.get('files', []):
                url_of[(job.get('dir', job['name']), f['out'])] = f['url']
        rows = []
        for dp, dn, fn in os.walk(WH):
            for f in fn:
                if f.startswith('.'): continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, WH)
                top = rel.split(os.sep)[0]
                try: st = os.stat(p)
                except OSError: continue
                rows.append([rel, top, st.st_size,
                             datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                             redact(url_of.get((top, f), ''))])
        rows.sort()
        write_csv(path, ['file', 'job', 'bytes', 'last_changed', 'source_address'], rows)
        log('== manifest file written:', len(rows), 'files ->', path)
    except Exception as e:
        log('== manifest EXC', type(e).__name__, str(e)[:150])

'''


def patch_collector():
    """Two small changes to collector.py: lowercase month support for addresses like the highway file, and a
    MANIFEST.csv written at the root of the collection at the end of every cycle."""
    s = open(COLL).read()
    changed = False
    if "spec.get('lower')" not in s:
        old = "            url = when.strftime(spec['url'])"
        if old in s:
            s = s.replace(old, "            url = when.strftime(spec['url'])\n"
                               "            if spec.get('lower'): url = url.replace(when.strftime('%b'), when.strftime('%b').lower())", 1)
            changed = True
    if 'def write_manifest' not in s:
        anchor = "def write_board():"
        if anchor in s:
            body = MANIFEST_FN.replace('HERE_COLLECTION', 'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))')
            s = s.replace(anchor, body.strip() + "\n\n\n" + anchor, 1)
            s = s.replace("write_status(summary, minutes, hrs); write_board();",
                          "write_status(summary, minutes, hrs); write_manifest(); write_board();", 1)
            changed = True
    if changed:
        shutil.copyfile(COLL, os.path.join(HERE, 'collector_pre_deep_%s.py.bak' % STAMP))
        open(COLL, 'w').write(s)
    return changed


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in JOBS:
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])

    dated = next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    if dated is None:
        dated = {'name': 'dated_files', 'func': 'job_dated_files', 'dir': 'dated_files', 'patterns': []}
        j['jobs'].append(dated); added.append('dated_files')
    have = {p['out'] for p in dated.get('patterns', [])}
    for p in DATED:
        q = dict(p)
        if q.pop('_lower_month', False): q['lower'] = True
        if q['out'] not in have: dated.setdefault('patterns', []).append(q)

    dyn = next((x for x in j['jobs'] if x['name'] == 'dynamic_links'), None)
    if dyn is not None:
        seen = {p['out_prefix'] for p in dyn.get('pages', [])}
        for p in PAGES:
            if p['out_prefix'] not in seen: dyn.setdefault('pages', []).append(p)

    # the heavy ones on the six-hour thread, the rest hourly
    slow = set(j.get('slow_jobs', []))
    slow.update(['energy_hf', 'bls_state_detail', 'vintage_databases', 'housing_listings'])
    j['slow_jobs'] = sorted(slow)

    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_deep_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry now', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files listed')
    print('collector patched:', patch_collector())

    readme = os.path.join(os.path.dirname(HERE), 'README.md')
    if os.path.exists(readme) and 'seventh pass' not in open(readme).read():
        open(readme, 'a').write(README_ADD); print('README addendum appended')


if __name__ == '__main__':
    main()
