# DIAGNOSTIC: for every recession, every branch's first proposal in the window, the confirmer that completed it and its day
p=p0
G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
PROPS={'U':sorted(leg_gapL_c(spl,p['u45'],p['look'])+F45),'L':sorted(leg_gapL(spl,p['low'],52,rearm='window')+F25),'I':leg_ic_c(ICfp,p['ic']),
       'W':leg_sv(p['wline'],rearm='zero'),'V':leg_sv(p['wline2'],rearm='window'),'B':leg_br(p['bshare'])}
CONFS={'U':[Vc,Hh,SP],'I':[Vc,Hh,SP],'L':[Hc,SP],'W':[Hc,SP],'V':[Hc,SP],'B':[Hc,SP]}
ALL4=[Vc,Hh,Hc,SP]
def first_at_line(cf,dd,back=6,fwd=4):
    ser=cf['gap']; seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; hit=seg[seg>=cf['line']]
    if len(hit)==0: return None
    t=hit.index[0]; return (pubof(cf,t),t)
print('recession | branch | proposal day (data) | its confirmers: first in place (pub day) | call day | with ALL four confirmers')
for i,(pk,tr) in enumerate(zip(PK,TR)):
    if pk<pd.Timestamp('1969-01-01'): continue
    lo=pk-pd.DateOffset(months=6); hi=tr+pd.DateOffset(months=3)
    print(f"--- {pk:%Y-%m} peak (month end {(pk+pd.offsets.MonthEnd(0)).date()})")
    for br,props in PROPS.items():
        w=[(a,b) for a,b in props if lo<=b<=hi]
        if not w: print(f"  {br}: no proposal in window"); continue
        pday,dd=w[0]
        cs=[]
        for cf in CONFS[br]:
            f=first_at_line(cf,dd)
            cs.append(f"{cf['name']} {f[0].date() if f else 'none'}")
        own=[first_at_line(cf,dd) for cf in CONFS[br]]; own=[x for x in own if x]
        call=max(pday,min(x[0] for x in own)) if own else None
        alle=[first_at_line(cf,dd) for cf in ALL4]; alle=[x for x in alle if x]
        call4=max(pday,min(x[0] for x in alle)) if alle else None
        print(f"  {br}: proposal {pday.date()} (data {dd:%Y-%m}) | {'; '.join(cs)} | call {call.date() if call else 'unconfirmed'} | all-four {call4.date() if call4 else 'unconfirmed'}")
    # the hub
    hub=[c for c in build_v.__globals__.get('hubcalls',[])] if False else None
