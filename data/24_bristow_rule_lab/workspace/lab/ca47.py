import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
ch=dict(channels('Canada'))
for nm in ['industrial production','manufacturing production','durable manufacturing']:
    s=ch[nm]['1944':'1950']
    print('---',nm)
    print(s.dropna().round(1).to_string())
