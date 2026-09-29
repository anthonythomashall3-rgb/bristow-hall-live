#!/usr/bin/env python3
"""Fetch FRASER Business Cycle Developments (BCD, title 43) issues Oct 1961 - Dec 1962.
URL pattern (from item page /title/business-conditions-digest-43/october-1962-7184):
  https://fraser.stlouisfed.org/files/docs/publications/BusCycD/60-69/BCD_<MM><YYYY>.pdf
Default python-urllib UA; >=1.5 s between requests; every request logged to fetch_log.csv."""
import csv, os, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://fraser.stlouisfed.org/files/docs/publications/BusCycD/60-69/BCD_{m:02d}{y}.pdf"
months = [(1961, m) for m in (10, 11, 12)] + [(1962, m) for m in range(1, 13)]
new = not os.path.exists(os.path.join(HERE, "fetch_log.csv"))
with open(os.path.join(HERE, "fetch_log.csv"), "a", newline="") as lf:
    w = csv.writer(lf)
    if new:
        w.writerow(["utc", "url", "status", "content_type", "bytes"])
    for y, m in months:
        dest = os.path.join(HERE, "pdf", f"BCD_{m:02d}{y}.pdf")
        if os.path.exists(dest):
            continue
        url = BASE.format(y=y, m=m)
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                data = r.read(); st = r.status; ct = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            data = b""; st = e.code; ct = e.headers.get("Content-Type", "")
        except Exception as e:
            data = b""; st = f"ERR:{type(e).__name__}"; ct = ""
        if st == 200 and data[:5] == b"%PDF-":
            open(dest, "wb").write(data)
        w.writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), url, st, ct, len(data)]); lf.flush()
        print(y, m, st, len(data), flush=True)
        time.sleep(1.5)
