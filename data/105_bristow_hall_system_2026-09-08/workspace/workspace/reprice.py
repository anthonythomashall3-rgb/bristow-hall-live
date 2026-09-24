"""Every Rule 21 verdict this route has made was priced on a window reaching
ONE MONTH forward. The window is now six months forward. Reprice all of them."""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
print(f"{'confirming set':52}{'(7,1) old':>11}{'(7,7) NOW':>11}{'rise':>8}")
sets=[("Sahm 0.50 alone",[S]),
      ("Sahm + vacancy 0.36  (the shipped pair)",[S,V]),
      ("+ payrolls 3-month 0.30%",[S,V,P3h]),
      ("+ ETA 5159 breadth 40%",[S,V,P3h,E5]),
      ("+ housing 35 x rate 0.20  (v5, shipped)",[S,V,P3h,E5,H]),
      ("   instead: + housing 30 x rate 0.20",None),
      ("+ factory hours 2.5%  (refused)",[S,V,P3h,E5,H,A])]
lh2=np.log(FP['HOUST'])*100
P30=pd.concat([(lh2.rolling(12).max()-lh2.rolling(2).mean())/30.0,
               (first_prints('UNRATE')-first_prints('UNRATE').rolling(12).min())/0.20],axis=1).min(axis=1).dropna()
H30=hits(P30,1.0)
base=None
for nm,parts in sets:
    if parts is None: parts=[S,V,P3h,E5,H30]
    a,_=win_expo(parts,7,1); b,_=win_expo(parts,7,7)
    mark='' if base is None else f"{b/base:7.3f}x"
    print(f"{nm:52}{a:10.2f}%{b:10.2f}%{mark:>8}")
    if nm.startswith("Sahm + vacancy"): base=b
print("\nEACH OBJECT ON ITS OWN, and what it adds to the shipped pair on the CORRECTED window")
pair,_=win_expo([S,V],7,7)
print(f"{'object':40}{'alone':>9}{'pair + it':>11}{'adds':>8}")
for nm,h in [("payrolls 3-month 0.30%",P3h),("ETA 5159 breadth 40%",E5),
             ("housing 35 x rate 0.20",H),("housing 30 x rate 0.20",H30),
             ("factory hours 2.5%",A)]:
    a,_=win_expo([h],7,7); c,_=win_expo([S,V,h],7,7)
    print(f"{nm:40}{a:8.2f}%{c:10.2f}%{c-pair:+7.2f}")
