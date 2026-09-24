"""Bounded refinement (the refinement search kept inside the clause's window) measured on the nine, alone and
with the opening-edge abstention (3 September 2026).  Four settings: shipped-through-v31 (unbounded, closing edge
only), bounded alone, bounded with 'dpeak', and 'dpeak' alone; 'joint' gives the same ends as 'dpeak' on the nine
(edge_abstain_test.py) and is what shipped.  Output refine_bounded_test.log."""
import sys,warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import bristow_rule_v3 as B, monthly_ends_all as M
def tally(rows):
    e=[x for c,k,x,w in rows if not w and x is not None]; return (sum(v==0 for v in e),sum(abs(v)<=1 for v in e),sum(abs(v)<=3 for v in e),len(e))
res={}
for name,(bounded,edge) in {'shipped':(False,'end'),'bounded':(True,'end'),'bounded+dpeak':(True,'dpeak'),'dpeak':(False,'dpeak'),'bounded+joint':(True,'joint')}.items():
    B.REFINE_BOUNDED=bounded; B.TROUGH_EDGE_ABSTAIN=edge; P,T=M.nine(); res[name]=(P,T)
    print(f'{name:14s} peaks exact/w1/w3/n {tally(P)}   troughs {tally(T)}',flush=True)
a=res['shipped']
for name in ('bounded','bounded+dpeak','dpeak','bounded+joint'):
    b=res[name]; print(f'\n{name}: ends that move')
    for kind,(ra,rb) in (('peak',(a[0],b[0])),('trough',(a[1],b[1]))):
        for (c,k,ea,w),(c2,k2,eb,w2) in zip(ra,rb):
            if ea!=eb: print(f'  {kind:6s} {c:26s} {k[:7]}  {ea!s:>5} -> {eb!s:<5}')
