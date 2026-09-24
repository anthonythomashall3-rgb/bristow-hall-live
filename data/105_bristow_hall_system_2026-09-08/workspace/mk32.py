# walk32 = walk31 with the one-clock menu, the days as tie-break, and no stall (collection 104, 8 September 2026)
s=open('walk31.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 31 - ONE CLOCK (collection 104, 8 September 2026).','"""WALK 32 - ONE CLOCK, THE MENU THAT SURVIVES IT (collection 104, 8 September 2026). Three changes to walk31.\n(1) The closer menu is C, K, H and J. Frozen at walk30\'s end configuration and dated on the firing day, S, R, T and Q\nfire at the pauses their dating rules used to hide: T closes the 1973-75 recession in August 1974, R closes 1980 in\nFebruary 1980 and 2007 in December 2007, Q closes 1981-82 in June 1981, S never closes at all. Their safety was the\nsettle-month date and the rule that a close may not be dated before the onset; on one clock that protection is gone.\nC, K, H and J fire on falls from a hump with a run and never fired at a pause. (2) The walk\'s objective keeps the\nmonth terms first and adds the day terms of walk30 after them (the count of calls more than thirty-one days after\nthe month ended, the median and the mean of the days), so that two configurations with the same months are separated\nby how early in the month they spoke and the confirmers do not drift to their loosest lines on a tie (walk31 chose a\nvacancy line of 0.12 at the 1962 cut on such a tie and called December 1962). (3) A cut with no clean point keeps the\nlast configuration and goes on logging, so the diary never has a gap; the cut is listed in STALL.\n\nWALK 31 - ONE CLOCK (collection 104, 8 September 2026).')
rep("MENU=None\ndef build_v(p):\n","MENU={'C','K','H','J'}   # the one-clock menu, declared (see the docstring)\ndef build_v(p):\n")
# the objective: months first, then days
rep("    v=[s['errp'][j] for j in ks]                        # ONE CLOCK: the error, in months, of the month the rule spoke\n",
    "    v=[(s['errp'][j],s['lags'][j]) for j in ks]         # ONE CLOCK: (error in months of the month the rule spoke, days after the month ended)\n")
rep("        if er<-1: return None                              # ONE CLOCK: closed more than a month before the trough month\n        w.append(er)",
    "        if er<-1: return None                              # ONE CLOCK: closed more than a month before the trough month\n        w.append((er,lg))")
rep("    a=(sum(1 for x in v if abs(x)>1), float(np.median([abs(x) for x in v])), float(np.mean([abs(x) for x in v])))\n    if not w: return a+(0,0.0,0.0)\n",
    "    def side(z):\n        m=[e for e,_ in z]; d=[l for _,l in z]\n        return (sum(1 for x in m if abs(x)>1), float(np.median([abs(x) for x in m])), float(np.mean([abs(x) for x in m])),\n                sum(1 for x in d if x>31), float(np.median(d)), float(np.mean(d)))\n    a=side(v)\n    if not w: return a+(0,0.0,0.0,0,0.0,0.0)\n")
rep("    return a+(sum(1 for x in w if abs(x)>1), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))",
    "    return a+side(w)")
rep("    if clean(p,cut,ks,kt) is None: continue\n",
    "    if clean(p,cut,ks,kt) is None:\n        STALL.append(Y); p=dict(last) if last is not None else dict(p)   # no clean point at this cut: the rule keeps its last configuration\n")
rep("LOG=[]; CHOSEN={}\nPROG=","LOG=[]; CHOSEN={}; STALL=[]\nPROG=")
rep("P(f\"   summaries {len(SUM)}\")","P(f\"   summaries {len(SUM)}  stalled cuts {STALL}\")")
rep("out=open('walk31_%s.out'%sys.argv[1],'w')","out=open('walk32_%s.out'%sys.argv[1],'w')")
open('walk32.py','w').write(s); print('walk32 written')
