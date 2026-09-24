def rd2(s): x=pd.read_csv(f'cache/surveys/{s}.csv',index_col=0,parse_dates=True).iloc[:,0].astype(float).dropna(); return x
PH=rd2('GACDFSA066MSFRBPHI'); NY=rd2('GACDISA066MSFRBNY'); CF=rd2('CFNAI'); LI=rd2('USSLIND'); MI=rd2('MICH'); PM=rd2('PERMIT'); NO=rd2('NEWORDER'); AW=rd2('AWHMAN')
OBJ2={}
OBJ2['Philly BOS, 3mo mean (negative = minus)']=(-PH.rolling(3).mean()).dropna()
OBJ2['Philly BOS, single month (minus)']=(-PH).dropna()
OBJ2['Empire, 3mo mean (minus)']=(-NY.rolling(3).mean()).dropna()
OBJ2['CFNAI 3mo avg (minus; Chicago Fed rule -0.7)']=(-CF.rolling(3).mean()).dropna()
OBJ2['USSLIND leading index (minus)']=(-LI).dropna()
OBJ2['Michigan expectations 3mo below 12mo high']=(MI.rolling(3).mean().rolling(12).max().shift(1)-MI.rolling(3).mean()).dropna()
lpm=np.log(PM)*100; OBJ2['permits 3mo below 12mo high, log pts']=(lpm.rolling(12).max()-lpm.rolling(3).mean()).dropna()
OBJ2['core capital orders 3mo change % (minus)']=(-(NO.rolling(3).mean()/NO.rolling(3).mean().shift(3)-1)*100).dropna()
OBJ2['factory hours below 12mo high %']=((AW.rolling(12).max()-AW)/AW.rolling(12).max()*100).dropna()
print(f"{'object':46s} "+' | '.join(k[:11] for k in WIN))
for nm,s in OBJ2.items():
    row=[]
    for k,(a,b) in WIN.items():
        seg=s[a:b]; row.append(f"{seg.max():6.1f}" if len(seg) else '   n/a')
    print(f"{nm:46s} "+' | '.join(row))
