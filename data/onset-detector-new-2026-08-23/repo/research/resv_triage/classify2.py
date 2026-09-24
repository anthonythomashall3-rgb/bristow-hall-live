import json,collections,re
d=json.load(open('live_data/config/planned_sources.v1.json'))['sources']
PROVEN={'bea_api','bls_json','census_api','census_btos_xlsx','census_qss_timeseries_zip',
'dallas_wei_xlsx','dol_ui_weekly_claims_report_html','eia_v2_json','fed_ddp_csv','fiscaldata_json',
'forecast_xlsx','fred_graph_csv','fred_json_api','geo_grid_json','geo_panel_json',
'nber_macrohistory_dat','regional_survey_xlsx','socrata_json','tabular_csv','treasury_yield_xml',
'tsa_passenger_html'}

def classify(s):
    ep=(s.get('endpoint') or '').lower(); st=s.get('endpoint_status') or ''; auth=s.get('auth_env') or ''
    # 1) NO CONCRETE ROUTE -> cannot be shaped (§6.3)
    if 'DISCOVERY_ONLY_NOT_AUTOMATABLE' in st: return 'zz_NO_ROUTE_discovery_only','no-route'
    if st=='CANDIDATE_UNVERIFIED_ROUTE': return 'zz_NO_ROUTE_candidate_unverified','no-route'
    if 'DISCOVERY_ONLY_NOT_AUTOMATABLE_UNTIL_URL_RECONFIRMED' in st: return 'zz_NO_ROUTE_discovery_only','no-route'
    # 2) PROVEN API transports (auth or status) -> §6.2 free
    if auth=='FRED_API_KEY' or 'FRED_JSON_API' in st or 'alfred' in s['source_id']: return 'fred_json_api','proven'
    if auth=='CENSUS_API_KEY' or 'CENSUS_API' in st: return 'census_api','proven'
    if auth=='EIA_API_KEY' or 'EIA_V2_JSON' in st: return 'eia_v2_json','proven'
    if auth=='BEA_API_KEY': return 'bea_api','proven'
    if 'DDP_ROUTE' in st: return 'fed_ddp_csv','proven'
    if 'data.bts.gov' in ep or 'socrata' in ep: return 'socrata_json','proven'
    if 'mccracken' in ep: return 'fred_macro_panel_csv','proven'  # FRED-MD, landed offline
    # 3) NEW concrete-route shapes
    if st=='PROTOCOL_DISCOVERED_SDMX': return 'sdmx_json','NEW'
    if st=='PROTOCOL_DISCOVERED_CDX': return 'wayback_cdx_snapshot','NEW'
    if 'POST_XML_API' in st: return 'post_xml_api','NEW'
    if 'fema.gov/api' in ep: return 'openfema_json_api','NEW'
    if re.search(r'\.zip($|\?)',ep): return 'bulk_zip_download','NEW'
    if re.search(r'\.xlsx?($|\?)',ep): return 'provider_xlsx_download','NEW'
    if re.search(r'\.csv($|\?)',ep): return 'provider_csv_download','NEW'
    if 'HTML_TABLE' in st or 'WEB_TABLE' in st or 'DATA_TABLE' in st or 'HTML_TABLE_HUB' in st: return 'official_html_table','NEW'
    if 'EXACT_DOWNLOAD' in st or 'BULK_DOWNLOAD' in st or 'BULK_DIRECTORY' in st or 'DOWNLOAD_LANDING' in st: return 'file_download_landing','NEW'
    # 4) landing pages needing scrape of a published output (no direct file yet)
    return 'published_output_landing_scrape','NEW'

res=[]
for s in d:
    sh,cls=classify(s)
    res.append({'id':s['source_id'],'shape':sh,'class':cls,'reg':s.get('registry_status'),
                'tz':s.get('release_timezone'),'auth':s.get('auth_env')})
json.dump(res,open('research/resv_triage/final.json','w'),indent=1)

byshape=collections.Counter(r['shape'] for r in res)
print('=== FINAL SHAPE COUNTS (proven first) ===')
for r in sorted(byshape.items()):
    cls=next(x['class'] for x in res if x['shape']==r[0])
    print(f'  {r[1]:3}  [{cls:8}] {r[0]}')
print()
c=collections.Counter(r['class'] for r in res)
print('CLASS ROLLUP:',dict(c))
proven_shapes={r['shape'] for r in res if r['class']=='proven'}
new_shapes={r['shape'] for r in res if r['class']=='NEW'}
print('distinct PROVEN shapes used:',len(proven_shapes),sorted(proven_shapes))
print('distinct NEW shapes needed:',len(new_shapes),sorted(new_shapes))
print('no-route instances:',c['no-route'])
