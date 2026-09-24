import pandas as pd, numpy as np
sc=pd.read_csv('SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','v']
sc['v']=pd.to_numeric(sc['v'],errors='coerce'); sc=sc.dropna().set_index('date')
for lbl,a,b in [("1981-82 trough Nov1982","1982-06","1983-04"),("2007-09 trough Jun2009","2009-01","2009-12"),
                ("1990-91 trough Mar1991","1991-01","1991-10"),("1957-58 trough Apr1958","1958-01","1958-09")]:
    print(f"\n{lbl}"); print(sc.loc[a:b].T.to_string())
