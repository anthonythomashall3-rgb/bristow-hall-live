#!/usr/bin/env python3
"""Parity across all fifty-one jurisdictions (collection 191), 18 September 2026.

Anthony's rule: if we hold a thing for one state we must hold it for all of them, or the states cannot be compared.
A sweep for the missing states of every partial object produced one clear finding and one clear design rule.

The finding: most partial objects have an all-fifty-one backbone that we were not using, and the state-specific feeds
we had were the exception rather than the object. Electricity is the case in point - we held three grid operators
covering three states, while the Energy Information Administration publishes every balancing authority and every
sub-region in two files, covering forty-nine states and the District. Petrol prices are the same: nine states have an
official weekly series and all fifty-one have a daily one. Transit, permits and business surveys likewise.

The rule, written into the coverage map: every object must have an all-fifty-one backbone, and anything finer is an
extra that may never stand in for the object. A metropolitan permit feed is not a state permit series; it is detail
on top of one. This patch registers the backbones that were missing and marks the extras as extras.

Two objects have no backbone and the search says plainly why. Alaska and Hawaii have no balancing authority, so
hourly load stops at forty-nine states and the District. And only New York and Texas publish lottery sales as data;
the state-revenue retail sales files are the substitute, Colorado's being the template.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'sources.json')
STAMP = time.strftime('%Y-%m-%d_%H%M')
EIA = 'https://www.eia.gov/'


def F(out, url, **kw):
    d = {'url': url, 'out': out}; d.update(kw); return d


GRID = {
 'name': 'grid_all_states', 'dir': 'grid_all_states', 'keep_vintages': False, 'fresh_hours': 8, 'parallel': 4,
 '_note': "Added 18 Sep 2026 as the all-states backbone for electricity, replacing three single-operator feeds as the "
          "object. Sixty balancing authorities in one file and every sub-region in another: the thirteen-state "
          "eastern market by twenty-one zones, the midcontinent by six, New England by eight, the southwest power "
          "pool by seventeen, New York by eleven, California by four, Texas by eight, New Mexico by nine, the Dakotas "
          "and Wyoming by three, and the southeast and northwest by authority. Hourly, one to two hours behind. The "
          "raw demand column is never revised; the adjusted one is. Alaska and Hawaii have no balancing authority and "
          "therefore no hourly load anywhere - that is the whole of the gap, and it is the country's, not ours.",
 'files': [
   F('eia930_subregion_2026_jul_dec.csv.gz',
     EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_SUBREGION_2026_Jul_Dec.csv', stream=True),
   F('eia930_balance_2026_jul_dec.csv.gz',
     EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_BALANCE_2026_Jul_Dec.csv', stream=True),
   F('eia930_interchange_2026_jul_dec.csv.gz',
     EIA + 'electricity/gridmonitor/sixMonthFiles/EIA930_INTERCHANGE_2026_Jul_Dec.csv', stream=True),
   F('bpa_five_minute_load.txt', 'https://transmission.bpa.gov/business/operations/Wind/baltwg.txt', min_bytes=2000),
 ]}

ENERGY = {
 'name': 'state_energy_production', 'dir': 'state_energy_production', 'keep_vintages': True, 'fresh_hours': 100,
 'parallel': 4,
 '_note': "Added 18 Sep 2026. Production and electricity sales by state, monthly, for every producing state at once, "
          "so that the two states whose regulators publish daily files stop being the object. Crude oil, natural gas "
          "withdrawals, and retail electricity sales and revenue by state and sector. Mine employment and production "
          "by state quarterly from the mine safety administration.",
 'files': [
   F('eia_crude_production_by_state.xls', EIA + 'dnav/pet/xls/PET_CRD_CRPDN_ADC_MBBL_M.xls'),
   F('eia_natural_gas_withdrawals_by_state.xls', EIA + 'dnav/ng/xls/NG_PROD_SUM_A_EPG0_VGM_MMCF_M.xls'),
   F('eia_retail_electricity_sales_by_state.xlsx', EIA + 'electricity/data/eia861m/xls/sales_revenue.xlsx'),
   F('msha_open_government_index.html', 'https://arlweb.msha.gov/OpenGovernmentData/OGIMSHA.asp', min_bytes=2000),
 ]}

FUEL = {
 'name': 'state_fuel_prices', 'dir': 'state_fuel_prices', 'keep_vintages': True, 'fresh_hours': 12, 'parallel': 4,
 '_note': "Added 18 Sep 2026. The daily page covering all fifty-one is already held; this adds the official weekly "
          "workbook, which carries the nine states that have their own series plus every refining district, so that "
          "each of the other forty-two states has an official regional series to be checked against. New York "
          "publishes its own eleven regions weekly.",
 'files': [
   F('eia_weekly_fuel_prices_all_areas.xls', EIA + 'petroleum/gasdiesel/xls/pswrgvwall.xls'),
   F('new_york_weekly_gasoline_by_region.csv', 'https://data.ny.gov/resource/nqur-w4p7.csv?$limit=100000'),
   F('new_york_fuel_spot_prices.csv', 'https://data.ny.gov/resource/k7gz-mn77.csv?$limit=100000'),
   F('new_york_heating_oil_by_region.csv', 'https://data.ny.gov/resource/rc94-5y2u.csv?$limit=100000'),
 ]}

SPEND = {
 'name': 'state_retail_sales', 'dir': 'state_retail_sales', 'keep_vintages': True, 'fresh_hours': 40, 'parallel': 4,
 '_note': "Added 18 Sep 2026. Lottery sales exist as data in two states only, so they cannot be the object. Retail "
          "sales as reported to state revenue departments are the substitute and exist in far more states; Colorado's "
          "file, by county and industry and month, is the template, and the same object is sought in every other "
          "state by the discovery job. Casino and sports-wagering revenue in Connecticut joins them as the same "
          "family of discretionary spending.",
 'files': [
   F('colorado_retail_sales_by_county_monthly.csv', 'https://data.colorado.gov/resource/fe4v-h3pk.csv?$limit=500000'),
   F('pennsylvania_lottery_by_county_annual.csv', 'https://data.pa.gov/resource/hymg-bws9.csv?$limit=100000'),
   F('connecticut_casino_slot_revenue.csv', 'https://data.ct.gov/resource/rfjk-ajfm.csv?$limit=100000'),
   F('connecticut_online_casino_revenue.csv', 'https://data.ct.gov/resource/imqd-at3c.csv?$limit=100000'),
   F('connecticut_sports_wagering.csv', 'https://data.ct.gov/resource/yb54-t38r.csv?$limit=100000'),
 ]}

HOUSING = {
 'name': 'state_housing_backbone', 'dir': 'state_housing_backbone', 'keep_vintages': True, 'fresh_hours': 40,
 'parallel': 3,
 '_note': "Added 18 Sep 2026. State-level housing where the weekly files are metropolitan: the state home-value index "
          "and the state market tracker, both carrying all fifty-one.",
 'files': [
   F('zillow_home_value_index_by_state.csv',
     'https://files.zillowstatic.com/research/public_csvs/zhvi/State_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv'),
   F('redfin_state_market_tracker.tsv.gz',
     'https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/state_market_tracker.tsv000.gz',
     stream=False),
 ]}

PERMITS_EXTRA = {
 'name': 'permits_daily_metro', 'dir': 'permits_daily_metro', 'keep_vintages': True, 'fresh_hours': 24, 'parallel': 8,
 '_note': "Added 18 Sep 2026, and marked an EXTRA rather than an object. Permits issued daily in twenty places. The "
          "state permit object remains the Census monthly file, which covers all fifty-one; these are detail on top "
          "of it and must never be read as a state series, because the twenty-nine states without such a feed would "
          "silently read as zero.",
 'files': [
   F('seattle_permits.csv', 'https://data.seattle.gov/resource/76t5-zqzr.csv?$limit=200000'),
   F('new_orleans_permits.csv', 'https://data.nola.gov/resource/rcm3-fn58.csv?$limit=200000'),
   F('cincinnati_permits.csv', 'https://data.cincinnati-oh.gov/resource/thvx-5mem.csv?$limit=200000'),
   F('los_angeles_permits.csv', 'https://data.lacity.org/resource/pi9x-tg5x.csv?$limit=200000'),
   F('mesa_permits.csv', 'https://citydata.mesaaz.gov/resource/dzpk-hxfb.csv?$limit=200000'),
   F('norfolk_permits.csv', 'https://data.norfolk.gov/resource/fahm-yuh4.csv?$limit=200000'),
   F('montgomery_county_md_permits.csv',
     'https://data.montgomerycountymd.gov/resource/m88u-pqki.csv?$limit=200000'),
   F('prince_georges_county_permits.csv',
     'https://data.princegeorgescountymd.gov/resource/weik-ttee.csv?$limit=200000'),
   F('cambridge_permits.csv', 'https://data.cambridgema.gov/resource/9qm7-wbdc.csv?$limit=200000'),
   F('san_francisco_permits.csv', 'https://data.sfgov.org/resource/i98e-djp9.csv?$limit=200000'),
   F('marin_county_permits.csv', 'https://data.marincounty.gov/resource/mkbn-caye.csv?$limit=200000'),
   F('sonoma_county_permits.csv', 'https://data.sonomacounty.ca.gov/resource/88ms-k5e7.csv?$limit=200000'),
   F('baton_rouge_permits.csv', 'https://data.brla.gov/resource/7fq7-8j7r.csv?$limit=200000'),
   F('new_jersey_statewide_permits.csv', 'https://data.nj.gov/resource/w9se-dmra.csv?$limit=500000'),
   F('philadelphia_permits.json',
     'https://phl.carto.com/api/v2/sql?q=SELECT%20*%20FROM%20permits%20ORDER%20BY%20permitissuedate%20DESC%20LIMIT%20100000'),
 ]}

DATED = [
 {'url': 'https://docs.misoenergy.org/marketreports/%Y%m%d_rf_al.xls',
  'out': 'miso_load_%Y-%m-%d.xls', 'days': 21, 'min_bytes': 5000, 'mark_404_days': 2},
]

PAGES = [
 {'page': 'https://rigcount.bakerhughes.com/na-rig-count',
  'pattern': 'href="([^"]*static-files/[^"]*)"', 'out_prefix': 'baker_hughes_rig_count', 'take': 'all',
  'fresh_hours': 100},
]


def main():
    j = json.load(open(SRC))
    names = [x['name'] for x in j['jobs']]
    added = []
    for job in (GRID, ENERGY, FUEL, SPEND, HOUSING, PERMITS_EXTRA):
        if job['name'] not in names:
            j['jobs'].append(job); added.append(job['name'])

    dated = next((x for x in j['jobs'] if x['name'] == 'dated_files'), None)
    if dated is not None:
        have = {p['out'] for p in dated['patterns']}
        for p in DATED:
            if p['out'] not in have: dated['patterns'].append(p)
    dyn = next((x for x in j['jobs'] if x['name'] == 'dynamic_links'), None)
    if dyn is not None:
        seen = {p['out_prefix'] for p in dyn.get('pages', [])}
        for p in PAGES:
            if p['out_prefix'] not in seen: dyn['pages'].append(p)

    slow = set(j.get('slow_jobs', []))
    slow.update(['grid_all_states', 'permits_daily_metro', 'state_energy_production'])
    j['slow_jobs'] = sorted(slow)
    fast = j.setdefault('fast_jobs', [])
    if 'state_fuel_prices' not in fast: fast.append('state_fuel_prices')

    shutil.copyfile(SRC, os.path.join(HERE, 'sources_pre_parity_%s.json.bak' % STAMP))
    json.dump(j, open(SRC, 'w'), indent=1)
    print('jobs added:', added)
    print('registry:', len(j['jobs']), 'jobs |', sum(len(x.get('files', [])) for x in j['jobs']), 'files')


if __name__ == '__main__':
    main()
