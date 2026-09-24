"""Window exposure of the route's second condition, measured OUTSIDE the United States.
Data: 28_intl_expansion_2026-09/{eurostat,oecd}/unemployment (monthly rates) and eurostat/gdp_q.
Episodes: technical recessions (two consecutive negative quarters of GDP); window [peak-9, peak+18] months.
Second condition: the Sahm form, three-month mean less its trailing twelve-month minimum, line 0.50.
Result (4 Sep 2026): 52 country files, 316 episodes, 241 detected in window (76%);
13,616 quiet country-months, 2,450 at or above 0.50 = 18.0% exposure, against 0.9-6.5% measured on US data.
"""

# rerun output appended below
