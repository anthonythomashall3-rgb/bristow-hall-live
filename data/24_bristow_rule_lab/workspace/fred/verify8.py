import pandas as pd, numpy as np
def ann(df,col):
    df=df.copy(); df['g']=((df[col]/df[col].shift(1))**4-1)*100; return df
g=pd.read_csv('GDPC1.csv',parse_dates=['observation_date']); g.columns=['date','gdp']
i=pd.read_csv('A261RX1Q020SBEA.csv',parse_dates=['observation_date']); i.columns=['date','gdi']
m=pd.merge(g,i,on='date'); m=ann(m,'gdp'); m['gi']=((m.gdi/m.gdi.shift(1))**4-1)*100
print("Current vintage annualized q/q growth, 2021Q4-2023Q2:")
print(m[(m.date>='2021-10-01')&(m.date<='2023-06-01')][['date','g','gi']].round(2).to_string(index=False))
print("\n1947 (GDP only):")
g2=ann(g,'gdp'); print(g2[(g2.date>='1947-01-01')&(g2.date<='1948-03-01')][['date','g']].round(2).to_string(index=False))
print("\n2003Q3 GDP growth:"); print(g2[(g2.date>='2003-04-01')&(g2.date<='2003-12-01')][['date','g']].round(2).to_string(index=False))
print("\nLatest quarters:"); print(m.tail(10)[['date','g','gi']].round(2).to_string(index=False))
