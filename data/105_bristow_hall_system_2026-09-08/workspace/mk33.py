# walk33 = walk32 with walk30's day objective back: one clock for the chronology, the lines chosen by speed in days
s=open('walk32.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 32 - ONE CLOCK, THE MENU THAT SURVIVES IT (collection 104, 8 September 2026).','"""WALK 33 - ONE CLOCK FOR THE CHRONOLOGY, THE LINES CHOSEN BY SPEED (collection 104, 8 September 2026). walk32 with\nwalk30\'s objective back: peaks (calls more than thirty-one days after the peak month ended, median days, mean days),\ntroughs (closes outside 0 to 31 days, median and mean of the absolute days). The month errors are reported, not\noptimised. walk32\'s month objective, being coarse, let the walk sit on lines that speed had moved it off in walk30,\nand one of them called August 2002; this walk tests whether the one-clock chronology can be had at walk30\'s choices.\n\nWALK 32 - ONE CLOCK, THE MENU THAT SURVIVES IT (collection 104, 8 September 2026).')
rep("        return (sum(1 for x in m if abs(x)>1), float(np.median([abs(x) for x in m])), float(np.mean([abs(x) for x in m])),\n                sum(1 for x in d if x>31), float(np.median(d)), float(np.mean(d)))\n    a=side(v)\n    if not w: return a+(0,0.0,0.0,0,0.0,0.0)\n",
    "        return (sum(1 for x in d if x>31), float(np.median(d)), float(np.mean(d)))\n    def side_t(z):\n        d=[l for _,l in z]\n        return (sum(1 for x in d if x>31 or x<0), float(np.median([abs(x) for x in d])), float(np.mean([abs(x) for x in d])))\n    a=side(v)\n    if not w: return a+(0,0.0,0.0)\n")
rep("    return a+side(w)","    return a+side_t(w)")
rep("out=open('walk32_%s.out'%sys.argv[1],'w')","out=open('walk33_%s.out'%sys.argv[1],'w')")
open('walk33.py','w').write(s); print('walk33 written')
