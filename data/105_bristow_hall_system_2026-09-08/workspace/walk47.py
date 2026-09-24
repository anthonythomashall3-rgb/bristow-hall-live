"""WALK 47 - WALK 46 WITH THE TROUGH CLOSERS' MONTHLY OBJECTS ON THE RELEASE-DAY VINTAGE (10 September 2026). The peak
side has read every monthly object from the series as it stood on the release day since walk45; the settling closers
R, T and S (and the confirmations of Q) still read housing starts, factory hours and the unemployment rate at each
month's first print. s2/asof_trough.py puts those four objects on the same convention - the rise of starts and of hours
from their twelve-month lows, the settling test on starts, the unemployment rate rolling over - so that one rule reads
all its monthly data one way. Everything else is walk46's: the grid, the walk, the objective, the tie-break, the depth
step. Run:  python3 walk47.py 1962 2026 w47"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0].replace("walk46_%s.out","walk47_%s.out"))
import pandas as pd, numpy as np
exec(open('s2/asof_trough.py').read())
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
