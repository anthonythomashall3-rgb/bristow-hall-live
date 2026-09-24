exec(open('union.py').read().split('S=hits(sahm,0.5)')[0])
S=hits(sahm,0.5); V=hits(vac,0.36); P=hits(pay,0.3)
awh6=(FP['AWHMAN'].rolling(6).max()/FP['AWHMAN']-1)*100
for line in (2.5,3.0,3.5,4.0):
    A=hits(awh6,line)
    w0,_=win_expo([S,V,P]); w1,n=win_expo([S,V,P,A]); wa,_=win_expo([A])
    print(f"hours off 6-month max >= {line}%:  hours alone {wa:5.2f}%   pair+payrolls {w0:5.2f}%   with hours {w1:5.2f}%   ({n} quiet months)")
