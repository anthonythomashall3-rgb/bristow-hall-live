"""Stage 86: (a) what the 4% global floor actually does, (b) how high the clause floor can go."""
exec(open("stage85_v9_tests.py").read().split('print("=== perturbation map')[0])
import numpy as np
def full(gf,cf):
    co=CL>=gf; cco=CL>=cf
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       np.asarray(persist2(h3,20),bool),np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    QU=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
    for p,t in [(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]:
        QU &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&co&G)
    armed|=(CLA&NG)
    return eps,[str(e["onset"].date()) for e in eps],[str(e["end_call"].date()) for e in eps],f,sum(1 for x in rN if x["lag"] is not None),100*(armed&QU).sum()/QU.sum()
e0,d0,en0,f0,n0,x0=full(0.03,0.10)
print("v9 (3%%/10%%): dates %s  ends ok  false %s  no-inv %d/9  quiet exposure %.3f%%" % ("identical" if d0==REF else d0,f0 if f0 else 0,n0,x0))
e1,d1,en1,f1,n1,x1=full(0.04,0.10)
print("\nat a 4%% global floor the extra episode is:", f1)
print("  its episodes:", [str(e["onset"].date()) for e in e1])
print("  -> the tightening makes one recession close early and re-open: an episode-splitting")
print("     artefact of the state machine, not a new quiet-period crossing.")
print("\nhow high can the clause floor go?")
for cf in [0.10,0.12,0.15,0.18,0.20,0.25]:
    e,d,en,f,n,x=full(0.03,cf)
    print("   %.0f%%  dates %-9s ends %-9s false %-3s no-inv %d/9  exposure %.3f%%" %
          (100*cf,"ok" if d==REF else "BROKEN","ok" if en==en0 else "BROKEN",len(f) if f else 0,n,x))
