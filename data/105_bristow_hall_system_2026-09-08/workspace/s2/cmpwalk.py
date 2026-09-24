# cmpwalk.py - compare two walks' chosen lines at every cut, their walk-end lines and their diaries. Run: python3 s2/cmpwalk.py w50 w51
import sys,pickle
a,b=sys.argv[1],sys.argv[2]
ca=pickle.load(open(f'cache/{a}_carry.pkl','rb')); cb=pickle.load(open(f'cache/{b}_carry.pkl','rb'))
print('walk-end lines differ:',{k:(ca.get(k),cb.get(k)) for k in set(ca)|set(cb) if ca.get(k)!=cb.get(k)} or 'none')
pa=pickle.load(open(f'cache/{a}_prog.pkl','rb')); pb=pickle.load(open(f'cache/{b}_prog.pkl','rb'))
xa,xb=pa['chosen'],pb['chosen']
d=[(c.year,{k:(xa[c].get(k),xb[c].get(k)) for k in set(xa[c])|set(xb[c]) if xa[c].get(k)!=xb[c].get(k)}) for c in sorted(set(xa)&set(xb)) if xa[c]!=xb[c]]
print('cuts',len(xa),len(xb),'| cuts where the chosen lines differ:',d or 'none')
la=sorted(pa['log'],key=lambda z:z[0]); lb=sorted(pb['log'],key=lambda z:z[0])
print('diary entries',len(la),len(lb))
for x,y in zip(la,lb):
    if x!=y: print('  differs:',[str(v)[:10] for v in x],'->',[str(v)[:10] for v in y])
