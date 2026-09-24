import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
ch=dict(channels('United States'))
for nm in ['real income less transfers','real consumption','retail volume','payroll employment',
           'industrial production (Federal Reserve)','real manufacturing and trade sales']:
    s=ma(ch[nm],3)['1969-01':'1971-02'].dropna()
    hi=s.max()
    print(f'--- {nm}   high {s.idxmax().date()}  ({hi:.4g})')
    print('   ', '  '.join(f"{d.strftime('%y-%m')}:{v/hi*100:.1f}" for d,v in s.items()))
