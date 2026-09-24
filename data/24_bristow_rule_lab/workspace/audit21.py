import pandas as pd
P=F=0
def rd(s):
    d=pd.read_csv(f'a20/{s}.csv'); d.columns=['date','v']
    d['date']=pd.to_datetime(d['date']); d['v']=pd.to_numeric(d['v'],errors='coerce')
    return d.set_index('date')['v'].dropna()
def chk(lab,got,want,tol=1e-9,claim=None):
    global P,F
    ok=(got==want) if isinstance(want,(str,bool,tuple)) else abs(got-want)<=tol
    print(("PASS " if ok else "FAIL ")+f"{lab}: got={got!r} want={want!r}"+("" if ok else f"  << {claim}"))
    P,F=(P+1,F) if ok else (P,F+1)
t=open('paper_v6_full.md').read()
pct=lambda s,a,b: 100*(float(s[b])/float(s[a])-1)

print("== the six indicators, April to August 2024 ==")
for k,name,stated in [('CMRMTSPL','mfg and trade sales',1.87),('PCEC96','real PCE',1.26),
                      ('W875RX1','income less transfers',0.78),('INDPRO','industrial production',0.19),
                      ('PAYEMS','nonfarm payrolls',0.14),('CE16OV','household employment',-0.01)]:
    chk(name,round(pct(rd(k),'2024-04-01','2024-08-01'),2),stated,0.005,f"rose {stated} percent")
chk("only household employment fell",
    sum(1 for k in ['CMRMTSPL','PCEC96','W875RX1','INDPRO','PAYEMS','CE16OV']
        if pct(rd(k),'2024-04-01','2024-08-01')<0),1,0,"only household-survey employment fell")

print("\n== annualised rates quoted ==")
ann=lambda p:((1+p/100)**3-1)*100
chk("sales 5.7% annualised",round(ann(pct(rd('CMRMTSPL'),'2024-04-01','2024-08-01')),1),5.7,0.05,"sales at 5.7 percent")
chk("consumption 3.8% annualised",round(ann(pct(rd('PCEC96'),'2024-04-01','2024-08-01')),1),3.8,0.05,"consumption at 3.8 percent")
chk("IP 0.6% annualised",round(ann(pct(rd('INDPRO'),'2024-04-01','2024-08-01')),1),0.6,0.05,"six-tenths of a percent at an annual rate")

print("\n== levels quoted ==")
ce=rd('CE16OV'); pay=rd('PAYEMS')
chk("household employment fell 9,000",round(float(ce['2024-08-01'])-float(ce['2024-04-01'])),-9,0,"nine thousand jobs")
chk("payroll gain 227,000",round(float(pay['2024-08-01'])-float(pay['2024-04-01'])),227,0,"227,000")
chk("598,000 exceeds the payroll gain",598>round(float(pay['2024-08-01'])-float(pay['2024-04-01'])),True,0,"smaller than the 598,000")
chk("IP peaked April 2022",rd('INDPRO')['2021-06-01':'2024-12-01'].idxmax().strftime('%Y-%m'),'2022-04',0,"peaked in April 2022")
chk("IP never regains the Apr 2022 level through 2024",
    bool((rd('INDPRO')['2022-05-01':'2024-12-01']>=float(rd('INDPRO')['2022-04-01'])).any()),False,0,"would not regain that level")

print("\n== the comparison recessions ==")
SIX=['W875RX1','PAYEMS','PCEC96','CMRMTSPL','CE16OV','INDPRO']
def fell(a,b):
    n=f=0
    for k in SIX:
        s=rd(k)
        try: v=pct(s,a,b)
        except Exception: continue
        n+=1; f+= v<0
    return f,n
chk("1990-91 first four months",fell('1990-07-01','1990-11-01'),(5,5),0,"every one of the five ... fell")
chk("2001 first four months",fell('2001-03-01','2001-07-01'),(5,5),0,"every one of the five ... fell")
chk("2007-09 first four months",fell('2007-12-01','2008-04-01'),(5,6),0,"five of the six fell")
chk("PCE monthly series begins 2007",rd('PCEC96').index[0].strftime('%Y'),'2007',0,"the five for which monthly data reach that far back")

print("\n== the paragraph is present and its figures match ==")
for s in ["real manufacturing and trade sales rose 1.87 percent","real personal consumption expenditures 1.26 percent",
          "real personal income less transfers 0.78 percent","industrial production 0.19 percent",
          "nonfarm payroll employment 0.14 percent","by 0.01 percent, a decline of nine thousand jobs",
          "sales at 5.7 percent and consumption at 3.8 percent","six-tenths of a percent at an annual rate",
          "The payroll gain across the four months was 227,000","smaller than the 598,000",
          "five of the six fell","the strongest single objection to the dating"]:
    chk(f"text: {s[:46]}",s in t,True,0,"paragraph wording")
print(f"\nPASSED {P}  FAILED {F}")
