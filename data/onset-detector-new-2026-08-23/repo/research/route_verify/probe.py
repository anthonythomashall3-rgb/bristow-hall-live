import json, urllib.request, urllib.error, ssl, socket, time
u=json.load(open('research/route_verify/unverified_40.json'))
# best-effort concrete probe URL per source_id
URL={
'abi_bankruptcy_statistics__epiq_partnered_monthly_highlights':'https://www.abi.org/newsroom/bankruptcy-statistics',
'adobe_digital_insights___adobe_analytics_e_commerce_releases':'https://business.adobe.com/blog',
'attom_foreclosure_market_and_u_s__housing_reports':'https://www.attomdata.com/news/',
'chief_executive_ceo_confidence_index':'https://chiefexecutive.net/category/ceo-confidence-index/',
'creighton_mid_america_business_conditions_index':'https://www.creighton.edu/economicoutlook',
'dallas_fed_banking_conditions_survey__bcs':'https://www.dallasfed.org/research/surveys/bcs',
'descartes_datamyne_global_shipping_report__us_container_impo':'https://www.descartes.com/resources/knowledge-center',
'epiq_aacer_monthly_us_bankruptcy_filing_statistics':'https://www.globenewswire.com/news-release/2026/08/06/3340394/10374/en/July-Small-Business-Filings-Increase-24-Year-Over-Year.html',
'fdic_bankfind_suite_api__failures__institutions__quarterly_f':'https://banks.data.fdic.gov/api/failures?sort_by=FAILDATE&sort_order=DESC&format=json&limit=1',
'ny_fed_business_leaders_survey__regional_service_sector':'https://www.newyorkfed.org/medialibrary/media/survey/business_leaders/bls_diffusion.csv',
'port_of_savannah_monthly_container_volumes__gpa_press_releas':'https://gaports.com/press-releases/',
'realclearmarkets_tipp_economic_optimism_index':'https://www.realclearmarkets.com/2026/08/04/as_household_finances_strengthen_rcmtipp_holds_gains_1198381.html',
'restaurant_performance_index__rpi':'https://restaurant.org/research-and-media/research/economists-notebook/',
'senior_loan_officer_opinion_survey_on_bank_lending_practices':'https://www.federalreserve.gov/data/sloos/sloos-202607.htm',
'vistage_ceo_confidence_index':'https://www.vistage.com/ceoindex/',
'aar_weekly_railroad_traffic__us_carloads___intermodal__20_co':'https://www.aar.org/news/',
'aisi_weekly_raw_steel_production__adjusted_production___capa':'https://www.steel.org/industry-data/',
'california_edd_warn_report__state_primary_source':'https://edd.ca.gov/en/jobs_and_training/layoff_services_warn/',
'dol_eta_unemployment_insurance_weekly_claims___state_level_d':'https://oui.doleta.gov/unemploy/claims.asp',
'drewry_world_container_index__wci__weekly_composite':'https://www.drewry.co.uk/supply-chain-advisors/supply-chain-expertise/world-container-index-assessed-by-drewry',
'kastle_systems_back_to_work_barometer__10_city_office_occupa':'https://www.kastle.com/safety-wellness/getting-america-back-to-work/',
'optimal_blue_mortgage_market_indices__obmmi':'https://www2.optimalblue.com/obmmi/',
'str__costar__weekly_u_s__hotel_performance':'https://www.costar.com/products/str-benchmark/resources/press-releases',
'adp_national_employment_report___ner_pulse__weekly':'https://adpemploymentreport.com/',
'airdna_monthly_market_review__u_s__short_term_rentals':'https://www.airdna.co/monthly-market-review',
'america_s_credit_unions___monthly_credit_union_estimates__mc':'https://www.americascreditunions.org/news-media/news',
'ata_for_hire_truck_tonnage_index':'https://www.trucking.org/news-insights',
'california_dof_finance_bulletin__monthly_economic_update_and':'https://dof.ca.gov/media/docs/forecasting/economics/economic-and-revenue-updates/Finance-Bulletin-July-2026.pdf',
'chicago_business_barometer__ism_chicago_pmi__produced_with_m':'https://mnimarkets.com/chicago-business-barometer-aka-chicago-pmi-publication-calendar',
'cnbc_nrf_retail_monitor__powered_by_affinity_solutions':'https://nrf.com/research-insights/nrf-cnbc-retail-monitor',
'cpb_world_trade_monitor':'https://www.cpb.nl/en/world-trade-monitor',
'ffiec_central_data_repository___public_data_distribution__bu':'https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx',
'fiserv_small_business_index':'https://www.fiserv.com/en/about-fiserv/resource-center/fiserv-small-business-index.html',
'georgia_dor_monthly_net_tax_revenue_releases':'https://dor.georgia.gov/press-releases',
'linkedin_workforce_report___economic_graph_hiring_rate':'https://economicgraph.linkedin.com/resources/linkedin-workforce-report',
'opportunity_insights_economic_tracker___weekly_job_postings_':'https://raw.githubusercontent.com/OpportunityInsights/EconomicTracker/main/data/Job%20Postings%20-%20National%20-%20Weekly.csv',
'paychex_small_business_employment_watch__small_business_jobs':'https://www.paychex.com/employment-watch',
'rsm_us_middle_market_business_index__mmbi':'https://rsmus.com/middle-market/mmbi.html',
'transunion_monthly_credit_industry_snapshot':'https://www.transunion.com/lp/monthly-industry-snapshot',
'vantagescore_creditgauge__monthly_consumer_credit_health':'https://vantagescore.com/insights/creditgauge/',
}
ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36'
out=[]
for s in u:
    sid=s['source_id']; url=URL.get(sid)
    r={'source_id':sid,'probe_url':url,'rights':s['rights']}
    if not url:
        r['status']='NO_URL'; out.append(r); continue
    try:
        req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'*/*'})
        t0=time.time()
        resp=urllib.request.urlopen(req,timeout=15,context=ctx)
        body=resp.read(4096)
        r['status']=resp.status
        r['final_url']=resp.geturl()
        r['content_type']=resp.headers.get('Content-Type','')
        r['content_length']=resp.headers.get('Content-Length','')
        r['bytes_read']=len(body)
        r['first_bytes']=body[:180].decode('utf-8','replace').replace('\n',' ').replace('\r',' ')
        r['ms']=int((time.time()-t0)*1000)
    except urllib.error.HTTPError as e:
        r['status']='HTTP_%s'%e.code; r['content_type']=e.headers.get('Content-Type','') if e.headers else ''
        try: r['first_bytes']=e.read(180).decode('utf-8','replace').replace('\n',' ')
        except: pass
    except Exception as e:
        r['status']='ERR'; r['error']=type(e).__name__+':'+str(e)[:120]
    out.append(r)
    print(sid, r['status'], r.get('content_type','')[:40], r.get('content_length',''))
json.dump(out, open('research/route_verify/probe_results.json','w'), indent=1)
