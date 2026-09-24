from mini import *
V26=vr; 
sys.path.insert(0,W+'/lab/slack')
from objects import load
v=-load()['-vacancy rate']; m3=v.rolling(3).mean(); V312=(m3.shift(1).rolling(12).max()-m3).dropna()   # Sahm's form on vacancies (Michaillat-Saez mirror)
df=pd.concat([g.rename('sahm_fp'),V26.rename('vac26'),V312.rename('vac312'),PAIR.rename('hous35pair'),P1.rename('hourspair')],axis=1)
def show(a,b): print(df[a:b].round(2).to_string())
print("== 1976 =="); show('1976-06','1977-03')
print("== 2003 =="); show('2003-01','2003-12')
print("== 1967 =="); show('1966-10','1968-03')
print("== 1951-52 =="); show('1951-03','1952-06')
print("== 2024 =="); show('2024-01','2024-12')
print("\n== quiet months (outside peak-6..trough+3 of 12+2024) where Sahm_fp>=0.50 AND vac26>=0.36 in the same month ==")
PKw=PK; TRw=TR
def inwin(d):
    return any(p-pd.DateOffset(months=6)<=d<=t+pd.DateOffset(months=3) for p,t in zip(PKw,TRw))
both=df[(df.sahm_fp>=0.5)&(df.vac26>=0.36)]
print([d.strftime('%Y-%m') for d in both.index if not inwin(d)])
print("== same for Sahm>=0.50 AND vac312>=0.60 (v37 form) ==")
both=df[(df.sahm_fp>=0.5)&(df.vac312>=0.60)]
print([d.strftime('%Y-%m') for d in both.index if not inwin(d)])
print("== Michaillat-Saez style min(sahm, vac312) >= 0.30 quiet months ==")
ms=df[[ 'sahm_fp','vac312']].min(axis=1)
print([d.strftime('%Y-%m') for d,x in ms.items() if x>=0.30 and not inwin(d)])
print("== vac26 >= 0.36 quiet months (episodes) ==")
q=[d for d,x in df.vac26.items() if x>=0.36 and not inwin(d) and d>=pd.Timestamp('1948-01-01')]
runs=[]; 
for d in q:
    if runs and (d-runs[-1][1]).days<=62: runs[-1][1]=d
    else: runs.append([d,d])
print([(a.strftime('%Y-%m'),b.strftime('%Y-%m')) for a,b in runs])
