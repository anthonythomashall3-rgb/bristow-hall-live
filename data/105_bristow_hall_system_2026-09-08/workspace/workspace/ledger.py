"""The Rule 21 ledger, on the verified namespace -- the one whose control
reproduces the route's own published 7.39 and 12.47 per cent exactly."""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
c1,_=win_expo([S,V],7,1); c2,_=win_expo([S,V,P3h,A],7,1)
print(f"CONTROL at the published window (6 back, 30 days fwd): pair {c1:.2f}% (published 7.39), "
      f"pair+payrolls+hours {c2:.2f}% (published 12.47)")
print(f"\n{'confirming set':46}{'(6,1) old':>11}{'(6,4) NOW':>11}{'hazard/yr':>11}{'one in':>9}")
for nm,parts in [("Sahm 0.50 alone",[S]),
                 ("Sahm + vacancy 0.36",[S,V]),
                 ("+ payrolls 3-month 0.30%",[S,V,P3h]),
                 ("+ housing 35 x rate 0.20   SHIPPED v6",[S,V,P3h,H]),
                 ("+ ETA 5159 breadth 40%     withdrawn",[S,V,P3h,H,E5]),
                 ("+ factory hours 2.5%       refused",[S,V,P3h,H,A])]:
    a,_=win_expo(parts,7,1); b,_=win_expo(parts,7,5); h=0.0779*b/100
    print(f"{nm:46}{a:10.2f}%{b:10.2f}%{h*100:10.3f}%{1/h:9.0f}")
