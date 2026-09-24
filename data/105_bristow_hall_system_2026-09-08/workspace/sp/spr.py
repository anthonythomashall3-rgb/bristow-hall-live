print('GSP index freq:',GSP.index[:3].tolist(),GSP.index[-1]); 
for a,b in [('2000-06','2001-06'),('2007-06','2008-06'),('2019-10','2020-06')]:
    s=GSP[a:b]; print(a,b,'max %.2f at %s'%(s.max(),s.idxmax().date()),'| values:',{k.strftime('%Y-%m-%d'):round(float(v),2) for k,v in s.iloc[::4].items()})
print([k for k in globals() if 'cp' in k.lower() or 'spread' in k.lower() or 'bill' in k.lower()][:30])
