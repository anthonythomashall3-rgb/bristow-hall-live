"""Final refinement around k=3 (three-month housing mean), rate-half minimum window 18: the starts line at one-point steps with margins,
and whether a longer low-branch lookback now buys 2007 on first prints for free."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep5.py').read().split('P("--- rate-half minimum window 18')[0].replace("out=open('sweep5.out','w')","out=open('sweep6.out','w')"))
P("--- k=3, minw 18, starts line at one-point steps ---")
for st in [33,32,31,30,29,28,27,26]: go2(f'k=3 minw18 starts {st}',st,3,18)
P("\n--- k=3 minw18 starts 31 / 29, low-branch lookback (does it buy 2007 on first prints?) ---")
for st in [31,29]:
    for lk in [52,65,78,91,104]:
        ok=go(f'k=3 minw18 starts {st} look25 {lk}',starts=st,k=3,minw=18,look25=lk)
P("\n--- and the 0.45 branch lookback in the new configuration ---")
for st in [31]:
    for lk in [52,78,104]: go(f'k=3 minw18 starts {st} look45 {lk}',starts=st,k=3,minw=18,look45=lk)
out.close()
