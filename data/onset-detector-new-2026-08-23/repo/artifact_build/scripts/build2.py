import json,os,glob,math,sys,csv,datetime as dt
sys.path.insert(0,'/tmp/rmv3')
from registry2 import REG,FAMILIES,FAMILY_LABEL
B=glob.glob('/sessions/*/mnt/RecessionMonitor 2')[0]
VAULT=os.path.join(B,'Recession Monitor V2/data_archive/current_revised_and_spatial')
YEAR=365.2425
def loadcsv(name):
    p=os.path.join(VAULT,name+'.csv')
    if not os.path.exists(p): return None
    out=[]
    with open(p) as f:
        r=csv.reader(f); hdr=next(r,None)
        if not hdr or len(hdr)<2: return None
        for row in r:
            if len(row)<2: continue
            d=row[0].strip()
            try: v=float(row[1])
            except: continue
            if len(d)==7: d=d+'-01'
            try: dt.date.fromisoformat(d)
            except: continue
            out.append((d,v))
    return sorted(out) if out else None
def d2o(s): return dt.date.fromisoformat(s).toordinal()
def transform(obs,cls,d):
    out=[]
    if cls=='lev':
        run=[]
        for dd,v in obs:
            if run:
                sv=sorted(run); n=len(sv)
                m=sv[n//2] if n%2 else (sv[n//2-1]+sv[n//2])/2
                out.append((dd,d*(v-m)))
            run.append(v)
        return out
    Hd=int(YEAR)
    for i,(dd,v) in enumerate(obs):
        t=d2o(dd)-Hd; j=i
        while j>0 and d2o(obs[j][0])>t: j-=1
        if d2o(obs[j][0])>t: continue
        lv=obs[j][1]
        if cls=='log':
            if v<=0 or lv<=0: continue
            out.append((dd,d*(math.log(v)-math.log(lv))))
        else: out.append((dd,d*(v-lv)))
    return out
def q(v,p):
    n=len(v); k=(n-1)*p; f=math.floor(k); c=min(f+1,n-1)
    return v[int(k)] if f==c else v[f]*(c-k)+v[c]*(k-f)
P={}; ATS={}; RAW={}; miss=[]
MIN_HIST=40
for sid,fam,dep,cls,d,label,live in REG:
    obs=loadcsv(sid)
    if not obs: miss.append((sid,'not_in_vault',0)); continue
    a=transform(obs,cls,d)
    vals=sorted(x for _,x in a[:-1])
    if len(vals)<MIN_HIST: miss.append((sid,'insufficient_admissible_history',len(vals))); continue
    q50=q(vals,0.50); q75=q(vals,0.75); spread=q(vals,0.90)-q(vals,0.10)
    if q75-q50<=max(1e-12,1e-6*abs(spread or 1.0)):
        miss.append((sid,'degenerate_percentile_scale',len(vals))); continue
    ATS[sid]=a; RAW[sid]=obs
    P[sid]={'family':fam,'dep':dep,'cls':cls,'d':d,'label':label,'live':live,
            'q50':q50,'q75':q75,'n_hist':len(vals),'first':obs[0][0],'last':obs[-1][0],
            'n_obs':len(obs),'latest_value':obs[-1][1],'latest_a':a[-1][1],
            'S_latest':max(0.0,(a[-1][1]-q50)/(q75-q50))}
    # live-recombination references: what the browser needs to turn a fresh
    # current value into an adverse measurement without recomputing history
    if live:
        if cls=='lev':
            sv=sorted(v for _,v in obs[:-1]); n=len(sv)
            P[sid]['prior_median']=sv[n//2] if n%2 else (sv[n//2-1]+sv[n//2])/2
        else:
            t=d2o(obs[-1][0])-int(YEAR); j=len(obs)-1
            while j>0 and d2o(obs[j][0])>t: j-=1
            P[sid]['lag_value']=obs[j][1]; P[sid]['lag_date']=obs[j][0]
        P[sid]['live_unit_check']={'vault_last':obs[-1][1],'vault_last_date':obs[-1][0]}
print('admitted',len(P),'abstained',len(miss))
for m in miss: print('   ',m)
json.dump({'params':P,'missing':miss},open('/tmp/rmv3/params_stage1.json','w'))
json.dump(ATS,open('/tmp/rmv3/ats.json','w'))
json.dump(RAW,open('/tmp/rmv3/raw.json','w'))
