# -*- coding: utf-8 -*-
"""THE PUBLISHER OF EACH FEED THE RULE READS (audit-0924, 24 September 2026; one list since 25 September 2026, ops-0924).
Anthony: every link to the publisher's own page, exact words only, no explanatory sentences. The data page (bhs_site.py)
shows these, and the state the site publishes (bhs_state.json) carries the same: the publisher's name, its own page (None:
the feed's own address, already the publisher's) and the cadence it keeps.
Since collection 411 (25 September 2026; Anthony: "All data links should be to the exact source") the links the site shows are
the exact pages the numbers are read from (s2/source_links.py); the publisher's page here is kept only as the address of last
resort, for a row no exact page is known for, and the cadence is still shown from this list."""
import re

PUB = {'S&P 500':('S&P Dow Jones Indices, S&P 500','https://www.spglobal.com/spdji/en/indices/equity/sp-500/','Every trading day, 4:00 PM ET'),
      'Federal funds target range':('Federal Reserve, FOMC statement','https://www.federalreserve.gov/monetarypolicy/openmarket.htm','At each FOMC decision, 2:00 PM ET'),
      'Initial claims':('Department of Labor, weekly claims release',None,'Weekly, Thursday 8:30 AM ET'),
      'State insured unemployment rates':('Department of Labor, ETA 539',None,'Weekly, Thursday'),
      'Unemployment rate, factory hours':('Bureau of Labor Statistics, Employment Situation',None,'Monthly, 8:30 AM ET'),
      'Job openings':('Bureau of Labor Statistics, JOLTS',None,'Monthly, 10:00 AM ET'),
      'Housing starts':('Census Bureau, New Residential Construction',None,'Monthly, 8:30 AM ET'),
      'Commercial paper':('Federal Reserve, H.15 Selected Interest Rates',None,'Daily, 4:15 PM ET'),
      'Industrial production':('Federal Reserve, G.17 Industrial Production and Capacity Utilization',None,'Monthly, 9:15 AM ET'),
      'State continued weeks claimed':('Department of Labor, ETA 539; Bureau of Labor Statistics',None,'Monthly'),
      'State unemployment rates':('Bureau of Labor Statistics, Local Area Unemployment Statistics',None,'Monthly, 10:00 AM ET'),
      'Real GDP':('Bureau of Economic Analysis, Gross Domestic Product',None,'Quarterly, 8:30 AM ET'),
      'GDPNow':('Federal Reserve Bank of Atlanta, GDPNow',None,'Several times a month'),
      'Sahm rule':('Federal Reserve Bank of St. Louis, FRED SAHMREALTIME',None,'Monthly'),
      'Search week':('Google Trends, United States',None,'Daily')}


def strip_paren(x):
    return re.sub(r'\s*\([^)]*\)', '', x or '').replace('  ', ' ').strip().rstrip(':,')


def pub(name):
    for k, v in PUB.items():
        if str(name or '').startswith(k):
            return v
    return None


_ABOUT = re.compile(r',?\s*(?:at\s+)?about\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\s*ET', re.I)


def normalize(feed):
    """A feed record as the data page shows it: the publisher's own page (a FRED address only where FRED is the publisher)
    and the exact cadence; an approximate clock ("about 8 PM ET") leaves the source."""
    p = pub(strip_paren(feed.get('name')))
    if p:
        if p[1]:
            feed['url'] = p[1]
        feed['every'] = p[2]
    if feed.get('source'):
        feed['source'] = _ABOUT.sub('', feed['source'])
    return feed
