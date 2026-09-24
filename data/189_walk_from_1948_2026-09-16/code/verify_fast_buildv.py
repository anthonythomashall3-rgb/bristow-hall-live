import sys, os, io, contextlib, time, pickle, random
os.chdir('/home/claude/ws'); sys.path.insert(0,'/home/claude/ws')
src=open('walk91.py').read()
sys.argv=['walk91.py','2027','2026','wverify']
t0=time.time(); buf=io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src,'walk91','exec'))
print('preamble %.0f s'%(time.time()-t0), flush=True)
ref=pickle.load(open('cache/w81_sum.pkl','rb'))
SUM.clear()
keys=list(ref.keys()); random.seed(7); random.shuffle(keys); keys=keys[:int(os.environ.get('N','120'))]
bad=0; t1=time.time(); times=[]
for i,k in enumerate(keys):
    p=dict(zip(NAMES,k)); p.update({n:v for n,v in BASE15.items() if n not in p})
    t=time.time(); s=summary(p); times.append(time.time()-t)
    r=ref[k]
    same = (s['lags']==r['lags'] and s['early']==r['early'] and list(s['fa'])==list(r['fa']) and s['tro']==r['tro'] and s['pair']==r['pair'] and s['opens']==r['opens'])
    if not same:
        bad+=1; print('MISMATCH',k, {kk:(s[kk],r[kk]) for kk in s if s[kk]!=r[kk]}, flush=True)
    if (i+1)%20==0: print('%d/%d checked, %d mismatches, mean %.2fs (last 20: %.2fs)'%(i+1,len(keys),bad,sum(times)/len(times),sum(times[-20:])/20), flush=True)
print('DONE checked',len(keys),'mismatches',bad,'total %.0fs'%(time.time()-t1), 'memo entries',len(_MEMO))
