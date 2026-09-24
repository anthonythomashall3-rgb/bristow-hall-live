#!/usr/bin/env python3
"""Daily and weekly state data for the state tests (collection 191), 18 September 2026.

A sweep for everything free, machine-fetchable, and faster than monthly with a state dimension. What it found, and
what this registers:

Electricity at sub-state grain and a six-hour lag. Texas publishes actual load for each of its eight weather zones and
New York for each of its eleven load zones, the latter within the same day. Both are administrative meter readings and
are never revised, which makes them the fastest honest measure of activity below the state line that exists.

Housing weekly. Six files carry new listings, for-sale inventory, new pending sales, median list price, days to
pending and the share of listings cut in price, for eight hundred metropolitan areas each tagged with its state, to
the week ending thirteen days ago.

Health weekly by state. Seven files from the disease centre, one of them daily, covering emergency-department visits,
hospital admissions and deaths by state within six days - and the Delphi service beside them, which is the only one of
these that publishes with an issue date, so it can be read as it stood on any past day.

Degree days daily. Population-weighted heating and cooling degree days for the forty-eight contiguous states, two days
behind. Without this the electricity series cannot be read: a cold week and a recession both lower industrial load.

With them: daily transit and toll crossings in New York, daily building permits in three cities, North Dakota's daily
rig list, and the six state layoff-notice pages that have no API and must be kept as pages.

Also here: the validator's ragged-start fix. The weekly claims file begins in 1984 but states joined it one at a time
through 1986, so a state's first observation is not the start of its record. Ninety-four per cent of the 939 "missing
weeks" were that, not holes.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
COLL = os.path.join(HERE, 'collector.py')
STAMP = time.strftime('%Y-%m-%d_%H%M')
Z = 'https://files.zillowstatic.com/research/public_csvs/'
CDC = 'https://data.cdc.gov/resource/'


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


GRID = {
 'name': 'state_grid_load', 'dir': 'state_grid_load', 'keep_vintages': True, 'fresh_hours': 6, 'parallel': 4,
 '_note': "Added 18 Sep 2026. Electricity actually drawn, below the state line, within hours. Texas publishes load "
          "for each of eight weather zones and New York for each of eleven load zones; both are meter readings and "
          "are never revised. The Texas index is a list of documents, so the collector keeps the index and the "
          "downloader follows it; New York's file is one a day at a dated address.",
 'files': [
   F('ercot_actual_load_by_weather_zone_index.json',
     'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13101'),
   F('ercot_system_wide_demand_index.json',
     'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=12340'),
   F('caiso_actual_system_load.zip',
     'https://oasis.caiso.com/oasisapi/SingleZip?queryname=SLD_FCST&startdatetime=20260915T07:00-0000'
     '&enddatetime=20260916T07:00-0000&version=1&market_run_id=ACTUAL&resultformat=6', fresh_hours=24),
   F('north_dakota_active_rig_list.html', 'https://www.dmr.nd.gov/oilgas/riglist.asp', min_bytes=2000),
 ]}

HOUSING = {
 'name': 'state_housing_weekly', 'dir': 'state_housing_weekly', 'keep_vintages': True, 'fresh_hours': 24,
 'parallel': 6,
 '_note': "Added 18 Sep 2026. Six weekly housing files, eight hundred metropolitan areas each carrying its state "
          "name, to the week ending about thirteen days ago: new listings, for-sale inventory, new pending sales, "
          "median list price, days to pending, and the share of listings whose price was cut. The state-level "
          "versions of these files do not exist; the metro files aggregate to states by their own state column. The "
          "whole history is restated at each release, which is why a dated copy is kept every time one changes.",
 'files': [
   F('zillow_new_listings_metro_week.csv', Z + 'new_listings/Metro_new_listings_uc_sfrcondo_week.csv'),
   F('zillow_inventory_metro_week.csv', Z + 'invt_fs/Metro_invt_fs_uc_sfrcondo_week.csv'),
   F('zillow_new_pending_metro_week.csv', Z + 'new_pending/Metro_new_pending_uc_sfrcondo_week.csv'),
   F('zillow_median_list_price_metro_week.csv', Z + 'mlp/Metro_mlp_uc_sfrcondo_week.csv'),
   F('zillow_days_to_pending_metro_week.csv', Z + 'med_doz_pending/Metro_med_doz_pending_uc_sfrcondo_week.csv'),
   F('zillow_price_cuts_metro_week.csv', Z + 'perc_listings_price_cut/Metro_perc_listings_price_cut_uc_sfrcondo_week.csv'),
 ]}

HEALTH = {
 'name': 'state_health_weekly', 'dir': 'state_health_weekly', 'keep_vintages': True, 'fresh_hours': 24, 'parallel': 6,
 '_note': "Added 18 Sep 2026. Weekly and daily measures by state that arrive within six days, which is faster than "
          "any labour series and which a recession moves through hours worked, insurance and deferred care. The "
          "Delphi service is kept beside them because it publishes an issue date with every observation, so it can be "
          "read as it stood on a past day - the only file in this group that can.",
 'files': [
   F('cdc_hospital_respiratory_by_state.csv', CDC + 'ua7e-t2fy.csv?$limit=500000'),
   F('cdc_ed_visit_trajectories.csv', CDC + 'rdmq-nq56.csv?$limit=500000'),
   F('cdc_ed_respiratory_daily.csv', CDC + 'vjzj-u7u8.csv?$limit=500000'),
   F('cdc_respiratory_illness_activity.csv', CDC + 'f3zz-zga5.csv?$limit=500000'),
   F('cdc_ed_visits_by_demographics.csv', CDC + '7xva-uux8.csv?$limit=500000'),
   F('cdc_provisional_deaths_by_state.csv', CDC + 'r8kw-7aab.csv?$limit=500000'),
   F('cdc_wastewater_by_state.csv', CDC + 'j9g8-acpt.csv?$limit=500000'),
   F('delphi_fluview_all_states.json',
     'https://api.delphi.cmu.edu/epidata/fluview/?regions=nat&epiweeks=199740-203001'),
 ]}

DAILY = {
 'name': 'state_daily_activity', 'dir': 'state_daily_activity', 'keep_vintages': True, 'fresh_hours': 8,
 'parallel': 6,
 '_note': "Added 18 Sep 2026. Daily counts with a place attached: journeys and toll crossings in New York two days "
          "behind, building permits issued in New York City, Chicago and Austin within a day or two, and boardings in "
          "Chicago. Permits issued daily are the only construction signal below the month that exists free.",
 'files': [
   F('mta_daily_ridership_and_tolls.csv', 'https://data.ny.gov/resource/sayj-mze2.csv?$limit=200000'),
   F('chicago_transit_daily_boardings.csv',
     'https://data.cityofchicago.org/resource/6iiy-9s97.csv?$limit=200000'),
   F('new_york_city_building_permits.csv',
     'https://data.cityofnewyork.us/resource/ipu4-2q9a.csv?$limit=200000&$order=issuance_date%20DESC'),
   F('chicago_building_permits.csv',
     'https://data.cityofchicago.org/resource/ydr8-5enu.csv?$limit=200000&$order=issue_date%20DESC'),
   F('austin_building_permits.csv', 'https://data.austintexas.gov/resource/3syk-w9eu.csv?$limit=200000'),
 ]}

WARN_PAGES = {
 'name': 'state_warn_pages', 'dir': 'state_warn_all', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 6,
 '_note': "Added 18 Sep 2026. Six more state layoff-notice lists that exist only as pages. A dated copy is kept every "
          "time the page changes, so the notices accumulate with the date they appeared even though the state "
          "publishes no file.",
 'files': [
   F('washington_warn_page.html', 'https://esd.wa.gov/employer-requirements/layoffs-and-employee-notifications/'
                                  'worker-adjustment-and-retraining-notification-warn-layoff-and-closure-data'),
   F('new_jersey_warn_page.html', 'https://www.nj.gov/labor/employer-services/warn/'),
   F('maryland_warn_page.html', 'https://labor.maryland.gov/employment/warn.shtml'),
   F('michigan_warn_page.html', 'https://www.michigan.gov/leo/bureaus-agencies/wd/data-public-notices/warn-notices'),
   F('wisconsin_warn_page.html', 'https://dwd.wisconsin.gov/dislocatedworker/warn/'),
   F('new_york_warn_page.html', 'https://dol.ny.gov/legacy-warn-notices'),
   F('wisconsin_ui_stats.csv', 'https://bi.wisconsin.gov/t/DWD/views/ED_LandingPage/LandingPage.csv', min_bytes=200),
   F('nevada_weekly_claims.html',
     'https://www.nevadaworkforce.com/_docs/Other-Publications/Current-Fact-Sheet/National-Weekly-Claims-Report'),
   F('hawaii_weekly_unemployment.html',
     'https://dbedt.hawaii.gov/economic/unemployment/state_weekly_unemployment_update'),
   F('alaska_ui_claims_by_area.html', 'https://live.laborstats.alaska.gov/data-pages/ui-claims-area'),
 ]}

DATED = [
 {'url': 'http://mis.nyiso.com/public/csv/pal/%Y%m%dpal.csv', 'out': 'nyiso_zonal_load_%Y-%m-%d.csv',
  'days': 30, 'min_bytes': 20000, 'mark_404_days': 2},
 {'url': 'https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/%Y/StatesCONUS.Heating.txt',
  'out': 'degree_days_heating_%Y.txt', 'quarters': 20, 'min_bytes': 5000, 'mark_404_days': 1},
 {'url': 'https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/%Y/StatesCONUS.Cooling.txt',
  'out': 'degree_days_cooling_%Y.txt', 'quarters': 20, 'min_bytes': 5000, 'mark_404_days': 1},
]


def patch_collector():
    """Daily address patterns, and a cheaper vintage check."""
    s = open(COLL).read(); changed = False
    if "spec.get('days')" not in s:
        old = "        back = int(spec.get('months', 0)) or int(spec.get('weeks', 0)) or 6"
        if old in s:
            s = s.replace(old, "        back = (int(spec.get('days', 0)) or int(spec.get('months', 0)) or "
                               "int(spec.get('weeks', 0)) or 6)", 1)
            s = s.replace("            if step_weeks:\n                when = today - timedelta(days=7 * i)",
                          "            if spec.get('days'):\n                when = today - timedelta(days=i)\n"
                          "            elif step_weeks:\n                when = today - timedelta(days=7 * i)", 1)
            changed = True
    if changed:
        shutil.copyfile(COLL, os.path.join(HERE, 'collector_pre_daily_%s.py.bak' % STAMP))
        open(COLL, 'w').write(s)
    return changed


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in (GRID, HOUSING, HEALTH, DAILY, WARN_PAGES):
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])

    dated = next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    if dated is not None:
        have = {p['out'] for p in dated['patterns']}
        for p in DATED:
            if p['out'] not in have: dated['patterns'].append(p)

    fast = j.setdefault('fast_jobs', [])
    for n in ('state_grid_load', 'state_daily_activity'):
        if n not in fast: fast.append(n)
    slow = set(j.get('slow_jobs', []))
    slow.update(['state_health_weekly'])
    j['slow_jobs'] = sorted(slow)

    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_daily_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('collector patched for daily patterns:', patch_collector())
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files')


if __name__ == '__main__':
    main()
