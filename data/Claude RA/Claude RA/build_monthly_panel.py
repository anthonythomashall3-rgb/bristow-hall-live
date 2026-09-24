#!/usr/bin/env python3
"""Monthly state x supersector employment panel from the repo's ind_state CES pulls.
READ-ONLY on the repo; output lands in Claude RA. Prefer SA ({ST}{IND}.csv),
fall back to NSA ({ST}{IND}N.csv) flagged sa=0. Format: FRED csv (observation_date,VALUE).
Output: state,ind,sa,date,empl (thousands).
"""
import os, csv, re

SRC = os.path.expanduser("~/Projects/bristow-hall/repo/data_archive/current_revised_and_spatial/ind_state")
OUT = os.path.expanduser("~/Desktop/Recession Papers/Claude RA/ind_state_monthly.csv")
INDS = ["CONS","EDUH","FIRE","GOVT","INFO","LEIH","MFG","NRMN","PBSV","SRVO","TRAD"]
# NRMN is the SA mnemonic for natural resources/mining (FRED: e.g. AKNRMN); its NSA twin ends NRMNN
files = set(os.listdir(SRC))
w = csv.writer(open(OUT, "w", newline=""))
w.writerow(["state","ind","sa","date","empl"])
states = sorted(set(f[:2] for f in files if re.match(r"^[A-Z]{2}", f)))
n = miss = 0
for st in states:
    for ind in INDS:
        sa, fn = 1, f"{st}{ind}.csv"
        if fn not in files:
            sa, fn = 0, f"{st}{ind}N.csv"
        if fn not in files:
            miss += 1
            continue
        with open(os.path.join(SRC, fn)) as fh:
            r = csv.reader(fh)
            header = next(r)
            for row in r:
                if len(row) >= 2 and row[1] not in (".", ""):
                    w.writerow([st, ind, sa, row[0][:7], row[1]])
                    n += 1
print("states:", len(states), "rows:", n, "missing state-ind pairs:", miss)
