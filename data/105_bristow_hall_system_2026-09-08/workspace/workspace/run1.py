from mini import *
print("== reproduction of the frozen v8 (ABCMU; S,V,H,P; K,J,H) on 12 + Paper 1's 2024 ==")
r=rep("v8 frozen", chron({k:PL[k] for k in 'ABCMU'},{k:TLG[k] for k in 'KJH'},['S','V','H','P']))
r=rep("v8 + S closer", chron({k:PL[k] for k in 'ABCMU'},{k:TLG[k] for k in 'KJHS'},['S','V','H','P']))
print("\n== the minimal conjunctions, all 1948-on legs, closers K,J,H ==")
for pk in ['U','C','UC','B','BU','BC','BCU','A','M','AM','AC','ACU','ACM','AU']:
    for cf in [['S'],['S','V'],['V'],['S','V','H','P']]:
        rep(f"{pk} + {'|'.join(cf)}", chron({k:PL[k] for k in pk},{k:TLG[k] for k in 'KJH'},cf))
