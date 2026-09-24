#!/usr/bin/env python3
"""Filling the two state gaps the coverage map found (collection 191), 18 September 2026.

The map in collection 215 measured what we hold for every state: weekly claims, monthly unemployment, payrolls,
permits and business applications are complete for all 51. Two objects were nearly empty - layoff notices, held for
three states, and monthly tax receipts, held for five. This registers what a search of all fifty found, so that the
collector fetches them on its own clock from now on and no judgement is needed per fetch.

Everything here is a plain address the collector can ask for. Sources that need a nonce, a session or a browser are
deliberately left out and listed in the note at the end of this file rather than half-registered.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
GS = 'https://search/warn_lookups?utf8=%E2%9C%93&q%5Bnotice_on_gteq%5D=1990-01-01&q%5Bnotice_on_lteq%5D=2035-12-31&commit=Search'


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


WARN = [
 F('alabama_warn.html', 'https://www.madeinalabama.com/warn-list/'),
 F('alaska_warn.html', 'https://jobs.alaska.gov/RR/WARN_notices.htm'),
 F('arizona_warn.html', 'https://www.azjobconnection.gov' + GS.split('https://')[1].replace('search/', 'search/', 1)),
 F('delaware_warn.html', 'https://joblink.delaware.gov' + GS.split('https://')[1].replace('search/', 'search/', 1)),
 F('kansas_warn.html', 'https://www.kansasworks.com' + GS.split('https://')[1].replace('search/', 'search/', 1)),
 F('maine_warn.html', 'https://joblink.maine.gov' + GS.split('https://')[1].replace('search/', 'search/', 1)),
 F('vermont_warn.html', 'https://www.vermontjoblink.com' + GS.split('https://')[1].replace('search/', 'search/', 1)),
 F('florida_warn_2026.html', 'https://reactwarn.floridajobs.org/WarnList/Records?year=2026&page=1'),
 F('indiana_warn.html', 'https://www.in.gov/dwd/warn-notices/current-warn-notices/'),
 F('iowa_warn.xlsx', 'https://workforce.iowa.gov/media/1190/download?inline'),
 F('michigan_warn.json', 'https://www.michigan.gov/leo/sxa/search/results/?s=%7B8E97AB1D-D2D4-47F8-8CC4-3F1039C8854F%7D&itemid=%7BBE81F7C2-36A8-4FDE-853C-B05B6E090055%7D&sig=&autoFireSearch=true&v=%7B1FFFCC21-5151-4A2B-ABFC-F7FE4E5C9783%7D&p=500&o=Created%20Date%20sort,Descending'),
 F('new_jersey_warn_archive.xlsx', 'https://www.nj.gov/labor/assets/PDFs/WARN/WARN_Notice_Archive.xlsx'),
 F('new_york_warn.csv', 'https://public.tableau.com/views/WorkerAdjustmentRetrainingNotificationWARN/WARNList.csv?%3Aembed=y&%3AshowVizHome=n'),
 F('ohio_warn_2026.csv', 'https://dam.assets.ohio.gov/raw/upload/jfs.ohio.gov/2026/2026-warn-notice.csv'),
 F('oregon_warn.html', 'https://ccwd.hecc.oregon.gov/Layoff/WARN?page=1'),
 F('pennsylvania_warn.html', 'https://www.pa.gov/agencies/dli/programs-services/workforce-development-home/warn-requirements/warn-notices'),
 F('rhode_island_warn.xlsx', 'https://dlt.ri.gov/sites/g/files/xkgbur571/files/2025-06/Warn%20Report.xlsx'),
 F('south_dakota_warn.html', 'https://dlr.sd.gov/workforce_services/businesses/warn_notices.aspx'),
 F('tennessee_warn.html', 'https://www.tn.gov/workforce/general-resources/major-publications0/major-publications-redirect/reports.html'),
 F('utah_warn.html', 'https://jobs.utah.gov/employer/business/warnnotices.html'),
 F('washington_warn.html', 'https://fortress.wa.gov/esd/file/warn/Public/SearchWARN.aspx'),
 F('west_virginia_warn.html', 'https://workforcewv.org/job-seeker/layoffs-downsizing/warn-listing/'),
 F('wisconsin_warn.json', 'https://sheets.googleapis.com/v4/spreadsheets/1cyZiHZcepBI7ShB3dMcRprUFRG24lbwEnEDRBMhAqsA/values/Originals?key=AIzaSyBF5bsJ9oCetBmqXL5LQII4G639YaKritw'),
 F('illinois_warn.xlsx', 'https://apps.illinoisworknet.com/iebs/api/public/export?search=&layoffTypes=&trade=0&dateReportedStart=Invalid%20Date&dateReportedEnd=Invalid%20Date&statuses=4&reasons=&eventCauses=&naicsCodes=1&naicIndustries=&naics=&unionsInvolved=0&geolocation=1&cities=&counties=&lwias=&includeAdditionalLwias=false&edrs=&lat=0&lng=0&distance=.5&memberType=1&users=&accessList=&bookmarked=false'),
 F('montana_warn.xlsx', 'https://wsd.dli.mt.gov/_docs/wioa/warn_notices_july_2026.xlsx'),
 F('nebraska_warn_2020.html', 'https://dol.nebraska.gov/LayoffServices/WARNReportData/?year=2020'),
 F('hawaii_warn_2026.html', 'https://labor.hawaii.gov/wdc/2026-warn-notices/'),
 F('minnesota_warn.html', 'https://mn.gov/deed/business/layoff-resources/'),
 F('missouri_warn_2026.html', 'https://jobs.mo.gov/warn/2026'),
 F('massachusetts_warn_fy26.xlsx', 'https://www.mass.gov/doc/fy26-warn-report-0/download'),
 F('nevada_warn_2026.pdf', 'https://detr.nv.gov/content/media/WARN_and_NonWARN_Master_w_Logo_2026.pdf'),
 F('connecticut_warn.json', 'https://dolpublicdocumentlibrary.ct.gov/CsblrCategory/GetSpecializedData?pageSize=5000&pageIndex=1&prefix=%2Frapid_response%2Fwarn_documents&sortedCol=warn_document_date&module=WARN',
   headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://dolpublicdocumentlibrary.ct.gov/'}),
 F('dc_warn_2026.html', 'https://does.dc.gov/page/industry-closings-and-layoffs-warn-notifications-2026'),
 F('north_dakota_warn.pdf', 'https://www.jobsnd.com/sites/www/files/documents/jsnd-documents/WARN%20Notices%202015%20to%20present.pdf'),
 F('idaho_warn.pdf', 'https://www.labor.idaho.gov/wp-content/uploads/2026/09/Idaho-WARN-Notices.pdf'),
]

REVENUE = [
 F('census_selected_monthly_state_tax_collections.xlsx',
   'https://www2.census.gov/data/experimental-data-products/selected-monthly-sales-tax-collections/selected-monthly-sales-tax-collections-data.xlsx', fresh_hours=400),
 F('census_monthly_state_tax_sources.xlsx',
   'https://www2.census.gov/data/experimental-data-products/selected-monthly-sales-tax-collections/selected-monthly-sales-tax-collections-sources.xlsx', fresh_hours=400),
 F('colorado_sales_tax_monthly.csv', 'https://data.colorado.gov/resource/54t3-n5uh.csv?$limit=200000'),
 F('colorado_sales_tax_by_industry.csv', 'https://data.colorado.gov/resource/6kn4-89kh.csv?$limit=500000'),
 F('colorado_sales_tax_by_city.csv', 'https://data.colorado.gov/resource/2yhn-3dbj.csv?$limit=500000'),
 F('illinois_daily_collections_fy2027.xlsx',
   'https://tax.illinois.gov/content/dam/soi/en/web/tax/research/taxstats/collections-daily/daily-collections-from-major-revenue-sources-fy2027.xlsx'),
 F('illinois_monthly_collections_fy2027.xlsx',
   'https://tax.illinois.gov/content/dam/soi/en/web/tax/research/taxstats/collections-monthly/collections-remitted-to-state-comptroller-fy2027.xlsx'),
 F('iowa_monthly_memo_data.xlsx', 'https://www.legis.iowa.gov/docs/LSA/MonMemo/Monthly_Memo_Data.xlsx'),
 F('utah_revenue_summary_2026.pdf', 'https://files.tax.utah.gov/tax/esu/revenuereports/2026-revenue-summary.pdf'),
 F('wyoming_sales_use_tax_fy2027.pdf', 'https://eadiv.state.wy.us/s&utax/CMP27.pdf'),
 F('michigan_monthly_revenue_latest.pdf', 'https://sfa.senate.michigan.gov/Publications/monthrev/mrr_mostrecent.pdf'),
]

# addresses that carry a date: the collector builds them itself each cycle
DATED = [
 {'url': 'https://www.dllr.state.md.us/employment/pdf/warn-log-{y}.pdf',
  'out': 'maryland_warn_{y}.pdf', 'quarters': 60, 'min_bytes': 20000, 'mark_404_days': 14},
 {'url': 'https://www.dws.nm.gov/Portals/0/DM/Business/{y}_WARN.pdf',
  'out': 'new_mexico_warn_{y}.pdf', 'quarters': 32, 'min_bytes': 10000, 'mark_404_days': 14},
 {'url': 'https://www.laworks.net/Downloads/WFD/WarnNotices{y}.pdf',
  'out': 'louisiana_warn_{y}.pdf', 'quarters': 16, 'min_bytes': 10000, 'mark_404_days': 14},
 {'url': 'https://revenue.alabama.gov/wp-content/uploads/%Y/%m/abstract%b%yweb.pdf',
  'out': 'alabama_revenue_abstract_%Y-%m.pdf', 'months': 40, 'min_bytes': 20000, 'mark_404_days': 7, 'lower': True},
 {'url': 'https://dfa.arkansas.gov/wp-content/uploads/generalRevenue%Y%m.pdf',
  'out': 'arkansas_general_revenue_%Y-%m.pdf', 'months': 40, 'min_bytes': 20000, 'mark_404_days': 7},
 {'url': 'https://www.pa.gov/content/dam/copapwp-pagov/en/revenue/documents/news-and-statistics/reportsstats/mrr/documents/%Y/%Y_%m_mrr.pdf',
  'out': 'pennsylvania_monthly_revenue_%Y-%m.pdf', 'months': 130, 'min_bytes': 20000, 'mark_404_days': 7},
 {'url': 'https://bfm.sd.gov/dashboards/SWAT_2_gfrev_%Y%m.pdf',
  'out': 'south_dakota_general_fund_%Y-%m.pdf', 'months': 90, 'min_bytes': 10000, 'mark_404_days': 7},
 {'url': 'https://www.tn.gov/content/dam/tn/revenue/documents/statistics/%Y/Main%Y%m.xlsx',
  'out': 'tennessee_collections_%Y-%m.xlsx', 'months': 90, 'min_bytes': 20000, 'mark_404_days': 7},
 {'url': 'https://files.hawaii.gov/tax/stats/monthly/%Y%mge.xlsx',
  'out': 'hawaii_general_excise_%Y-%m.xlsx', 'months': 30, 'min_bytes': 10000, 'mark_404_days': 7},
 {'url': 'https://edr.state.fl.us/content/revenues/reports/monthly-revenue-report/newsletters/nl%b%y.pdf',
  'out': 'florida_monthly_revenue_%Y-%m.pdf', 'months': 40, 'min_bytes': 20000, 'mark_404_days': 7, 'lower': True},
 {'url': 'https://azjlbc.gov/mfh/mfh-%b-%y.pdf',
  'out': 'arizona_fiscal_highlights_%Y-%m.pdf', 'months': 40, 'min_bytes': 20000, 'mark_404_days': 7, 'lower': True},
 {'url': 'https://sfa.senate.michigan.gov/Publications/MonthRev/mrr%b%y.pdf',
  'out': 'michigan_monthly_revenue_%Y-%m.pdf', 'months': 60, 'min_bytes': 20000, 'mark_404_days': 7, 'lower': True},
 {'url': 'https://lbo.ms.gov/pdfs/fy%y_revrpt_%b_%Y.pdf',
  'out': 'mississippi_revenue_%Y-%m.pdf', 'months': 40, 'min_bytes': 10000, 'mark_404_days': 7, 'lower': True},
]

# pages whose file address changes every time it is published
PAGES = [
 {'page': 'https://www.virginiaworks.gov/warn-notices/', 'pattern': 'href="([^"]*warn_notices_[^"]*\\.csv)"',
  'out_prefix': 'virginia_warn', 'take': 'first', 'fresh_hours': 20},
 {'page': 'https://www.commerce.nc.gov/report-workforce-warn-summary-list-2026',
  'pattern': 'href="([^"]*warn[^"]*\\.csv[^"]*)"', 'out_prefix': 'north_carolina_warn', 'take': 'first',
  'fresh_hours': 20},
 {'page': 'https://kcc.ky.gov/WARN%20notices/Pages/default.aspx',
  'pattern': 'href="([^"]*WARN%20Report[^"]*\\.csv)"', 'out_prefix': 'kentucky_warn', 'take': 'all',
  'fresh_hours': 20},
 {'page': 'https://scworks.org/employer/employer-programs/risk-closing/layoff-notification-reports',
  'pattern': 'href="([^"]*WARN[^"]*\\.pdf)"', 'out_prefix': 'south_carolina_warn', 'take': 'all', 'fresh_hours': 40},
 {'page': 'https://mdes.ms.gov/information-center/warn-information/',
  'pattern': 'href="([^"]*warn[^"]*\\.pdf)"', 'out_prefix': 'mississippi_warn', 'take': 'all', 'fresh_hours': 40},
 {'page': 'https://budget.wv.gov/general-revenue-fund',
  'pattern': 'href="([^"]*media/\\d+/download[^"]*)"', 'out_prefix': 'west_virginia_revenue', 'take': 'all',
  'fresh_hours': 40},
 {'page': 'https://wsd.dli.mt.gov/wioa/related-links/warn-notice-page',
  'pattern': 'href="([^"]*warn[^"]*\\.xlsx)"', 'out_prefix': 'montana_warn_current', 'take': 'first',
  'fresh_hours': 20},
]

NOTE_WARN = ("Added 18 Sep 2026 after the coverage map in collection 215 showed layoff notices held for three states "
             "of fifty-one. Every address here was fetched and its contents read before it was written down. Three "
             "states publish nothing at all - Arkansas cites its own statute, New Hampshire takes enquiries by "
             "electronic mail, Wyoming publishes only the rules - and Oklahoma's list renders only in a browser. "
             "Nebraska's endpoint still answers but the state stopped filling it after 2020, and North Dakota's "
             "cumulative file has not moved since October 2023; both are kept so that the day they resume is "
             "recorded. Richest by far is Illinois: 4,889 notices with thirty-four columns back to 1987.")
NOTE_REV = ("Added 18 Sep 2026. Monthly tax collections were held for five states. The Census Bureau's experimental "
            "workbook carries all fifty-one at once from April 2019 to March 2025 - discontinued, which is why the "
            "live feeds below matter - and the rest are each state's own monthly report. Withholding tax, the fastest "
            "labour signal in public finance, is broken out separately by Utah, Michigan, Maryland and Arizona. "
            "Illinois publishes daily. Nine states publish only through a browser-rendered dashboard and are left out "
            "rather than half-registered.")


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for name, folder, files, note in (('state_warn_all', 'state_warn_all', WARN, NOTE_WARN),
                                      ('state_revenue', 'state_revenue', REVENUE, NOTE_REV)):
        if name not in names:
            j['jobs'].append({'name': name, 'dir': folder, 'keep_vintages': True, 'fresh_hours': 12,
                              'parallel': 6, 'mark_404_days': 3, '_note': note, 'files': files})
            added.append(name)

    dated = next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    if dated is not None:
        have = {p['out'] for p in dated.get('patterns', [])}
        for p in DATED:
            if p['out'] not in have: dated['patterns'].append(p)

    dyn = next((x for x in j['jobs'] if x['name'] == 'dynamic_links'), None)
    if dyn is not None:
        seen = {p['out_prefix'] for p in dyn.get('pages', [])}
        for p in PAGES:
            if p['out_prefix'] not in seen: dyn['pages'].append(p)

    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_stategaps_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry now', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files |',
          len(dated['patterns']) if dated else 0, 'dated patterns |', len(dyn['pages']) if dyn else 0, 'scraped pages')


if __name__ == '__main__':
    main()
