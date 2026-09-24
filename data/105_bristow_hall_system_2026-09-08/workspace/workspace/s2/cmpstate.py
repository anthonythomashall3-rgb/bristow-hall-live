"""NaN-aware comparison of two bhs_state.json files (built_at ignored): python3 s2/cmpstate.py a.json b.json"""
import json,math,sys
def load(p):
    d=json.load(open(p)); d.pop('built_at',None); d.pop('built',None); return d
def diff(x,y,path,out):
    if len(out)>40: return
    if isinstance(x,float) and isinstance(y,float) and math.isnan(x) and math.isnan(y): return
    if type(x)!=type(y): out.append(path+': type'); return
    if isinstance(x,dict):
        for k in sorted(set(x)|set(y),key=str):
            if k not in x or k not in y: out.append(path+'/'+str(k)+': missing'); continue
            diff(x[k],y[k],path+'/'+str(k),out)
    elif isinstance(x,list):
        if len(x)!=len(y): out.append(path+': len %d vs %d'%(len(x),len(y))); return
        for i,(a,b) in enumerate(zip(x,y)): diff(a,b,path+'[%d]'%i,out)
    elif x!=y: out.append(path+': '+(repr(x)[:50]+' vs '+repr(y)[:50]))
a=load(sys.argv[1]); b=load(sys.argv[2]); out=[]; diff(a,b,'',out)
print('differences:',len(out)); print('\n'.join(out[:30]))
