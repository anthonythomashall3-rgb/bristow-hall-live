#!/usr/bin/env python3
"""MANIFEST.csv: one row per delivered series. first/last obs read from the values;
pct_repeated_values = share of observations equal to the previous observation of the same
series (for vintage panels: computed on the first-print series and on each issue's run)."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def pct_rep(s):
    s = s.dropna()
    if len(s) < 2:
        return np.nan
    return round(100 * float((s.values[1:] == s.values[:-1]).mean()), 2)


rows = []
df = pd.read_csv(os.path.join(HERE, "permits_asprinted_1960_1999.csv"), dtype={"month": str, "issue_ym": str})
for var, name in (("permits_authorized_saar_thous", "New private housing units authorized by building permits, total, SAAR, thousands"),
                  ("starts_total_saar_thous", "New private housing units started, total (incl. farm), SAAR, thousands")):
    x = df[df[var].notna()].sort_values(["issue_ym", "month"])
    within = np.mean([pct_rep(g[var]) for _, g in x.groupby("issue_ym") if len(g) > 1])
    rows.append({"file": "permits_asprinted_1960_1999.csv", "source": "FRASER, Economic Indicators (CEA for JEC), monthly issues",
                 "url": "https://fraser.stlouisfed.org/files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf (7 issues: EI_<MM><YYYY>.pdf)",
                 "series": name + " -- all months printed in each issue (vintage panel)",
                 "frequency": "monthly observations x monthly issues",
                 "first_obs": x.month.min(), "last_obs": x.month.max(), "first_issue": x.issue_ym.min(), "last_issue": x.issue_ym.max(),
                 "n_issues": x.issue_ym.nunique(), "n_obs": len(x), "pct_repeated_values": round(within, 2)})
    fp = x[x.is_newest_month].sort_values("month")
    rows.append({"file": "permits_asprinted_1960_1999.csv", "source": "FRASER, Economic Indicators", "url": "(as above)",
                 "series": name + " -- newest month of each issue (first print)", "frequency": "monthly",
                 "first_obs": fp.month.min(), "last_obs": fp.month.max(), "first_issue": fp.issue_ym.min(), "last_issue": fp.issue_ym.max(),
                 "n_issues": fp.issue_ym.nunique(), "n_obs": len(fp), "pct_repeated_values": pct_rep(fp.set_index("month")[var])})
f = os.path.join(HERE, "bcd", "bcd_series29_asprinted.csv")
if os.path.exists(f):
    b = pd.read_csv(f, dtype={"month": str, "issue_ym": str})
    for kind, name in (("level", "BCD series 29, new private housing units authorized by local building permits, SAAR, thousands (Oct 1961 issue only)"),
                       ("index", "BCD series 29, index of new private housing units authorized by local building permits, 1957-59=100, SA")):
        x = b[(b.kind == kind) & b.value.notna()]
        if x.empty:
            continue
        rows.append({"file": "bcd/bcd_series29_asprinted.csv", "source": "FRASER, Business Cycle Developments (Census), Table 1 Basic data",
                     "url": "https://fraser.stlouisfed.org/files/docs/publications/BusCycD/60-69/BCD_<MM><YYYY>.pdf",
                     "series": name, "frequency": "monthly observations x monthly issues",
                     "first_obs": x.month.min(), "last_obs": x.month.max(), "first_issue": x.issue_ym.min(), "last_issue": x.issue_ym.max(),
                     "n_issues": x.issue_ym.nunique(), "n_obs": len(x),
                     "pct_repeated_values": round(np.mean([pct_rep(g.sort_values("month").value) for _, g in x.groupby("issue_ym") if len(g) > 1]), 2)})
pd.DataFrame(rows).to_csv(os.path.join(HERE, "MANIFEST.csv"), index=False)
print(pd.DataFrame(rows).to_string())
