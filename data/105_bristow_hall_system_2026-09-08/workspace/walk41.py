"""WALK 41 - WALK 40 WITH A BUFFER ON EVERY LINE (declared 9 September 2026, before the run). Everything is walk40's -
the objects on first prints, the actual release days, the hub's still-falling clause, the grid, the windows, the
walk, the objective (fewest late, then soonest), the tie-break and the depth step - with one step added to the choice
at every January cut, AFTER walk40's choice is made:

THE BUFFER. A line chosen at the edge of the clean region is one grid step from a false alarm or a premature close, and
the next year's noise can cross that step. At each cut, every line in the grid (the hub's look-back and the closer's run,
which are not lines, excepted) is moved one grid step looser ALONE, and the record to the cut is re-scored. Where a
single loosening is not clean - a false alarm, a missed recession, or a close more than a month early - that line is
moved one grid step SAFER, if the safer configuration is itself clean; the test is repeated up to eight times. Where a
line has no looser grid step (it already sits at the loosest value the grid offers) or its safer step is not clean,
it is left where walk40 put it, and the diary records that the buffer could not be bought. The joint loosening (every
line one step looser at once) is also recorded, as a fact, and is not required.

Cost: the buffer is bought with speed. Its purpose is a margin against the next recession's noise, declared now and
walked from 1962 like everything else; the record is whatever it is (Rule Zero).

Run:  python3 walk41.py 1962 2026 w41   (copy cache/w40_sum.pkl to cache/w41_sum.pkl first; ~20-40 minutes)"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk40.py').read().split(_MARK)[0].replace("walk40_%s.out","walk41_%s.out"))
import pandas as pd, numpy as np

# walk39's diary amendment (an open episode followed to its close by the lines that opened it) and walk38's loop text
_t39=open('walk39.py').read().split(_MARK)[1].split("\n",1)[1]
exec(_t39.split("assert _TAIL.count")[0])          # defines _AMEND and _TAIL (walk38's loop from "Y0,Y1,VAR=")

_ANCHOR="    last=dict(p); CHOSEN[cut]=dict(p); r,t=build_v(p)"
assert _TAIL.count(_ANCHOR)==1
_BUFFER='''    # ---- WALK41: the buffer (declared 9 September 2026) ----
    _LOOSE=[n for n in NAMES if n not in ('hback','cn')]
    def _loose1(q,n):
        gr=GD[n]; i=gr.index(q[n])
        if i+1<len(gr) and gr[i+1] is not None: r=dict(q); r[n]=gr[i+1]; return r
        return None
    _p0=dict(p)
    for _it in range(8):
        _bad=[n for n in _LOOSE if (lambda q:(q is not None and clean(q,cut,ks,kt) is None))(_loose1(p,n))]
        if not _bad: break
        _moved=False
        for n in _bad:
            gr=GD[n]; i=gr.index(p[n])
            if i>=1:
                r=dict(p); r[n]=gr[i-1]
                if clean(r,cut,ks,kt) is not None: p=r; _moved=True
        if not _moved: break
    _left=[n for n in _LOOSE if (lambda q:(q is not None and clean(q,cut,ks,kt) is None))(_loose1(p,n))]
    _q=dict(p)
    for n in _LOOSE:
        gr=GD[n]; i=gr.index(p[n])
        if i+1<len(gr) and gr[i+1] is not None: _q[n]=gr[i+1]
    BUF[cut]=dict(moved={n:(_p0[n],p[n]) for n in NAMES if _p0[n]!=p[n]},unbuffered=_left,joint=clean(_q,cut,ks,kt) is not None)
    P(f"   {cut:%Y}: buffer moved {BUF[cut]['moved']} | still at the edge {_left} | joint loosening clean {BUF[cut]['joint']}")
'''
_T41=_TAIL.replace(_ANCHOR,_BUFFER+_ANCHOR)
_T41=_T41.replace("LOG=[]; CHOSEN={}; STALL=[]","LOG=[]; CHOSEN={}; STALL=[]; BUF={}")
assert _T41.count("LOG.sort(key=lambda z:z[0])")==1
_T41=_T41.replace("LOG.sort(key=lambda z:z[0])",_AMEND+"LOG.sort(key=lambda z:z[0])")
_T41=_T41+"\npickle.dump(BUF,open(f'cache/{VAR}_buf.pkl','wb'))\n"
exec("Y0,Y1,VAR=int(sys.argv[1])"+_T41)
