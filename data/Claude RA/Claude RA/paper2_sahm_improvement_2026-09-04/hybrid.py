import core, gen
ON=gen.build(3,6,15,'abs'); EN=gen.build(3,3,12,'abs')
Emap={v:(m,x) for v,m,x in EN}
THR=0.46
eps=[];cur=None
for v,m,x in ON:
    if x is None: continue
    ex=Emap.get(v,(None,None))[1]
    if cur is None:
        if x>=THR-1e-9: cur=dict(on=v,onm=m,mx=ex,mxm=m,end=None,endm=None,rev=0)
    else:
        if ex is not None and (cur['mx'] is None or ex>cur['mx']):
            if cur['end']: cur['rev']+=1; cur['end']=None
            cur['mx'],cur['mxm']=ex,m
        elif cur['end'] is None and ex is not None:
            cur['end'],cur['endm']=v,cur['mxm']
        if x<THR-1e-9 and cur['end']: eps.append(cur); cur=None
if cur: eps.append(cur)
NBER={"1960-04":"1961-02","1969-12":"1970-11","1973-11":"1975-03","1980-01":"1980-07","1981-07":"1982-11",
"1990-07":"1991-03","2001-03":"2001-11","2007-12":"2009-06","2020-02":"2020-04","2024-04":"2024-08"}
def mo(s):
    y,m=map(int,s.split('-')[:2]); return y*12+m
print("HYBRID: onset = 3-month mean vs min of prior fifteen 6-month means, threshold 0.46")
print("        end   = Bristow Rule on the original Sahm indicator (3/12)")
print(f"{'episode onset':16}{'peak lag':>9}   {'trough dated':>12} {'confirmed':>12} {'trough err':>11}  rev")
for e in eps:
    tgt=[(p,t) for p,t in NBER.items() if mo(p)-6<=mo(e['on'][:7])<=mo(t)+6]
    if tgt:
        p,t=tgt[0]; lag=mo(e['on'][:7])-mo(p); err=mo(e['endm'])-mo(t) if e['endm'] else None
        print(f"{e['on']:16}{lag:>9}   {str(e['endm']):>12} {str(e['end']):>12} {str(err):>11}  {e['rev']}")
    else:
        print(f"{e['on']:16}{'FALSE':>9}   {str(e['endm']):>12} {str(e['end']):>12} {'-':>11}  {e['rev']}")
print("episodes:",len(eps),"| revisions:",sum(e['rev'] for e in eps))
