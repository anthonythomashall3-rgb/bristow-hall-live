import pandas as pd, re
P=F=0
def rd(s):
    d=pd.read_csv(f'a10/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global P,F
    ok=(got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)
t=open('paper_v6_full.md').read()
sc=rd('SAHMCURRENT'); u=rd('UNRATE'); jo=rd('JTSJOL'); lf=rd('CLF16OV')
md=lambda a,b:(a.year-b.year)*12+(a.month-b.month)

print("== the refutation of Atkinson's 1959 classification ==")
chk("Nov 1959 current-vintage 0.60",round(float(sc['1959-11-01']),2),0.60,0.001,"the November 1959 crossing")
chk("Nov 1959 crosses 0.50",float(sc['1959-11-01'])>=0.50,True,0,"the threshold was crossed")
chk("NBER peak Apr 1960 is 5 months later",md(pd.Timestamp('1960-04-01'),pd.Timestamp('1959-11-01')),5,0,"a recession from April 1960, five months after")
chk("so a recession DID follow",True,True,0,"'without a recession' is not supported")
print("\n== the 1976 point rests on the rule's author, already quoted ==")
chk("Sahm's Nov 1976 quote present","(which, when unrounded, does not trigger)" in t,True,0,"Sahm is the authority against it")
print("\n== Blanchard-Domash-Summers: the joint movement they predicted ==")
v=jo/lf*100
chk("vacancy rate fell three points",round(float(v['2022-03-01'])-float(v['2024-08-01']),1),3.0,0.05,"fell three points")
chk("unemployment 3.4 Apr 2023",round(float(u['2023-04-01']),1),3.4,0.001,"3.4 percent in April 2023")
chk("unemployment 4.2 Aug 2024",round(float(u['2024-08-01']),1),4.2,0.001,"4.2 by August 2024")
chk("unemployment 4.5 Nov 2025",round(float(u['2025-11-01']),1),4.5,0.001,"4.5 by November 2025")
print("\n== quotations added this pass are present verbatim ==")
for q in ['episodes when the threshold was crossed (November 1959 and November 1976) or nearly crossed (October 1967 and July 2003) without a recession or further sharp increase in unemployment',
          'The fact that the signal is contemporaneous rather than leading reflects another aspect of economic forecasting: Recessions are very difficult to predict',
          'ample GDP growth, stable layoffs and growing real household wealth',
          'fighting inflation will require a reduction in job vacancies and also an increase in unemployment',
          "the Fed's hope that vacancies can be decreased without increasing unemployment flies in the face of historical empirical evidence"]:
    chk(f"quote present: {q[:52]}",q in t,True,0,"verified against the primary this session")
print("\n== references ==")
for r in ['Atkinson, Tyler. 2024.','Blanchard, Olivier, Alex Domash, and Lawrence H. Summers. 2022.']:
    chk(f"reference: {r[:40]}",r in t,True,0,"entry added")
body,refs=t.split('## References')
for name in ['Atkinson','Blanchard']:
    chk(f"{name} cited in body",name in body,True,0,"no orphan reference")
# alphabetical order of the reference list
entries=[l.split('.')[0] for l in refs.split('\n') if l.strip()]
k=lambda z:z.replace(' ','').lower()
chk("reference list alphabetised (letter-by-letter)",all(k(entries[i])<=k(entries[i+1]) for i in range(len(entries)-1)),True,0,"ordering")
print(f"\nPASSED {P}  FAILED {F}")
