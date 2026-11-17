"""THE DISTURBANCE CHRONOLOGY'S SIX FRED SERIES, DOWNLOADED BEFORE THE SITE IS BUILT (17 November 2026, collection 1141; Anthony:
"ensure that we fix the issue and that this never happens again").

Until today disturbance_site.py downloaded them AFTER bhs_site.py had built the data page, so the data page's six disturbance rows
showed the files the run BEFORE had downloaded. On 17 Nov the 9:15 ET G.17 release revised September's industrial production
(103.9506 -> 103.8458): every run's data page carried the old file, the source gate held it, a held run commits nothing, so the
next run started from the same old file and was held again (three runs, 9:16 to 9:32 ET).

run_cloud.sh runs this before bhs_site.py: the six files go to out/fred_latest (all six or none: a failed download leaves the
last files in place and exits 1), and disturbance_site.py then dates the chronology from these same files instead of downloading
again, so the data page and the chronology show one read. No AI. Usage (from the workspace): python3 s2/disturbance/fred_refresh.py"""
import os, shutil, sys, urllib.request
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
from disturbance_chronology import SERIES
DEST = os.path.join(H, 'out', 'fred_latest'); TMP = DEST + '.tmp'


def main():
    shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
    for s in SERIES:
        body = None
        for _ in range(3):
            try:
                # the default client, as disturbance_chronology.fetch_fred: FRED leaves a named client unanswered (found 17 Nov 2026)
                with urllib.request.urlopen('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + s, timeout=30) as r: body = r.read()
                if body.count(b'\n') > 100 and body[:16].lower().startswith(b'observation_date'): break
                body = None
            except Exception as e:
                err = e
        if body is None:
            shutil.rmtree(TMP, ignore_errors=True)
            print('disturbance series not refreshed before the site build (%s could not be read): the chronology step downloads them itself' % s); sys.exit(1)
        open(os.path.join(TMP, s + '.csv'), 'wb').write(body)
    os.makedirs(DEST, exist_ok=True)
    for s in SERIES: os.replace(os.path.join(TMP, s + '.csv'), os.path.join(DEST, s + '.csv'))
    shutil.rmtree(TMP, ignore_errors=True)
    print('disturbance series refreshed before the site build: %s' % ', '.join(SERIES))


if __name__ == '__main__':
    main()
