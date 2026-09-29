#!/usr/bin/env python3
"""Fetch FRASER Economic Indicators monthly PDFs (1960-1999).

URL pattern (verified 2026-09-29 on 01-1960, 06-1965, 10-1969, 03-1975, 07-1985,
05-1990, 07-1999): https://fraser.stlouisfed.org/files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf
FRASER drops browser User-Agents, so the default python-urllib UA is used.
Every request is logged (URL, HTTP status, content-type, bytes) to fetch_log.csv.
Politeness: >= 1.5 s between requests.
Usage: fetch_ei.py [first_year] [last_year]
"""
import csv, os, sys, time, urllib.request, urllib.error

BASE = "https://fraser.stlouisfed.org/files/docs/publications/ei/{y}/{m:02d}-{y}.pdf"
# some issues are stored as EI_MMYYYY.pdf instead (found from the FRASER item pages, e.g.
# /title/economic-indicators-1/february-1962-471 -> ei/1962/EI_021962.pdf); S3 answers 403 for a missing key
ALT = "https://fraser.stlouisfed.org/files/docs/publications/ei/{y}/EI_{m:02d}{y}.pdf"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "raw", "pdf")
LOG = os.path.join(HERE, "fetch_log.csv")
os.makedirs(OUT, exist_ok=True)


def fetch(url, dest):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
            ctype = r.headers.get("Content-Type", "")
            status = r.status
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), 0
    except Exception as e:  # network error
        return f"ERR:{type(e).__name__}:{e}", "", 0
    if status == 200 and data[:5] == b"%PDF-":
        with open(dest, "wb") as f:
            f.write(data)
    else:
        status = f"{status}-NOTPDF"
    return status, ctype, len(data)


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 1960
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 1999
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as lf:
        w = csv.writer(lf)
        if new:
            w.writerow(["utc", "url", "status", "content_type", "bytes"])
        for y in range(y0, y1 + 1):
            for m in range(1, 13):
                dest = os.path.join(OUT, f"{m:02d}-{y}.pdf")
                if os.path.exists(dest) and os.path.getsize(dest) > 10000:
                    continue
                for url in (BASE.format(y=y, m=m), ALT.format(y=y, m=m)):
                    for attempt in range(2):
                        st, ct, n = fetch(url, dest)
                        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), url, st, ct, n])
                        lf.flush()
                        time.sleep(1.5)
                        if st in (200, 403, 404):
                            break
                        time.sleep(5 * (attempt + 1))
                    if st == 200:
                        break
                print(y, m, st, n, flush=True)


if __name__ == "__main__":
    main()
