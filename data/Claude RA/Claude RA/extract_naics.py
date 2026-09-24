#!/usr/bin/env python3
"""Extract state x industry rows from QCEW NAICS annual singlefiles.
Keep: state areas (FIPS<=56, not US), own_code=5 (private), agglvl 53 (supersector) + 54 (sector).
Output cols: year,area,own,industry,agglvl,disc,estabs,empl,wages
"""
import zipfile, csv, io, os

YEARS = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2015, 2020, 2023, 2024]
BASE = os.path.dirname(os.path.abspath(__file__))
out = open(os.path.join(BASE, "naics_state_panel.csv"), "w", newline="")
w = csv.writer(out)
w.writerow(["year", "area", "own", "industry", "agglvl", "disc", "estabs", "empl", "wages"])
n = 0
for y in YEARS:
    zp = os.path.join(BASE, "qcew_naics", f"{y}_annual_singlefile.zip")
    with zipfile.ZipFile(zp) as z:
        name = z.namelist()[0]
        with z.open(name) as fh:
            r = csv.reader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
            header = next(r)
            for row in r:
                a, o, ind, g = row[0], row[1], row[2], row[3]
                if len(a) == 5 and a[2:] == "000" and a[:2].isdigit() and int(a[:2]) <= 56 \
                        and o == "5" and g in ("53", "54"):
                    w.writerow([row[5], a, o, ind, g, row[7], row[8], row[9], row[10]])
                    n += 1
    print(y, "done, cum rows:", n, flush=True)
out.close()
print("TOTAL", n)
