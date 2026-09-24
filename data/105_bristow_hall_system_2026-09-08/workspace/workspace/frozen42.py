import sys,pickle
sys.argv=['frozen42.py','1962','2026','m42']
src=open('walk42.py').read().split('# ---- the walk itself')[0]
exec(src)
p=pickle.load(open('cache/w42_carry.pkl','rb')); print('walk42 end lines:',{k:p[k] for k in ('ic','u45','low','look','vl','hline','spr','cD','cs','sahm','wline','wline2','bshare')})
r,t=build_v(p)
pk=[(x['published'].strftime('%Y-%m-%d'),x['leg']) for x in t if x['kind']=='peak' and x['published'].year>=1948]
tr=[(x['published'].strftime('%Y-%m-%d'),x['leg']) for x in t if x['kind']=='trough' and x['published'].year>=1948]
print('frozen peaks 1948-2026:',pk); print('frozen troughs:',tr); print('count',len(pk),len(tr))
