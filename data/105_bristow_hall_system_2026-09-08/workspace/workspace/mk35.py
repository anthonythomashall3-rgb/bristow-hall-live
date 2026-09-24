# walk35 = walk34 with the month error first in the objective (accuracy first, then days), machinery unchanged
s=open('walk34.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30','"""WALK 35 - ONE CLOCK, ACCURACY FIRST (collection 104, 8 September 2026). walk34 with the objective reordered: on each\nside the error in months of the firing month comes first (turns off by more than a month, median absolute error,\nmean absolute error), the day terms of walk30 after it. The machinery, the matching windows, the false-alarm test\nand the trough acceptance are walk34\'s. This is the test of whether a causal rule can be made to speak in the\ncommittee\'s own month without buying a false alarm.\n\nWALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30')
rep("       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}\n",
    "       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}\n    s['errp']={i:(pb.year-PK[i].year)*12+pb.month-PK[i].month for i,pb in s['opens'].items()}   # one clock: months\n")
rep("    v=[s['lags'][j] for j in ks if j in s['lags']]\n    if len(v)!=len(ks): return None\n",
    "    v=[s['lags'][j] for j in ks if j in s['lags']]\n    if len(v)!=len(ks): return None\n    if any(j not in s['errp'] for j in ks): return None\n    v=[(s['errp'][j],s['lags'][j]) for j in ks]         # (error in months of the firing month, days after the month ended)\n")
rep("        if lg<-31: return None                             # the declared acceptance, in days; there is no named month to test\n        w.append(lg)",
    "        if lg<-31: return None                             # the declared acceptance, in days; there is no named month to test\n        w.append(((pub_.year-TR[i].year)*12+pub_.month-TR[i].month,lg))")
rep("    a=(sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))\n    if not w: return a+(0,0.0,0.0)\n",
    "    def side(z):\n        m=[e for e,_ in z]; d=[l for _,l in z]\n        return (sum(1 for x in m if abs(x)>1), float(np.median([abs(x) for x in m])), float(np.mean([abs(x) for x in m])),\n                sum(1 for x in d if x>31), float(np.median(d)), float(np.mean(d)))\n    def side_t(z):\n        m=[e for e,_ in z]; d=[l for _,l in z]\n        return (sum(1 for x in m if abs(x)>1), float(np.median([abs(x) for x in m])), float(np.mean([abs(x) for x in m])),\n                sum(1 for x in d if x>31 or x<0), float(np.median([abs(x) for x in d])), float(np.mean([abs(x) for x in d])))\n    a=side(v)\n    if not w: return a+(0,0.0,0.0,0,0.0,0.0)\n")
rep("    return a+(sum(1 for x in w if x>31 or x<0), float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))",
    "    return a+side_t(w)")
rep("out=open('walk34_%s.out'%sys.argv[1],'w')","out=open('walk35_%s.out'%sys.argv[1],'w')")
open('walk35.py','w').write(s); print('walk35 written')
