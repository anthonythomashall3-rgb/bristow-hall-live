"""Fast form v2 final: U45 re-arms at a new 52-week low; U-low re-arms when an unconfirmed proposal's window has closed; no breadth object."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast17.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast17.out','w')","out=open('fast18.out','w')"))
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori lines (vacancy .36, Sahm .50)',V36,0.50),('construction-grade (vacancy .30, Sahm .43)',V30,0.43)]:
        for fhr in ['zero','window']:
            FHx=[x for x in leg_gap_mx(gm,0.45,rearm=fhr) if x[1]<pd.Timestamp('1971-01-01')]
            U=confirm(leg_gapx(s,0.45,rearm='zero')+FHx,[Vc,HpX,Pp]); L=confirm(leg_gapx(s,0.25,rearm='window'),[HpX]); X=hub(sl,vr,Vc['line'])
            run2(f"v2 {lab_}; FH re-arm {fhr}",{'U':U,'L':L,'X':X})
out.close()
