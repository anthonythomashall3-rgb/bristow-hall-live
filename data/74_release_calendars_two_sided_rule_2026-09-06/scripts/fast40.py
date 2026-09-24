"""v2.6 RECORD SCRIPT — Anthony's ruling that lines may be fitted to the tightest clean value (the Michez/Sahm/SOS standard), applied to
every line except the hub's, which stays on Sahm's published 0.50 by his instruction. Two lines move, each to the SAFEST CORNER OF ITS CLEAN
PLATEAU: the vacancy 0.36 -> 0.35 (buys 1960: 153 -> 122) and the housing half 35 -> 33 log points (buys 1990: 50 -> 38 and 2007: 51 -> 17).
The four-month re-arm boundary is written 'at four months'. Everything else unchanged."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep2.py').read().split("for vac in [0.36,0.35]:")[0].replace("out=open('sweep2.out','w')","out=open('fast40.out','w')"))
V26=dict(sahm=0.50,vac=0.35,u45=0.45,low=0.25,starts=33,half=4,h1=2.0,h2=1.20)
def detail(nm,p):
    for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
        F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
        F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
        Vc=dict(name=f"vac{p['vac']}",gap=vr,line=p['vac'],pubs=VJ36['pubs']); Hc,_=mkpair(p['starts'],p['half']); Hh=mkhours(p['h1'],p['h2'])
        U=confirm_w(leg_gapx(s,p['u45'],rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapx(s,p['low'],rearm='window')+F25,[Hc],'month'); X=hub_actual(p['sahm'],vr,p['vac'])
        r=run3(f"{nm} — {tag}",{'U':U,'L':L,'X':X})
        P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"| trough date errors",[r['errs_t'].get(i) for i in range(13)])
        P("      troughs: "+" | ".join(f"{TR[i]:%Y-%m}:{[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['published']:%Y-%m-%d}" for i in range(13) if i in r['lags_t']))
detail('v2.5 (vacancy .36, starts 35)',dict(V26,vac=0.36,starts=35))
detail('v2.6 (vacancy .35, starts 33)',V26)
P("\nPLATEAU: starts 33, 32 and 31 give the IDENTICAL record; 33 is its safest corner (quiet-window margin 0.124 against 0.096 and 0.067).")
P("starts 30 and 29 buy 2007 (17 -> 4) but open 1969 twenty-one days before the peak month ends and cut the margin to 0.036 and 0.003; 28 makes a November 1984 false alarm. Not taken.")
P("vacancy 0.35, 0.34, 0.32 and 0.30 give the IDENTICAL record; 0.35 is its safest corner. 0.28 makes a March 2003 false alarm.")
out.close()
