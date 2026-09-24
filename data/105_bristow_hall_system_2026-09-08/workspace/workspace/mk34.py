# walk34 = walk30 with C's hold removed, the chronology dated on the firing month, the lines chosen as in walk30
s=open('walk30.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED','"""WALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30 (collection 104, 8 September 2026). Anthony: when\nthe rule fires, that is the date. Every call in the diary is dated the calendar month of its firing day, peaks and\ntroughs alike; closer C\'s hold to the last day of the month it used to name is removed, so C fires the day its\nevidence arrives. Inside the machine nothing else changes: the confirmation windows, the matching of calls to\nrecessions and the false-alarm test still run on the data months (that is how the rule decides whether to speak,\nnot what it says), the walk still chooses every line by the day-count objective of walk30, and the trough clause\nis the declared acceptance in days (a ratified trough may not be closed more than thirty-one days before its month\nended; the old test on the named month is gone because there is no named month). walk31 to walk33 tried a month\nobjective and a re-dated matching window; both let the walk sit on lines walk30 had moved off and each produced one\nfalse alarm (August 2002; November 1984) - recorded in the version note, refused. A cut with no clean point keeps\nthe last configuration and goes on logging.\n\nWALK 30 - WALK 29 WITH THE RUN FIXED AT THREE FALLING WEEKS, NOT WALKED')
rep("        pub=max(pub,dated+pd.offsets.MonthEnd(0))\n        calls.append((pub,dated)); last_=t","        calls.append((pub,dated)); last_=t   # one clock: no hold")
rep("        if lg<-31 or abs(er)>1: return None                # early by more than a month, or dated more than a month out (declared 8 September 2026)\n",
    "        if lg<-31: return None                             # the declared acceptance, in days; there is no named month to test\n")
rep("    if clean(p,cut,ks,kt) is None: continue\n",
    "    if clean(p,cut,ks,kt) is None:\n        STALL.append(Y); p=dict(last) if last is not None else dict(p)   # no clean point at this cut: the rule keeps its last configuration\n")
rep("LOG=[]; CHOSEN={}\nPROG=","LOG=[]; CHOSEN={}; STALL=[]\nPROG=")
rep("            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))\n",
    "            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',pd.Timestamp(x['published'].year,x['published'].month,1),x['leg']))   # ONE CLOCK\n")
rep("P(f\"   summaries {len(SUM)}\")","P(f\"   summaries {len(SUM)}  stalled cuts {STALL}\")")
rep("out=open('walk30_%s.out'%sys.argv[1],'w')","out=open('walk34_%s.out'%sys.argv[1],'w')")
open('walk34.py','w').write(s); print('walk34 written')
