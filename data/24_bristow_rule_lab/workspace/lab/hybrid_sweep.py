import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, pandas as pd, numpy as np, warnings, json; warnings.filterwarnings('ignore')
from rule17_sweep import score
rows=[]
for sm,ds,tag in ((3,None,'shipped s3'),(3,1,'plateau s3 + D-peak s1'),(3,2,'plateau s3 + D-peak s2'),(2,1,'plateau s2 + D-peak s1'),(2,None,'s2'),(1,None,'s1')):
    B.DPEAK_SMOOTH=ds
    s=score(sm,'later','all',True)
    print(f'{tag:26s} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f} | Q {s["qp_exact"]}/{s["qt_exact"]} of {s["qn"]}', flush=True)
    for c,(cp,ct) in s['per'].items():
        f=lambda v:[('-' if x is None else x) for x in v]
        print(f'    {c:24s} peaks {str(f(cp)):58s} troughs {str(f(ct))}', flush=True)
    rows.append((tag,{k:v for k,v in s.items() if k!='per'},s['per']))
B.DPEAK_SMOOTH=None
json.dump(rows,open('/home/claude/lab/hybrid_sweep.json','w'),default=str)
