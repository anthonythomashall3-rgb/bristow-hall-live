import json,collections,re
rows=json.load(open('research/resv_triage/rows.json'))
PROVEN={'bea_api','bls_json','census_api','census_btos_xlsx','census_qss_timeseries_zip',
'dallas_wei_xlsx','dol_ui_weekly_claims_report_html','eia_v2_json','fed_ddp_csv','fiscaldata_json',
'forecast_xlsx','fred_graph_csv','fred_json_api','geo_grid_json','geo_panel_json',
'nber_macrohistory_dat','regional_survey_xlsx','socrata_json','tabular_csv','treasury_yield_xml',
'tsa_passenger_html'}

def classify(r):
    ep=(r['ep'] or '').lower(); st=(r['estatus'] or ''); auth=(r['auth'] or ''); pub=(r['pub'] or '')
    # Non-automatable discovery landings first -> no concrete route (shape = DISCOVERY_LANDING_NO_ROUTE)
    if 'DISCOVERY_ONLY_NOT_AUTOMATABLE' in st: return ('DISCOVERY_NO_ROUTE', 'no-route')
    if st=='CANDIDATE_UNVERIFIED_ROUTE': return ('CANDIDATE_UNVERIFIED', 'no-route')
    if 'OFFICIAL_LANDING_DISCOVERY_ONLY' in st: return ('DISCOVERY_NO_ROUTE','no-route')
    # proven API transports by auth / status
    if auth=='FRED_API_KEY' or 'FRED_JSON_API' in st: return ('fred_json_api','proven')
    if auth=='CENSUS_API_KEY' or 'CENSUS_API' in st: return ('census_api','proven')
    if auth=='EIA_API_KEY' or 'EIA_V2_JSON' in st: return ('eia_v2_json','proven')
    if auth=='BEA_API_KEY': return ('bea_api','proven')
    # protocol discovered
    if st=='PROTOCOL_DISCOVERED_SDMX': return ('sdmx_json','NEW')
    if st=='PROTOCOL_DISCOVERED_CDX': return ('wayback_cdx','NEW')
    if 'DDP_ROUTE' in st: return ('fed_ddp_csv','proven')
    if 'POST_XML_API' in st: return ('post_xml_api','NEW')
    # endpoint extension based
    if ep.endswith('.xml') or 'treasury' in ep and 'yield' in ep: return ('treasury_yield_xml','proven?')
    if re.search(r'\.xlsx?($|\?)',ep): return ('generic_xlsx','proven?')
    if re.search(r'\.csv($|\?)',ep): return ('generic_csv','proven?')
    if re.search(r'\.(zip)($|\?)',ep): return ('bulk_zip','NEW')
    if re.search(r'\.json($|\?)',ep) or 'api' in ep and 'json' in st.lower(): return ('generic_json_api','NEW')
    if 'HTML_TABLE' in st or 'WEB_TABLE' in st or 'DATA_TABLE_LANDING' in st: return ('html_table','proven?')
    if 'BULK' in st or 'DOWNLOAD_LANDING' in st or 'EXACT_DOWNLOAD' in st: return ('bulk_download','NEW')
    if 'SURVEY_LANDING' in st or 'RELEASE_LANDING' in st or 'DATASET_LANDING' in st or 'OUTPUT_LANDING' in st or 'REPORT_LANDING' in st or 'SNAPSHOT_LANDING' in st or 'PROGRAM_LANDING' in st: return ('landing_page_scrape','NEW')
    return ('UNCLASSIFIED','?')

for r in rows:
    sh,cls=classify(r); r['shape']=sh; r['class']=cls

byshape=collections.Counter(r['shape'] for r in rows)
byclass=collections.Counter(r['class'] for r in rows)
print('=== SHAPE COUNTS ===')
for k,v in byshape.most_common(): print(f'  {v:3}  {k}')
print('=== CLASS ROLLUP ===')
for k,v in byclass.most_common(): print(f'  {v:3}  {k}')
json.dump(rows,open('research/resv_triage/classified.json','w'),indent=1)
