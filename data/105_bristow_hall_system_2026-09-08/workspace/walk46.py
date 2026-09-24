"""WALK 46 - WALK 45 WITH THE HOUSING PAIR'S LINE FIXED AT 1.0: BOTH HALVES AT THEIR LINES (10 September 2026, after the
audit). walk38 to walk45 let the walk choose the pair's line from a grid of 1.10, 1.00, 0.95, 0.90, 0.85, 0.80 - a
confirmation by starts at 85 per cent of their fall and the unemployment rate at 85 per cent of its rise - and, on a
tie, took the looser value because a confirmer cannot cause a call by itself. On the release-day vintage that looseness
is what confirmed the insured-rate proposal of 25 October 1984: on 19 September 1984 starts stood 27.4 log points below
their twelve-month high as then published (February 1984 had been revised up from 2,197 to 2,262 thousand), 0.945 of
the 29-point line, and the pair's line that year was 0.85. A pair is two objects at their lines; a pair at 85 per cent
of two lines is a different, looser object that no structural reason supports. The line is therefore fixed at 1.0 and
leaves the grid. Everything else is walk45's. Run:  python3 walk46.py 1962 2026 w46"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk45.py').read().split(_MARK)[0].replace("walk45_%s.out","walk46_%s.out"))
import pandas as pd, numpy as np
GRID=[(n,g) for n,g in GRID if n!='hline']; NAMES=[n for n,_ in GRID]; GD=dict(GRID)
BASE15=dict(BASE15); BASE15['hline']=1.0
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
