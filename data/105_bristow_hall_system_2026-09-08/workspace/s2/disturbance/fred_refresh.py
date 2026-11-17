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


# 1052 speed (17 Nov 2026): ON A RELEASE DAY THE PUBLISHER'S OWN SERIES. At the release run FRED has not posted yet, so its file carried
# the month before (and, at the G.17, September before its revision): the data page's disturbance rows and the chronology showed the
# old numbers while the detector had the new release, and the source gate held the build (17 Nov, 9:16 ET). A series whose release is
# out today and whose publisher now differs from FRED's file is written from the publisher (s2/publisher_first.py: the G.17 file, the
# BLS through s2/bls_fetch.py, the BEA API), in fredgraph's layout; FRED's file replaces it whole once FRED posts the same numbers.
# Parity: ops/speed/parity_disturbance_overlay.py (the publisher's series equal to FRED's once FRED has posted).
OVERLAY = {'INDPRO': 'fed_g17', 'PAYEMS': 'bls_empsit', 'UNRATE': 'bls_empsit', 'GDPC1': 'bea_gdp'}
# W875RX1 is not here: BEA's Table 2.6 line 36 is not FRED's W875RX1 to the last digit (parity, 17 Nov 2026: 1959 months differ), so it
# stays FRED's, as CMRMTSPL (FRED's own computation) does


def _num(v):
    return ('%d' % v) if float(v).is_integer() else repr(float(v))


def publisher_overlay(d):
    try:
        sys.path.insert(0, os.path.dirname(H)); import publisher_first as pf, pandas as pd, io
    except Exception as e:
        print('publisher overlay: not run (%s)' % e); return
    day = pf.ny_day()
    for s, g in OVERLAY.items():
        try:
            if g not in pf.RID or day not in pf.release_days(g): continue
            if s == 'W875RX1':
                cur = pf.bea_series('T20600', '36', 'M')
            else:
                cur = pf.publisher([s], full=True)[s]
            cur = cur.dropna()
            f = os.path.join(d, s + '.csv'); fr = pd.read_csv(f); fr.columns = ['date', 'v']; fr['v'] = pd.to_numeric(fr.v, errors='coerce'); fr = fr.dropna()
            fs = pd.Series(fr.v.values, index=pd.to_datetime(fr.date))
            ix = fs.index.intersection(cur.index)
            newer = len(cur) and cur.index[-1] > fs.index[-1]
            revised = [str(x.date()) for x in ix if fs[x] != cur[x]]
            if not newer and not revised: continue
            cur = cur[cur.index >= fs.index[0]]   # FRED's own first month
            open(f, 'w').write('observation_date,%s\n' % s + ''.join('%s,%s\n' % (x.strftime('%Y-%m-%d'), _num(v)) for x, v in cur.items()))
            print('publisher overlay: %s from the publisher (%s through %s%s); FRED had through %s' % (s, g, cur.index[-1].strftime('%Y-%m'),
                  ('; revised ' + ', '.join(revised[-3:])) if revised else '', fs.index[-1].strftime('%Y-%m')))
        except Exception as e:
            print('publisher overlay: %s not read from the publisher (%s); FRED\'s file stands' % (s, str(e)[:120]))


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
    publisher_overlay(TMP)
    os.makedirs(DEST, exist_ok=True)
    for s in SERIES: os.replace(os.path.join(TMP, s + '.csv'), os.path.join(DEST, s + '.csv'))
    shutil.rmtree(TMP, ignore_errors=True)
    # 1116h (17 Nov 2026; Anthony: "fix everything else"): when the six files were read, in the chronology's own clock and layout, for the
    # data page's "Refreshed" column (it showed the chronology's last build, one run behind: s2/tool_inputs.py disturbance_rows)
    import datetime as _dt, json as _json
    _json.dump({'at': _dt.datetime.now().isoformat(timespec='seconds')}, open(os.path.join(H, 'out', 'fred_refreshed.json'), 'w'))
    print('disturbance series refreshed before the site build: %s' % ', '.join(SERIES))


if __name__ == '__main__':
    main()
