import json,collections
r={x['source_id']:x for x in json.load(open('research/route_verify/probe_results.json'))}
# per-route: shape_class (R109 vocab), fold target, verdict
# verdicts: ROUTE_VERIFIED_DATA / ROUTE_VERIFIED_LANDING / ROUTE_BOT_BLOCKED / ROUTE_404_UNCONFIRMED / ROUTE_TIMEOUT
M={
'fdic_bankfind_suite_api__failures__institutions__quarterly_f':('ROUTE_VERIFIED_DATA','openfema_json_api(analog json-REST)','B-RESV-PARSER','json meta+data, total=4115 records, format=json; no key'),
'opportunity_insights_economic_tracker___weekly_job_postings_':('ROUTE_VERIFIED_DATA','provider_csv_download','B-RESV-PARSER-1','raw.githubusercontent CSV, weekly job postings header measured'),
'california_dof_finance_bulletin__monthly_economic_update_and':('ROUTE_VERIFIED_DATA','file_download_landing(PDF)','B-RESV-PARSER','%PDF-1.7 235564B, concrete Finance-Bulletin-July-2026.pdf pattern live'),
'senior_loan_officer_opinion_survey_on_bank_lending_practices':('ROUTE_VERIFIED_LANDING','fed_ddp_csv/fred_json_api(proven)','B-RESV-PROVEN','sloos-202607.htm 200; SLOOS also on FRED+DDP XML zip -> proven shape'),
'ny_fed_business_leaders_survey__regional_service_sector':('ROUTE_404_UNCONFIRMED','provider_csv_download','B-RESV-PARSER-1','guessed CSV path 404->/errors/404; publisher proven (nyfed_business_leaders) but exact service-sector CSV URL unverified'),
'abi_bankruptcy_statistics__epiq_partnered_monthly_highlights':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','abi.org 200 html'),
'attom_foreclosure_market_and_u_s__housing_reports':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','attomdata.com/news 200 228185B'),
'chief_executive_ceo_confidence_index':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','chiefexecutive.net category 200'),
'creighton_mid_america_business_conditions_index':('ROUTE_VERIFIED_LANDING','file_download_landing(PDF)','B-RESV-PARSER','creighton economicoutlook 200; monthly PDF'),
'dallas_fed_banking_conditions_survey__bcs':('ROUTE_VERIFIED_LANDING','provider_xlsx_download/official_html_table','B-RESV-PARSER','dallasfed BCS 200 40195B; Dallas surveys are proven xlsx family'),
'descartes_datamyne_global_shipping_report__us_container_impo':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','descartes knowledge-center 200 351706B'),
'epiq_aacer_monthly_us_bankruptcy_filing_statistics':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','globenewswire release 200; monthly PR archive = first-print'),
'realclearmarkets_tipp_economic_optimism_index':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','rcm article 200 6505B'),
'restaurant_performance_index__rpi':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','restaurant.org economists-notebook 200'),
'vistage_ceo_confidence_index':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','vistage.com/ceoindex 200 215612B'),
'aar_weekly_railroad_traffic__us_carloads___intermodal__20_co':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','aar.org/news 200'),
'aisi_weekly_raw_steel_production__adjusted_production___capa':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','steel.org/industry-data 200'),
'california_edd_warn_report__state_primary_source':('ROUTE_VERIFIED_LANDING','file_download_landing(XLSX)','B-RESV-PARSER','edd.ca.gov WARN page 200 159096B; XLSX workbook link'),
'dol_eta_unemployment_insurance_weekly_claims___state_level_d':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','oui.doleta.gov/unemploy/claims.asp 200 query form; output=Spreadsheet/XML'),
'drewry_world_container_index__wci__weekly_composite':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','drewry.co.uk 200 116201B (note EP flagged robots-block; direct GET succeeded here)'),
'kastle_systems_back_to_work_barometer__10_city_office_occupa':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','kastle.com back-to-work 200; charts only, no bulk file'),
'optimal_blue_mortgage_market_indices__obmmi':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','www2.optimalblue.com/obmmi 200; JS chart export'),
'adp_national_employment_report___ner_pulse__weekly':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','adpemploymentreport 200 1341B (JS app shell); NER also on FRED/ALFRED lane'),
'airdna_monthly_market_review__u_s__short_term_rentals':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','airdna.co monthly-market-review 200; report library email/account gate'),
'ata_for_hire_truck_tonnage_index':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','trucking.org/news-insights 200; FRED mirror TRUCKD11'),
'chicago_business_barometer__ism_chicago_pmi__produced_with_m':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','mnimarkets calendar 200 101279B'),
'ffiec_central_data_repository___public_data_distribution__bu':('ROUTE_VERIFIED_LANDING','bulk_zip_download(form POST)','B-RESV-PARSER','cdr.ffiec.gov DownloadBulkData.aspx 200 29436B; bulk needs form POST/period select'),
'georgia_dor_monthly_net_tax_revenue_releases':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','dor.georgia.gov/press-releases 200'),
'paychex_small_business_employment_watch__small_business_jobs':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','paychex.com/employment-watch 200'),
'rsm_us_middle_market_business_index__mmbi':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','rsmus mmbi.html 200 252292B'),
'vantagescore_creditgauge__monthly_consumer_credit_health':('ROUTE_VERIFIED_LANDING','published_output_landing_scrape','B-RESV-PARSER','vantagescore creditgauge 200 108216B'),
# bot-blocked
'port_of_savannah_monthly_container_volumes__gpa_press_releas':('ROUTE_BOT_BLOCKED','NO_CLEAN_ROUTE','NO_ROUTE','403 Cloudflare "Just a moment"; anti-bot wall, no automatable route without headless'),
'str__costar__weekly_u_s__hotel_performance':('ROUTE_BOT_BLOCKED','NO_CLEAN_ROUTE','NO_ROUTE','403 Access Denied (Akamai); anti-bot wall'),
'transunion_monthly_credit_industry_snapshot':('ROUTE_BOT_BLOCKED','NO_CLEAN_ROUTE','NO_ROUTE','403 Cloudflare + form-gated PDF; free_registration_key'),
# 404 unconfirmed
'america_s_credit_unions___monthly_credit_union_estimates__mc':('ROUTE_404_UNCONFIRMED','UNKNOWN','DISCOVERY_FIRST','404 at news landing; EP already noted MCUE data page 404; route needs discovery'),
'cnbc_nrf_retail_monitor__powered_by_affinity_solutions':('ROUTE_404_UNCONFIRMED','UNKNOWN','DISCOVERY_FIRST','404 next.js error page at probed nrf path; route needs discovery'),
'cpb_world_trade_monitor':('ROUTE_404_UNCONFIRMED','file_download_landing(XLSX)','DISCOVERY_FIRST','404 at /en/world-trade-monitor; monthly Excel exists on release pages, exact path unverified'),
'fiserv_small_business_index':('ROUTE_404_UNCONFIRMED','UNKNOWN','DISCOVERY_FIRST','404 at resource-center path; JS index site, route needs discovery'),
'linkedin_workforce_report___economic_graph_hiring_rate':('ROUTE_404_UNCONFIRMED','file_download_landing(PDF)','DISCOVERY_FIRST','404 "Resource at .../linkedin-workforce-report" not found; archive path unverified'),
# timeout
'adobe_digital_insights___adobe_analytics_e_commerce_releases':('ROUTE_TIMEOUT','UNKNOWN','DISCOVERY_FIRST','read timeout 15s at business.adobe.com/blog; unmeasurable this batch (unknown)'),
}
rows=[]
for sid,(verdict,shape,fold,note) in M.items():
    p=r[sid]
    rows.append({'source_id':sid,'probe_url':p.get('probe_url'),'http_status':p['status'],
        'content_type':p.get('content_type',''),'content_length':p.get('content_length',''),
        'bytes_read':p.get('bytes_read'),'rights':p['rights'],
        'verdict':verdict,'shape_class':shape,'fold_target':fold,'note':note})
assert len(rows)==40,len(rows)
json.dump(rows,open('research/route_verify/classified_40.json','w'),indent=1)
c=collections.Counter(x['verdict'] for x in rows)
f=collections.Counter(x['fold_target'] for x in rows)
print('N',len(rows))
print('verdict',dict(c))
print('fold',dict(f))
