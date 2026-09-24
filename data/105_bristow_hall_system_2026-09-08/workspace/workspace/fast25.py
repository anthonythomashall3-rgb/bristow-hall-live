"""v2.2 without the hours x nondurable pair (four series): what the pair buys."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast24.py').read().split("RES={}")[0].replace("out=open('fast24.out','w')","out=open('fast25.out','w')"))
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); L3=confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3],'month')
        run3(f"v2.2 {lab_} (six series)",{'U':confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Ppx],'month'),'L':L3,'X':X})
        run3(f"v2.2-lite {lab_} (FOUR series: no hours pair)",{'U':confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'),'L':L3,'X':X})
for vl in [0.36,0.30]:
    eV,_=win_expo([hits(vr,vl)]); eVP,_=win_expo([hits(vr,vl),hits(P1x,1.0)]); P(f"vacancy {vl}: window exposure V alone {eV:.2f}% vs V|P {eVP:.2f}%")
out.close()
