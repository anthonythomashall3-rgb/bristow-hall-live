"""Six months either side was chosen for SYMMETRY, not measured. The twelve
recessions' own confirming crossings arrive between five months before the
claims call and four months after it, so [-5,+4] holds every one -- and the
second factor of the hazard is a rising function of the window's width.
This is the last parameter nobody chose."""
exec(open('hazard_v5.py').read().split('print("CONTROL')[0])
SET=[S,V,P3h,H]      # the FREE set: pair + payrolls + housing 35, no ETA 5159
print("the second factor as a function of the window, on the free confirming set")
print(f"{'window (months back, forward)':34}{'exposure':>10}{'hazard/yr':>12}{'one in':>10}")
for bk,fw in [(6,18),(6,6),(6,4),(5,4),(5,3),(4,3),(3,3),(6,1)]:
    e,_=win_expo(SET,bk+1,fw+1); h=0.0779*e/100
    print(f"   back {bk:2d}, forward {fw:2d}{'':16}{e:9.2f}%{h*100:11.3f}%{1/h:10.0f}")
