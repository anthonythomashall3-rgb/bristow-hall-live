"""The trough clause at the window's opening edge: four abstention readings measured on the nine.

channel_trough abstains when the smoothed level's minimum sits at the window's CLOSING month (still
falling); channel_peak abstains at both edges.  On real-time windows that open just after the
previous trough, a channel that did not fall in the new contraction carries the previous
contraction's residual deviation at the opening month and votes that earlier trough (real
consumption on the 1 November 1984 vintage dates the 1981-82 trough at May 1980,
final_date_rt_windows.log).  Readings (bristow_rule_v3.TROUGH_EDGE_ABSTAIN):
  end     shipped: closing edge only
  both    also abstain when the level's low is the opening month
  dpeak   also abstain when the deviation statistic's maximum is the opening month
  either  either of the two
  joint   both at once
Scored on the nine chronologies' monthly ends (monthly_ends_all.nine); the four held-out are run by
setting BR_TROUGH_EDGE in the environment of rulings_heldout.py.  Run 3 September 2026.  The
refinement is left UNBOUNDED here (REFINE_BOUNDED=False) so that the four readings are measured
alone, as they were before 'joint' and the bounded refinement were adopted; refine_bounded_test.py
measures the combinations.
"""
import sys,warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import bristow_rule_v3 as B, monthly_ends_all as M
B.REFINE_BOUNDED=False
def tally(rows):
    e=[x for c,k,x,w in rows if not w and x is not None]; return (sum(v==0 for v in e),sum(abs(v)<=1 for v in e),sum(abs(v)<=3 for v in e),len(e))
res={}
for mode in ('end','both','dpeak','either','joint'):
    B.TROUGH_EDGE_ABSTAIN=mode; P,T=M.nine(); res[mode]=(P,T)
    print(f'{mode:7s} peaks exact/w1/w3/n {tally(P)}   troughs {tally(T)}',flush=True)
a=res['end']
for mode in ('both','dpeak','either','joint'):
    b=res[mode]; print(f'\n{mode}: ends that move (shipped -> {mode})')
    for kind,(ra,rb) in (('peak',(a[0],b[0])),('trough',(a[1],b[1]))):
        for (c,k,ea,w),(c2,k2,eb,w2) in zip(ra,rb):
            if ea!=eb: print(f'  {kind:6s} {c:26s} {k[:7]}  {ea!s:>5} -> {eb!s:<5}')
