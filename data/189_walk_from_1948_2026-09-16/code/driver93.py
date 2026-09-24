"""One preamble, two walks: (A) walk 93 with the hold grid restricted to [0] == walk 90 exactly (same keys, same
objective except the second key, which cannot change a choice when hold is fixed... it CAN: the [-45,-1] count
is a new second key. So run A is 'walk 90 under walk 93's objective', reported as such); (B) walk 93 proper."""
import sys, os, io, contextlib, time, pickle
os.chdir('/home/claude/ws'); sys.path.insert(0,'/home/claude/ws')
src=open('walk93.py').read()
_MARK="# ---- the walk "+"itself"
tail_line="exec(open('walk39.py').read().split(_MARK)[1].split(\"\\n\", 1)[1])"
assert src.count(tail_line)==1, 'tail exec line not found'
head=src.replace(tail_line,"")
# run B first is wrong: A must run first so its hold=0 summaries seed B. But both share SUM in memory.
sys.argv=['walk93.py','1962','2026','w93']
t0=time.time()
exec(compile(head,'walk93_head','exec'))
print('preamble %.0f s'%(time.time()-t0),flush=True)
tail=open('walk39.py').read().split(_MARK)[1].split("\n",1)[1]
def run(var, hold_grid):
    global GRID, GD, NAMES, out, SUMF
    GRID=[(n,(hold_grid if n=='hold' else g)) for n,g in GRID]
    GD=dict(GRID); NAMES=[n for n,_ in GRID]
    sys.argv=['walk93.py','1962','2026',var]
    out=open('walk93_%s_1962.out'%var,'w'); SUMF='cache/%s_sum.pkl'%var
    for f in ('cache/%s_prog.pkl'%var,'cache/%s_carry.pkl'%var):
        if os.path.exists(f): os.remove(f)
    t=time.time(); exec(compile(tail,'walk_tail','exec'),globals()); print(var,'done %.0f s'%(time.time()-t),flush=True)
run('w93a',[0])
run('w93',[0,15,30,45])
