"""WALK 50 - WALK 47 WITH THE SEARCH WEEK IN THE SUDDEN STOP (10 September 2026, collection 108). The sudden stop K reads
one labour datum - a week of initial claims 35 per cent over its base - with the S&P 500 20 per cent under its 20-day
high; the datum is weekly, so 2020 waited for the release of 19 March. s2/search_week.py adds a daily labour datum on
the same numbers: the seven-day mean of Google searches for "unemployment" (daily from 2004) over the same base, 35 per
cent, read at the close of the day it is known. K takes the earlier of the two weeks. Nothing else changes: the grid,
the walk, the objective, the tie-break, the depth step are walk47's. Run:  python3 walk50.py 1962 2026 w50"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk47.py').read().split(_MARK)[0].replace("walk47_%s.out","walk50_%s.out"))
import pandas as pd, numpy as np
exec(open('s2/search_week.py').read())
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
