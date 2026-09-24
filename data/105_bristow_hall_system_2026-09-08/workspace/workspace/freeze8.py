"""Route v8 -- payrolls dropped at zero cost. Twelve objects to eleven."""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
AWH=first_prints('AWHMAN'); ND=first_prints('NDMANEMP')
f12=lambda v,l:(v.rolling(12).max()/v-1)*100/l; f3=lambda v,l:(-(v/v.shift(3)-1)*100)/l
P1=pd.concat([f12(AWH,2.0),f3(ND,1.20)],axis=1).min(axis=1).dropna()
H1=(P1>=1.0).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
c1,_=win_expo([S,V],7,1); print(f"control {c1:.2f}% (published 7.39)")
print(f"{'confirming set':44}{'expo (6,4)':>12}{'hazard/yr':>11}{'one in':>8}")
for nm,parts in [("v7  Sahm+vacancy+payrolls+housing+pair",[S,V,P3h,H,H1]),
                 ("v8  Sahm+vacancy+housing+pair  (no payrolls)",[S,V,H,H1])]:
    e,_=win_expo(parts,7,5); hz=0.0779*e/100; print(f"{nm:44}{e:11.2f}%{hz*100:10.3f}%{1/hz:8.0f}")
