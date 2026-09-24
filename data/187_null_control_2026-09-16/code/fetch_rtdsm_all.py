#!/usr/bin/env python3
"""Fetch the whole Philadelphia Fed Real-Time Data Set for Macroeconomists, not three files of it.

WHY THIS MATTERS TO THE RULE. Three legs of the tool are priced on series whose FRED vintage history
begins in 2011 (AUTHNOTT, DRSFRMACBS) or 2021 (BBKMCOIX). A leg that can only be shown on revised data
is a leg whose historical calls cannot be demonstrated as they would have been seen. The RTDSM is the
oldest continuous vintage archive that exists for American macro aggregates -- monthly matrices back
to 1962 and quarterly ones to 1965 -- so it is the substrate on which a substitute for those legs can
be priced honestly.

THE TRAP IN FETCHING IT. The listing page is rendered client-side and serves no links, and the file
host answers EVERY path with HTTP 200: a request for `zzzfakeMvMd.xlsx` returns 18,397 bytes of
JavaScript with a 200 and a text/html content type. A name probe by status code therefore reports that
every name exists, which is what the first pass here did -- 71 variables, all "found". Existence is
decided by the response BODY: a real vintage matrix is a zip (PK magic) of a few megabytes. Nothing in
this file trusts a status code.
"""
import os, sys, time, urllib.request, urllib.error, concurrent.futures as cf

B = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx'
DEST = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/outputs/rtdsm'
os.makedirs(DEST, exist_ok=True)

MON = """ipt ipm ipcd ipcn ipbe ipmat ipfinal ipp cum cut cuall m1 m2 m3 mb bra brc brn brt employ h hs hg
ruc lfc lfpart lfnc cpi ppi pcpi wsd hstarts nap napmpi rsales ftb tb3m oli ipmfg iputil ipmining
ulc oph hours payems unrate""".split()
QTR = """routput noutput rcon rcond rconnd rcons rconshh rinvbf rinvresid rinvchi rnx rex rim rg rgf rgsl
wsd oli corpbt ndpi nsave rate ulc ruc p poutput pimp h nfi rtfpi ipt m1 m2 rgdp ngdp pgdp rconhh
rinvent rprofits nfi rnfi hstarts ruc lfc""".split()

def grab(args):
    kind, v = args
    suf = 'MvMd' if kind == 'M' else 'QvQd'
    url = '%s/%s%s.xlsx' % (B, v, suf)
    path = os.path.join(DEST, '%s%s.xlsx' % (v, suf))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                b = r.read()
            if len(b) > 20000 and b[:2] == b'PK':
                with open(path, 'wb') as f: f.write(b)
                return (kind, v, 'ok', len(b))
            return (kind, v, 'not-a-file', len(b))
        except Exception as e:
            if attempt == 2: return (kind, v, 'error:%s' % type(e).__name__, 0)
            time.sleep(2 + 3 * attempt)

if __name__ == '__main__':
    jobs = [('M', v) for v in dict.fromkeys(MON)] + [('Q', v) for v in dict.fromkeys(QTR)]
    t0 = time.time(); ok = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for kind, v, st, n in ex.map(grab, jobs):
            if st == 'ok':
                ok.append((kind, v, n)); print('  %s %-10s %8.2f MB' % (kind, v, n / 1e6), flush=True)
    print('\nreal vintage matrices: %d of %d probed, %.1f min'
          % (len(ok), len(jobs), (time.time() - t0) / 60))
    with open(os.path.join(DEST, 'MANIFEST_rtdsm.csv'), 'w') as f:
        f.write('kind,variable,bytes\n')
        for kind, v, n in ok: f.write('%s,%s,%d\n' % (kind, v, n))
