"""HOW GOOD IS OUR CAUSAL TEST? Its blind spot is OBJECT SELECTION. The replay re-chooses fourteen NUMBERS from the past,
but the OBJECT SET was chosen by me this week, knowing the whole record — the paper spread was found by sweeping 15,128
files against all 78 years. Nobody in 1969 had it in their candidate set. This tests exactly that: at each fold, the
whole spread family is re-screened using ONLY the quiet windows before the fold, and we ask (a) would this object have
passed the screen then, (b) what line would the rule have set, (c) would any OTHER spread have looked better."""
exec(open('fast51.py').read().split("def full(")[0].replace("out=open('fast51.out','w')","out=open('causal32.out','w')"))
OUT2=open("causal32.out","w")
def P(*a):
    t=" ".join(str(x) for x in a); print(t); OUT2.write(t+"\n"); OUT2.flush()
def sp2(a,b):
    aa=L25(a); bb=L25(b)
    if aa is None or bb is None: return None
    idx=aa.index.union(bb.index); S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna()
    return S[S.index>=max(aa.index.min(),bb.index.min())]
FAM=[('CP1m-bill3m','H0RIFSPPFM01NWF','WTB3MS'),('CP3m-bill3m','H0RIFSPPFM03NWF','WTB3MS'),('CP6m-bill3m','H0RIFSPPFM06NWF','WTB3MS'),
     ('BA3m-bill3m','H1RIFSPABM03NWF','WTB3MS'),('prime-bill3m','WPRIME','WTB3MS'),('CD3m-bill3m','WCD3M','WTB3MS'),
     ('CP3m-funds','H0RIFSPPFM03NWF','FF'),('bill6m-bill3m','WTB6MS','WTB3MS')]
def objx(S,sm=13,win=39):
    m=S.rolling(sm).mean(); return (m-m.rolling(win).min()).dropna()
P("(a) WOULD THE ADOPTED OBJECT HAVE PASSED ITS OWN SCREEN, USING ONLY THE PAST?")
P(f"{'fold':10s} {'quiet windows before':>21s} {'quiet max then':>15s} {'line the rule sets':>19s} {'recessions it then reached':>27s}")
S=sp2('H0RIFSPPFM01NWF','WTB3MS'); G=objx(S)
for i in range(5,13):
    cut=PK[i]-pd.DateOffset(months=6)
    qb=[dd for dd in QP if dd<cut and len(wseg(G,dd))]
    if not qb: P(f"{PK[i]:%Y-%m}   (no quiet window with data before this fold)"); continue
    qm=max(float(wseg(G,dd).max()) for dd in qb); ln=qm*1.5
    prior=[j for j in range(i) if len(wseg(G,PK[j]))]
    reach=[PK[j].strftime('%Y') for j in prior if float(wseg(G,PK[j]).max())>=ln]
    P(f"{PK[i]:%Y-%m}   {len(qb):21d} {qm:15.3f} {ln:19.3f}   {str(reach):>27s}")
P("\n(b) WOULD ANY OTHER SPREAD HAVE LOOKED BETTER AT EACH FOLD? (screen: clears every quiet window before the fold;")
P("    ranked by how many PRIOR recessions it reaches at 1.5x its own quiet maximum)")
GS={}
for nm,a,b in FAM:
    s=sp2(a,b)
    if s is not None and len(s)>200: GS[nm]=objx(s)
for i in [5,7,8,9,10,11,12]:
    cut=PK[i]-pd.DateOffset(months=6); rank=[]
    for nm,Gx in GS.items():
        qb=[dd for dd in QP if dd<cut and len(wseg(Gx,dd))]
        if len(qb)<5: continue
        qm=max(float(wseg(Gx,dd).max()) for dd in qb); ln=qm*1.5
        prior=[j for j in range(i) if len(wseg(Gx,PK[j]))]
        n=sum(1 for j in prior if float(wseg(Gx,PK[j]).max())>=ln)
        rank.append((n,nm,round(ln,3)))
    rank.sort(reverse=True)
    P(f"   {PK[i]:%Y-%m}: " + " | ".join(f"{nm} {n}/{len([j for j in range(i)])} at {ln}" for n,nm,ln in rank[:4]))
P("\n(c) THE SHAPE — would the thirteen-week mean over a nine-month minimum have been chosen from the past?")
for i in [8,10,12]:
    cut=PK[i]-pd.DateOffset(months=6); best=[]
    for sm in [1,4,8,13,17,26]:
        for wmon in [3,6,9,12]:
            Gx=objx(S,sm,max(4,int(wmon*30/7)))
            qb=[dd for dd in QP if dd<cut and len(wseg(Gx,dd))]
            if len(qb)<5: continue
            qm=max(float(wseg(Gx,dd).max()) for dd in qb); ln=qm*1.5
            prior=[j for j in range(i) if len(wseg(Gx,PK[j]))]
            n=sum(1 for j in prior if float(wseg(Gx,PK[j]).max())>=ln)
            best.append((n,sm,wmon,round(ln,3)))
    best.sort(reverse=True)
    P(f"   {PK[i]:%Y-%m}: best shapes on the past — " + " | ".join(f"sm{sm} {wmon}m ({n} prior, line {ln})" for n,sm,wmon,ln in best[:5]))
OUT2.close()
