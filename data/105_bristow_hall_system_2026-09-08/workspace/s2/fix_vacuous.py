# fix_vacuous.py - Rule Zero, 11 September 2026. The v3.29 documents said the sudden stop's no-false-alarm test was
# "nearly vacuous for the datum". s2/q40.py shows that is wrong: since 1948 the market gate alone held in nine episodes,
# three of them outside any recession (the October-November 1987 crash), and the claims week alone fires eleven times
# with five outside a recession window; the conjunction fires twice since 1967 and never outside. Mode 'list' prints
# every occurrence with its context; mode 'apply' makes the replacements in REPL below.
import sys,os,glob
MODE=sys.argv[1] if len(sys.argv)>1 else 'list'
ROOTS=[os.path.expanduser('~/Projects/Recession Papers'),os.path.expanduser('~/Projects/Onset Detector Data/105_bristow_hall_system_2026-09-08'),os.path.expanduser('~/Projects/Onset Detector Data/108_high_frequency_speed_2026-09-10')]
FILES=[]
for r in ROOTS:
    for p in glob.glob(os.path.join(r,'**','*.md'),recursive=True):
        if 'projects-old' in p or 'bristow-hall/' in p: continue
        try: t=open(p).read()
        except Exception: continue
        if 'vacuous' in t: FILES.append(p)
if MODE=='list':
    for p in FILES:
        t=open(p).read(); print('='*100); print(p)
        i=0
        while True:
            i=t.find('vacuous',i)
            if i<0: break
            print('---'); print(repr(t[max(0,i-700):i+700])); i+=7
    print('\nfiles:',len(FILES))
