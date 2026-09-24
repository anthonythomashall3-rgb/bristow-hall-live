import sys,pickle
sys.argv=['pullback2.py','1962','2026','m41']
exec(open('pullback.py').read().split("base=calls(p0)")[0])
base=calls(p0)
for name,q in [('u45 0.55 + ic 50',dict(p0,u45=0.55,ic=50)),('u45 0.55 + ic 50 + look 78',dict(p0,u45=0.55,ic=50,look=78)),('u45 0.55 + ic 60 + look 78',dict(p0,u45=0.55,ic=60,look=78)),('u45 0.55 + ic 50 + low 0.15',dict(p0,u45=0.55,ic=50,low=0.15))]:
    c=calls(q); dp=[(a,b) for a,b in zip(base[0],c[0]) if a!=b]; dt=[(a,b) for a,b in zip(base[1],c[1]) if a!=b]
    same=(len(c[0])==len(base[0]) and len(c[1])==len(base[1]))
    print('%-30s'%name,'same count' if same else 'DIFFERENT COUNT %d/%d peaks %d/%d troughs'%(len(c[0]),len(base[0]),len(c[1]),len(base[1])),'| peak changes',dp,'| trough changes',dt)
    if not same: print('   peaks:',c[0]); print('   troughs:',c[1])
m4=ICfp.dropna().rolling(4).mean(); ic=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
print('claims object Feb-May 2001 (week, reading):',[(w.strftime('%m-%d'),round(float(v),1)) for w,v in ic['2001-02':'2001-05'].items()])
