from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur, spl
import itertools
sys.path.insert(0,W+'/lab/slack'); from objects import load
v=-load()['-vacancy rate']; m3=v.rolling(3).mean(); V312=(m3.shift(1).rolling(12).max()-m3).dropna()
KJHS={k:TLG[k] for k in 'KJHS'}
def summ(turns):
    r=score13(turns); lp=list(r['lags_p'].values())
    return len(lp),len(r['other']),np.median(lp),max(lp),sum(1 for l in lp if l<=31)
print("PLATEAU: core rule (U line x vacancy line, (2,6) form), hub = Sahm 0.50 & vacancy; U confirmed by V|H|P; closers K,J,H,S")
print(f"{'U line':>7}"+''.join(f"{'vac '+str(vl):>22}" for vl in [0.30,0.36,0.42,0.50]))
for ul in [0.40,0.45,0.50,0.55,0.60,0.70]:
    row=f"{ul:>7.2f}"
    for vl in [0.30,0.36,0.42,0.50]:
        SEC['V']=dict(name='vacancy',gap=vr,line=vl,pub_day=30)
        X=leg_X2(vac=vr,vac_line=vl); U=leg_U(s_cur,line=ul)
        n,oth,med,wst,w31=summ(chron({'U':U,'X':X},KJHS,['V','H','P']))
        row+=f"   {n:2d}/13 o{oth} m{med:4.0f} w{wst:4d}"
    print(row)
SEC['V']=dict(name='vacancy',gap=vr,line=0.36,pub_day=30)
print("\nHUB with Sahm's own form on vacancies, (3,12) at 0.60 (Michaillat-Saez mirror), U 0.50:")
SEC['V']=dict(name='vacancy312',gap=V312,line=0.60,pub_day=30)
X=leg_X2(vac=V312,vac_line=0.60); U=leg_U(s_cur,0.50)
for nm,cf in [('V312 only',['V']),('V312|H|P',['V','H','P'])]:
    r=score13(chron({'U':U,'X':X},KJHS,cf)); lp=[r['lags_p'].get(i) for i in range(13)]
    print(f"  {nm:12}",[('-' if l is None else l) for l in lp],'other',r['other'])
SEC['V']=dict(name='vacancy',gap=vr,line=0.36,pub_day=30)
print("\nSAHM line sensitivity in the hub (U 0.50, vac 0.36): Sahm 0.45 / 0.50 / 0.55")
for sl in [0.45,0.50,0.55]:
    X=leg_X2(sahm_line=sl); r=score13(chron({'U':leg_U(s_cur),'X':X},KJHS,['V','H','P'])); lp=[r['lags_p'].get(i) for i in range(13)]
    print(f"  Sahm {sl:.2f}",[('-' if l is None else l) for l in lp],'other',r['other'])
